"""Queue backend factory (from P2)."""

from __future__ import annotations

from yourrag_gateway.core.logging import get_logger
from yourrag_gateway.core.settings import YourRAGSettings
from yourrag_gateway.queue.base import QueueBackend
from yourrag_gateway.queue.redis_queue import RedisQueueBackend
from yourrag_gateway.queue.sqlite_queue import SqliteQueueBackend

logger = get_logger(__name__)


def build_queue_backend(settings: YourRAGSettings) -> QueueBackend:
    backend = settings.ingestion_queue_backend.strip().lower()
    if backend == "redis":
        if not settings.redis_url:
            logger.warning("QUEUE_BACKEND_FALLBACK | requested=redis | reason=missing REDIS_URL | using=sqlite")
            return SqliteQueueBackend()
        try:
            return RedisQueueBackend(settings.redis_url)
        except Exception as exc:
            logger.warning("QUEUE_BACKEND_FALLBACK | requested=redis | reason=%s | using=sqlite", exc)
            return SqliteQueueBackend()
    return SqliteQueueBackend()
