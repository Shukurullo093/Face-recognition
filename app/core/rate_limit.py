"""Rate limiting: slowapi (per-IP, global) + a small per-API-key limiter.

The per-key limiter is a plain fixed-window counter used as a FastAPI dependency
for the external/enroll endpoints — slowapi's decorator mangles the route
signature when combined with File/dependency params, so we avoid it there.

Both the global slowapi limiter and the per-key limiter use Redis when
``REDIS_URL`` is set (shared across workers/replicas); otherwise they fall back
to per-worker in-process counters — correct only for a single worker.
"""
from __future__ import annotations

import threading
import time
from typing import Protocol

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import get_redis

log = get_logger(__name__)

# Global per-IP limiter. With a Redis storage_uri slowapi shares the window
# across workers; None falls back to its in-memory storage.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT],
    headers_enabled=True,
    storage_uri=settings.REDIS_URL or None,
)


def exempt_from_global_limit(func):
    """Mark a route exempt from slowapi's global per-IP limit WITHOUT wrapping it.

    `limiter.exempt` wraps the endpoint in a `(*a, **k)` shim, which erases the
    Form()/File()/Depends markers FastAPI reads off the signature (turning body
    params into required query params -> 422). We register the route name on the
    limiter directly instead, so the function is returned untouched.
    """
    limiter._exempt_routes.add(f"{func.__module__}.{func.__name__}")
    return func


def parse_rate(spec: str) -> tuple[int, float]:
    """Parse a "N/period" spec into (limit, window_seconds). Defaults to per-minute."""
    try:
        count, _, period = spec.partition("/")
        limit = int(count.strip())
    except ValueError:
        return 60, 60.0
    window = {"second": 1.0, "minute": 60.0, "hour": 3600.0}.get(period.strip().lower(), 60.0)
    return limit, window


class KeyRateLimiter(Protocol):
    """Fixed-window per-key limiter. `allow` returns False when the key is over budget."""

    def allow(self, key: str, limit: int, window: float) -> bool: ...


class InProcessKeyRateLimiter:
    """Fixed-window per-key counter held in memory. Thread-safe, per-worker."""

    def __init__(self) -> None:
        self._buckets: dict[str, list[float]] = {}  # key -> [window_start, count]
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window: float) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None or now - bucket[0] >= window:
                self._buckets[key] = [now, 1]
                return True
            if bucket[1] >= limit:
                return False
            bucket[1] += 1
            return True


class RedisKeyRateLimiter:
    """Fixed-window per-key counter in Redis (INCR + EXPIRE). Shared across workers.

    The window is a single key with a TTL: the first hit creates it and sets the
    expiry, subsequent hits increment until it expires. On any Redis error we
    fail open (allow) so a Redis blip degrades availability of the limit, not of
    the endpoint.
    """

    _PREFIX = "fr:ratelimit:"

    def __init__(self, redis) -> None:
        self._redis = redis

    def allow(self, key: str, limit: int, window: float) -> bool:
        bucket = f"{self._PREFIX}{key}"
        try:
            current = self._redis.incr(bucket)
            if current == 1 or self._redis.ttl(bucket) < 0:
                self._redis.expire(bucket, max(1, int(window)))
            return current <= limit
        except Exception as exc:  # noqa: BLE001 — fail open on Redis trouble
            log.error("ratelimit_redis_error_failing_open", error=str(exc))
            return True


def build_key_rate_limiter() -> KeyRateLimiter:
    """Redis-backed limiter when Redis is available, else an in-process one."""
    redis = get_redis()
    if redis is not None:
        return RedisKeyRateLimiter(redis)
    return InProcessKeyRateLimiter()


# Per-API-key limiter for /external/search.
external_rate_limiter: KeyRateLimiter = build_key_rate_limiter()

# Per-IP limiter for /faces/enroll. The endpoint takes File/Form params, so we
# can't use slowapi's decorator; the route is exempted from the global slowapi
# limit and this is applied as a dependency instead.
enroll_rate_limiter: KeyRateLimiter = build_key_rate_limiter()
