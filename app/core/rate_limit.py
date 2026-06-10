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
