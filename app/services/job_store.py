"""In-process job registry for bulk-import progress tracking.

Single-worker friendly. For multi-worker / multi-replica deployments swap this
for a Redis/DB-backed store behind the same interface (it is intentionally
small and pluggable).
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class ImportJob:
    job_id: uuid.UUID
    state: str = "pending"  # pending | running | completed | failed
    total: int = 0
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def add_error(self, msg: str, *, cap: int = 100) -> None:
        if len(self.errors) < cap:
            self.errors.append(msg)


class JobStore:
    """Thread-safe registry of import jobs."""

    def __init__(self) -> None:
        self._jobs: dict[uuid.UUID, ImportJob] = {}
        self._lock = threading.Lock()

    def create(self) -> ImportJob:
        job = ImportJob(job_id=uuid.uuid4())
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: uuid.UUID) -> ImportJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def mark_running(self, job: ImportJob, total: int) -> None:
        with self._lock:
            job.state = "running"
            job.total = total
            job.started_at = datetime.now(UTC)

    def mark_finished(self, job: ImportJob, failed: bool = False) -> None:
        with self._lock:
            job.state = "failed" if failed else "completed"
            job.finished_at = datetime.now(UTC)


# Module-level singleton.
job_store = JobStore()
