"""Bulk import: enroll every image under a folder tree, with batched embedding.

Folder layout (use_dir_as_person=True):
    <root>/<person_name>/<img1.jpg>, <img2.png>, ...

The job runs in the background; progress is reported through JobStore. It owns
its own DB session (the request's session is closed once the endpoint returns).
"""
from __future__ import annotations

import uuid
from pathlib import Path

import cv2
import numpy as np

from app.core.config import Settings
from app.core.imaging import make_face_thumbnail
from app.core.logging import get_logger
from app.db.session import AsyncSessionFactory
from app.models.face import Face
from app.models.person import Person
from app.models.recognition_log import RecognitionAction
from app.recognition.pipeline import RecognitionPipeline
from app.repositories.face_repo import FaceRepository
from app.repositories.log_repo import RecognitionLogRepository
from app.repositories.person_repo import PersonRepository
from app.services.job_store import ImportJob, JobStore, job_store

log = get_logger(__name__)

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class BulkImportService:
    def __init__(
        self,
        pipeline: RecognitionPipeline,
        settings: Settings,
        jobs: JobStore = job_store,
    ) -> None:
        self.pipeline = pipeline
        self.settings = settings
        self.jobs = jobs

    @staticmethod
    def _discover(root: Path) -> list[tuple[str, Path]]:
        """Return (person_name, image_path) pairs from <root>/<person>/<img>."""
        pairs: list[tuple[str, Path]] = []
        for person_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            for img in sorted(person_dir.iterdir()):
                if img.suffix.lower() in _IMAGE_SUFFIXES:
                    pairs.append((person_dir.name, img))
        return pairs

    async def run(self, job: ImportJob, root_path: str) -> None:
        """Entry point for the background task."""
        root = Path(root_path)
        if not root.is_dir():
            self.jobs.add_error(job.job_id, f"Root path not found or not a directory: {root_path}")
            self.jobs.mark_finished(job.job_id, failed=True)
            return

        pairs = self._discover(root)
        self.jobs.mark_running(job.job_id, total=len(pairs))
        log.info("bulk_import_started", job_id=str(job.job_id), total=len(pairs))

        # Group by person so we resolve/create each Person once.
        person_cache: dict[str, uuid.UUID] = {}
        batch_size = self.settings.IMPORT_BATCH_SIZE
        batch: list[tuple[str, Path]] = []

        for pair in pairs:
            batch.append(pair)
            if len(batch) >= batch_size:
                await self._process_batch(batch, person_cache, job)
                batch.clear()
        if batch:
            await self._process_batch(batch, person_cache, job)

        self.jobs.mark_finished(job.job_id)
        snap = self.jobs.get(job.job_id)
        log.info(
            "bulk_import_finished",
            job_id=str(job.job_id),
            succeeded=snap.succeeded if snap else 0,
            failed=snap.failed if snap else 0,
        )

    async def _process_batch(
        self,
        batch: list[tuple[str, Path]],
        person_cache: dict[str, uuid.UUID],
        job: ImportJob,
    ) -> None:
        async with AsyncSessionFactory() as session:
            persons = PersonRepository(session)
            faces = FaceRepository(session, ef_search=self.settings.HNSW_EF_SEARCH)
            logs = RecognitionLogRepository(session)
            try:
                for person_name, img_path in batch:
                    await self._process_one(
                        person_name, img_path, person_cache, persons, faces, logs, job
                    )
                await session.commit()
            except Exception as exc:  # noqa: BLE001 — isolate batch failure
                await session.rollback()
                self.jobs.add_error(job.job_id, f"Batch failed: {exc}")
                log.error("bulk_import_batch_failed", error=str(exc), exc_info=exc)

    async def _process_one(
        self,
        person_name: str,
        img_path: Path,
        person_cache: dict[str, uuid.UUID],
        persons: PersonRepository,
        faces: FaceRepository,
        logs: RecognitionLogRepository,
        job: ImportJob,
    ) -> None:
        try:
            image = cv2.imdecode(
                np.fromfile(str(img_path), dtype=np.uint8), cv2.IMREAD_COLOR
            )
            if image is None:
                raise ValueError("could not decode image")

            result = await self.pipeline.process_largest(image)

            person_id = person_cache.get(person_name)
            if person_id is None:
                existing = await persons.get_by_name(person_name)
                if existing is None:
                    existing = await persons.add(Person(full_name=person_name))
                person_id = existing.id
                person_cache[person_name] = person_id

            await faces.add(
                Face(
                    person_id=person_id,
                    embedding=result.embedding.tolist(),
                    det_score=result.detection.score,
                    quality=result.detection.score,
                    image_path=str(img_path),
                    thumbnail=make_face_thumbnail(image, result.detection.bbox),
                )
            )
            self.jobs.record(job.job_id, success=True)
        except Exception as exc:  # noqa: BLE001 — per-image isolation
            self.jobs.record(job.job_id, success=False, error=f"{img_path}: {exc}")
            await logs.record(
                action=RecognitionAction.IMPORT,
                success=False,
                message=f"{img_path.name}: {exc}"[:512],
            )
