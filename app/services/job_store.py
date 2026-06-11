"""Job registry for bulk-import progress tracking.

`ImportJob` is a read snapshot; the store is the source of truth. All mutations
go through store methods (atomic per call) so the Redis backend stays consistent
across workers — the service never mutates a job object in place.

`build_job_store()` returns a Redis-backed store when REDIS_URL is set (shared
across workers/replicas) and otherwise an in-process one (single worker only).
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from app.core.redis_client import get_redis

_ERROR_CAP = 100


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


class JobStore(Protocol):
    """Pluggable store. Counter updates are atomic; `get` returns a snapshot."""

    def create(self) -> ImportJob: ...
    def get(self, job_id: uuid.UUID) -> ImportJob | None: ...
    def mark_running(self, job_id: uuid.UUID, total: int) -> None: ...
    def mark_finished(self, job_id: uuid.UUID, failed: bool = False) -> None: ...
    def record(self, job_id: uuid.UUID, *, success: bool, error: str | None = None) -> None: ...
    def add_error(self, job_id: uuid.UUID, msg: str) -> None: ...


class InProcessJobStore:
    """Thread-safe registry of import jobs held in memory (per-worker)."""

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

    def mark_running(self, job_id: uuid.UUID, total: int) -> None:
        with self._lock:
            if job := self._jobs.get(job_id):
                job.state = "running"
                job.total = total
                job.started_at = datetime.now(UTC)

    def mark_finished(self, job_id: uuid.UUID, failed: bool = False) -> None:
        with self._lock:
            if job := self._jobs.get(job_id):
                job.state = "failed" if failed else "completed"
                job.finished_at = datetime.now(UTC)

    def record(self, job_id: uuid.UUID, *, success: bool, error: str | None = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.processed += 1
            if success:
                job.succeeded += 1
            else:
                job.failed += 1
            if error and len(job.errors) < _ERROR_CAP:
                job.errors.append(error)

    def add_error(self, job_id: uuid.UUID, msg: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job and len(job.errors) < _ERROR_CAP:
                job.errors.append(msg)


class RedisJobStore:
    """Redis-backed registry: one hash per job + a capped errors list.

    Counters use HINCRBY so concurrent batches never lose updates. Keys expire
    after `ttl_seconds` so finished jobs don't accumulate.
    """

    _PREFIX = "fr:import:job:"

    def __init__(self, redis, ttl_seconds: int = 86_400) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    def _h(self, job_id: uuid.UUID) -> str:
        return f"{self._PREFIX}{job_id}"

    def _e(self, job_id: uuid.UUID) -> str:
        return f"{self._PREFIX}{job_id}:errors"

    def create(self) -> ImportJob:
        job = ImportJob(job_id=uuid.uuid4())
        key = self._h(job.job_id)
        self._redis.hset(
            key,
            mapping={
                "state": job.state,
                "total": 0,
                "processed": 0,
                "succeeded": 0,
                "failed": 0,
                "started_at": "",
                "finished_at": "",
            },
        )
        self._redis.expire(key, self._ttl)
        return job

    def get(self, job_id: uuid.UUID) -> ImportJob | None:
        data = self._redis.hgetall(self._h(job_id))
        if not data:
            return None
        errors = self._redis.lrange(self._e(job_id), 0, -1)
        return ImportJob(
            job_id=job_id,
            state=data.get("state", "pending"),
            total=int(data.get("total", 0)),
            processed=int(data.get("processed", 0)),
            succeeded=int(data.get("succeeded", 0)),
            failed=int(data.get("failed", 0)),
            errors=list(errors),
            started_at=_parse_dt(data.get("started_at")),
            finished_at=_parse_dt(data.get("finished_at")),
        )

    def mark_running(self, job_id: uuid.UUID, total: int) -> None:
        self._redis.hset(
            self._h(job_id),
            mapping={"state": "running", "total": total, "started_at": _now_iso()},
        )

    def mark_finished(self, job_id: uuid.UUID, failed: bool = False) -> None:
        self._redis.hset(
            self._h(job_id),
            mapping={
                "state": "failed" if failed else "completed",
                "finished_at": _now_iso(),
            },
        )

    def record(self, job_id: uuid.UUID, *, success: bool, error: str | None = None) -> None:
        key = self._h(job_id)
        self._redis.hincrby(key, "processed", 1)
        self._redis.hincrby(key, "succeeded" if success else "failed", 1)
        if error:
            self._push_error(job_id, error)

    def add_error(self, job_id: uuid.UUID, msg: str) -> None:
        self._push_error(job_id, msg)

    def _push_error(self, job_id: uuid.UUID, msg: str) -> None:
        errors_key = self._e(job_id)
        # Cap the list and keep it aligned with the hash's TTL.
        pipe = self._redis.pipeline()
        pipe.rpush(errors_key, msg)
        pipe.ltrim(errors_key, 0, _ERROR_CAP - 1)
        pipe.expire(errors_key, self._ttl)
        pipe.execute()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def build_job_store() -> JobStore:
    redis = get_redis()
    if redis is not None:
        return RedisJobStore(redis)
    return InProcessJobStore()


# Module-level singleton.
job_store: JobStore = build_job_store()
