"""Core recognition service: enrollment, verification (1:1), identification (1:N).

Orchestrates the ML pipeline + repositories. Holds no framework (FastAPI) types
— it is pure application logic, which keeps it unit-testable in isolation.
"""
from __future__ import annotations

import uuid

import numpy as np

from app.core.config import Settings
from app.core.exceptions import EntityNotFoundError
from app.core.logging import get_logger
from app.models.face import Face
from app.models.recognition_log import RecognitionAction
from app.recognition.pipeline import RecognitionPipeline
from app.repositories.face_repo import FaceRepository, SearchRow
from app.repositories.log_repo import RecognitionLogRepository
from app.repositories.person_repo import PersonRepository
from app.schemas.common import BoundingBox
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
    async def register(
        self, person_id: uuid.UUID, image_bytes: bytes, image_path: str | None = None
    ) -> FaceRegisterResponse:
        person = await self.persons.get(person_id)
        if person is None:
            raise EntityNotFoundError(f"Person {person_id} not found")

        image = self.pipeline.decode_image(image_bytes)
        result = await self.pipeline.process_single(image)

        face = Face(
            person_id=person.id,
            embedding=result.embedding.tolist(),
            det_score=result.detection.score,
            quality=result.detection.score,
            image_path=image_path,
            bbox=_bbox_from_array(result.detection.bbox).model_dump(),
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
