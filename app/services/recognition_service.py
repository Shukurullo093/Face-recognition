"""Core recognition service: enrollment, verification (1:1), identification (1:N).

Orchestrates the ML pipeline + repositories. Holds no framework (FastAPI) types
— it is pure application logic, which keeps it unit-testable in isolation.
"""
from __future__ import annotations

import uuid

import numpy as np

from app.core.config import Settings
from app.core.exceptions import EntityNotFoundError
from app.core.imaging import make_face_thumbnail
from app.core.logging import get_logger
from app.models.face import Face
from app.models.person import Person
from app.models.recognition_log import RecognitionAction
from app.recognition.pipeline import RecognitionPipeline
from app.repositories.face_repo import FaceRepository, SearchRow
from app.repositories.log_repo import RecognitionLogRepository
from app.repositories.person_repo import PersonRepository
from app.schemas.common import BoundingBox
from app.schemas.api_key import ExternalSearchResponse
from app.schemas.face import (
    FaceRegisterResponse,
    SearchMatch,
    SearchResponse,
    VerifyResponse,
)

log = get_logger(__name__)


def _bbox_from_array(arr: np.ndarray) -> BoundingBox:
    return BoundingBox(x1=float(arr[0]), y1=float(arr[1]), x2=float(arr[2]), y2=float(arr[3]))


class RecognitionService:
    def __init__(
        self,
        pipeline: RecognitionPipeline,
        person_repo: PersonRepository,
        face_repo: FaceRepository,
        log_repo: RecognitionLogRepository,
        settings: Settings,
        *,
        actor: str | None = None,
        client_ip: str | None = None,
    ) -> None:
        self.pipeline = pipeline
        self.persons = person_repo
        self.faces = face_repo
        self.logs = log_repo
        self.settings = settings
        self.actor = actor
        self.client_ip = client_ip

    # ---------------- Enrollment ----------------
    async def _enroll(
        self, person: Person, image_bytes: bytes, image_path: str | None
    ) -> FaceRegisterResponse:
        image = self.pipeline.decode_image(image_bytes)
        result = await self.pipeline.process_single(image)

        face = Face(
            person_id=person.id,
            embedding=result.embedding.tolist(),
            det_score=result.detection.score,
            quality=result.detection.score,
            image_path=image_path,
            bbox=_bbox_from_array(result.detection.bbox).model_dump(),
            thumbnail=make_face_thumbnail(image, result.detection.bbox),
        )
        face = await self.faces.add(face)

        await self.logs.record(
            action=RecognitionAction.REGISTER,
            person_id=person.id,
            matched_face_id=face.id,
            success=True,
            user_id=self.actor,
            client_ip=self.client_ip,
        )
        log.info("face_registered", face_id=str(face.id), person_id=str(person.id))
        return FaceRegisterResponse(
            face_id=face.id,
            person_id=person.id,
            confidence=result.detection.score,
            bbox=_bbox_from_array(result.detection.bbox),
        )

    async def register(
        self, person_id: uuid.UUID, image_bytes: bytes, image_path: str | None = None
    ) -> FaceRegisterResponse:
        """Enroll one more face image for an existing person.

        A person may own many faces; 1:N search returns the person if any of
        their enrolled embeddings matches.
        """
        person = await self.persons.get(person_id)
        if person is None:
            raise EntityNotFoundError(f"Person {person_id} not found")
        return await self._enroll(person, image_bytes, image_path)

    async def register_by_name(
        self, full_name: str, image_bytes: bytes, image_path: str | None = None
    ) -> FaceRegisterResponse:
        """Find-or-create a person by name, then enroll (used by client folder import)."""
        full_name = full_name.strip()
        person = await self.persons.get_by_name(full_name)
        if person is None:
            person = await self.persons.add(Person(full_name=full_name))
        return await self._enroll(person, image_bytes, image_path)

    async def replace_face_image(
        self, face_id: uuid.UUID, image_bytes: bytes, image_path: str | None = None
    ) -> FaceRegisterResponse:
        """Re-detect & re-embed a new image, updating the embedding + thumbnail
        of an existing face row (keeps the same face_id and person)."""
        face = await self.faces.get(face_id)
        if face is None:
            raise EntityNotFoundError(f"Face {face_id} not found")

        image = self.pipeline.decode_image(image_bytes)
        result = await self.pipeline.process_single(image)

        face.embedding = result.embedding.tolist()
        face.det_score = result.detection.score
        face.quality = result.detection.score
        face.bbox = _bbox_from_array(result.detection.bbox).model_dump()
        face.thumbnail = make_face_thumbnail(image, result.detection.bbox)
        if image_path is not None:
            face.image_path = image_path
        await self.faces.session.flush()

        await self.logs.record(
            action=RecognitionAction.REGISTER,
            person_id=face.person_id,
            matched_face_id=face.id,
            success=True,
            user_id=self.actor,
            client_ip=self.client_ip,
            message="image replaced",
        )
        log.info("face_image_replaced", face_id=str(face.id))
        return FaceRegisterResponse(
            face_id=face.id,
            person_id=face.person_id,
            confidence=result.detection.score,
            bbox=_bbox_from_array(result.detection.bbox),
        )

    # ---------------- Verification (1:1) ----------------
    async def verify(self, person_id: uuid.UUID, image_bytes: bytes) -> VerifyResponse:
        person = await self.persons.get(person_id)
        if person is None:
            raise EntityNotFoundError(f"Person {person_id} not found")

        image = self.pipeline.decode_image(image_bytes)
        result = await self.pipeline.process_largest(image)

        match = await self.faces.best_match_for_person(person.id, result.embedding.tolist())
        threshold = self.settings.RECOGNITION_THRESHOLD
        if match is None:
            similarity, matched_face_id = 0.0, None
        else:
            matched_face_id, similarity = match
        matched = similarity >= threshold

        await self.logs.record(
            action=RecognitionAction.VERIFY,
            person_id=person.id,
            matched_face_id=matched_face_id,
            similarity=similarity,
            success=matched,
            user_id=self.actor,
            client_ip=self.client_ip,
        )
        log.info("face_verified", person_id=str(person.id), similarity=similarity, matched=matched)
        return VerifyResponse(
            matched=matched,
            similarity_score=round(similarity, 6),
            threshold=threshold,
            person_id=person.id,
            matched_face_id=matched_face_id if matched else None,
        )

    # ---------------- Identification (1:N) ----------------
    async def search(self, image_bytes: bytes, top_k: int | None = None) -> SearchResponse:
        image = self.pipeline.decode_image(image_bytes)
        result = await self.pipeline.process_largest(image)

        k = top_k or self.settings.SEARCH_TOP_K
        threshold = self.settings.RECOGNITION_THRESHOLD
        rows: list[SearchRow] = await self.faces.search(result.embedding.tolist(), top_k=k)
        matches = [
            SearchMatch(
                person_id=r.person_id,
                face_id=r.face_id,
                full_name=r.full_name,
                similarity_score=round(r.similarity, 6),
            )
            for r in rows
            if r.similarity >= threshold
        ]

        best = matches[0] if matches else None
        await self.logs.record(
            action=RecognitionAction.SEARCH,
            person_id=best.person_id if best else None,
            matched_face_id=best.face_id if best else None,
            similarity=best.similarity_score if best else None,
            success=bool(matches),
            user_id=self.actor,
            client_ip=self.client_ip,
        )
        log.info("face_searched", num_matches=len(matches), top_k=k)
        return SearchResponse(
            matches=matches,
            threshold=threshold,
            query_confidence=result.detection.score,
        )

    async def identify_top1(self, image_bytes: bytes) -> ExternalSearchResponse:
        """3rd-party 1:N: return the single best match above threshold, or none."""
        image = self.pipeline.decode_image(image_bytes)
        result = await self.pipeline.process_largest(image)
        threshold = self.settings.RECOGNITION_THRESHOLD
        rows = await self.faces.search(result.embedding.tolist(), top_k=1)
        best = rows[0] if rows and rows[0].similarity >= threshold else None

        await self.logs.record(
            action=RecognitionAction.SEARCH,
            person_id=best.person_id if best else None,
            matched_face_id=best.face_id if best else None,
            similarity=best.similarity if best else None,
            success=bool(best),
            user_id=self.actor,
            client_ip=self.client_ip,
        )
        return ExternalSearchResponse(
            matched=bool(best),
            person_id=best.person_id if best else None,
            full_name=best.full_name if best else None,
            similarity=round(best.similarity, 6) if best else None,
            threshold=threshold,
        )
