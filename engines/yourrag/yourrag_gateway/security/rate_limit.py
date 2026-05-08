"""Rate limiter with in-memory + Redis backends (from P2)."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time

from yourrag_gateway.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, tuple[int, int]] = {}

    def check(self, *, key: str, limit: int, window_seconds: int = 60) -> RateLimitResult:
        now = int(time.time())
        window_start = now - (now % window_seconds)
        storage_key = f"{key}:{window_start}"
        with self._lock:
            count, stored_window = self._counters.get(storage_key, (0, window_start))
            if stored_window != window_start:
                count = 0
            next_count = count + 1
            self._counters[storage_key] = (next_count, window_start)
        allowed = next_count <= limit
        remaining = max(limit - next_count, 0)
        retry_after = max(window_seconds - (now - window_start), 1)
        return RateLimitResult(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            retry_after_seconds=retry_after if not allowed else 0,
        )


class RedisRateLimiter:
    def __init__(self, redis_url: str) -> None:
        self.redis_url = redis_url
        self._client = self._build_client(redis_url)

    def _build_client(self, redis_url: str):
        import redis  # type: ignore
        return redis.from_url(redis_url)

    def check(self, *, key: str, limit: int, window_seconds: int = 60) -> RateLimitResult:
        now = int(time.time())
        window_start = now - (now % window_seconds)
        redis_key = f"rate_limit:{key}:{window_start}"
        pipe = self._client.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, window_seconds)
        count, _ = pipe.execute()
        count_value = int(count)
        allowed = count_value <= limit
        remaining = max(limit - count_value, 0)
        retry_after = max(window_seconds - (now - window_start), 1)
        return RateLimitResult(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            retry_after_seconds=retry_after if not allowed else 0,
        )


class RateLimiter:
    """Facade that uses Redis when available, falls back to in-memory."""

    def __init__(self, redis_url: str = "") -> None:
        self._fallback = InMemoryRateLimiter()
        self._backend = "memory"
        if redis_url:
            try:
                self._redis = RedisRateLimiter(redis_url)
                self._backend = "redis"
            except Exception as exc:
                self._redis = None
                logger.warning("RATE_LIMITER_REDIS_DISABLED | error=%s", exc)
        else:
            self._redis = None

    @property
    def backend(self) -> str:
        return self._backend

    def check(self, *, key: str, limit: int, window_seconds: int = 60) -> RateLimitResult:
        if self._redis is not None:
            try:
                return self._redis.check(key=key, limit=limit, window_seconds=window_seconds)
            except Exception as exc:
                logger.warning("RATE_LIMITER_REDIS_ERROR | error=%s", exc)
        return self._fallback.check(key=key, limit=limit, window_seconds=window_seconds)
