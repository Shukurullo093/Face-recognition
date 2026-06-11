"""Behaviour of the in-process job store + key rate limiter (Redis backends use
the same contract, exercised in deployment)."""
from __future__ import annotations

from app.core.rate_limit import InProcessKeyRateLimiter
from app.services.job_store import InProcessJobStore


def test_job_store_records_outcomes_and_errors():
    store = InProcessJobStore()
    job = store.create()
    assert store.get(job.job_id).state == "pending"

    store.mark_running(job.job_id, total=3)
    store.record(job.job_id, success=True)
    store.record(job.job_id, success=True)
    store.record(job.job_id, success=False, error="img.jpg: boom")
    store.mark_finished(job.job_id)

    snap = store.get(job.job_id)
    assert snap.state == "completed"
    assert (snap.total, snap.processed, snap.succeeded, snap.failed) == (3, 3, 2, 1)
    assert snap.errors == ["img.jpg: boom"]
    assert snap.started_at is not None and snap.finished_at is not None


def test_job_store_caps_errors_and_handles_missing():
    store = InProcessJobStore()
    job = store.create()
    for i in range(150):
        store.add_error(job.job_id, f"err {i}")
    assert len(store.get(job.job_id).errors) == 100  # capped

    import uuid

    assert store.get(uuid.uuid4()) is None  # unknown job


def test_in_process_rate_limiter_enforces_window():
    rl = InProcessKeyRateLimiter()
    assert [rl.allow("ip", 2, 60) for _ in range(3)] == [True, True, False]
    # Independent keys have independent budgets.
    assert rl.allow("other-ip", 2, 60) is True
