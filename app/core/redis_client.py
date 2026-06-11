"""Shared, lazily-created Redis client used by the job store and rate limiters.

`get_redis()` returns a process-wide synchronous client (redis-py is thread-safe
and pools connections internally) when ``REDIS_URL`` is configured and reachable,
otherwise ``None`` — callers then fall back to their in-process implementations.

The connection is attempted once; on failure we log loudly and keep returning
``None`` so the app still boots (degraded to per-worker state) rather than
crash-looping on a transient Redis outage.
"""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from app.core.config import settings
from app.core.logging import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from redis import Redis

log = get_logger(__name__)

_client: Any = None
_attempted = False
_lock = threading.Lock()


def get_redis() -> "Redis | None":
    """Return the shared Redis client, or None when Redis is unconfigured/unreachable."""
    global _client, _attempted

    if not settings.REDIS_URL:
        return None
    if _attempted:
        return _client

    with _lock:
        if _attempted:
            return _client
        _attempted = True
        try:
            import redis  # imported lazily so the dep is optional without REDIS_URL

            client = redis.Redis.from_url(
                settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2
            )
            client.ping()
            _client = client
            log.info("redis_connected")
        except Exception as exc:  # noqa: BLE001 — any failure -> in-process fallback
            _client = None
            log.error(
                "redis_unavailable_falling_back_to_in_process",
                error=str(exc),
                hint="distributed state disabled; run a single worker or fix REDIS_URL",
            )
    return _client


def reset_redis_client() -> None:
    """Drop the cached client/attempt flag (used by tests)."""
    global _client, _attempted
    with _lock:
        _client = None
        _attempted = False
