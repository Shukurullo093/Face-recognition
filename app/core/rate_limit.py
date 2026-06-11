"""Rate limiting: slowapi (per-IP, global) + a small per-API-key limiter.

The per-key limiter is a plain in-process fixed-window counter used as a FastAPI
dependency for the external endpoint — slowapi's decorator mangles the route
signature when combined with File/dependency params, so we avoid it there.
Note: in-process state is per-worker; use Redis-backed limits for multi-replica.
"""
from __future__ import annotations

import threading
import time

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT],
    headers_enabled=True,
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


class KeyRateLimiter:
    """Fixed-window per-key counter. Thread-safe."""

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


external_rate_limiter = KeyRateLimiter()

# Per-IP limiter for /faces/enroll. The endpoint takes File/Form params, so we can't
# use slowapi's decorator (it mangles the route signature); instead the route is
# exempted from the global slowapi limit and this is applied as a dependency.
enroll_rate_limiter = KeyRateLimiter()
