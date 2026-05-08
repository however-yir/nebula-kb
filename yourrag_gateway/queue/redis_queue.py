"""Redis queue backend with delayed retries and dead-letter (from P2)."""

from __future__ import annotations

from datetime import datetime, timezone
import time

from yourrag_gateway.core.logging import get_logger
from yourrag_gateway.queue.base import QueueJobRef

logger = get_logger(__name__)


def _to_unix(moment: datetime) -> float:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc).timestamp()
    return moment.timestamp()


class RedisQueueBackend:
    name = "redis"

    def __init__(self, redis_url: str, queue_name: str = "ingestion_jobs") -> None:
        self.queue_name = queue_name
        self.ready_key = f"queue:{queue_name}:ready"
        self.delayed_key = f"queue:{queue_name}:delayed"
        self.dlq_key = f"queue:{queue_name}:dlq"
        self._client = self._build_client(redis_url)

    def _build_client(self, redis_url: str):
        import redis
        return redis.from_url(redis_url)

    def enqueue(self, *, job_id: str, available_at: datetime | None = None) -> None:
        if available_at is None:
            self._client.rpush(self.ready_key, job_id)
            return
        now = datetime.now(timezone.utc)
        if available_at <= now:
            self._client.rpush(self.ready_key, job_id)
            return
        self._client.zadd(self.delayed_key, {job_id: _to_unix(available_at)})

    def dequeue(self) -> QueueJobRef | None:
        self._promote_due_jobs()
        job_id = self._client.lpop(self.ready_key)
        if job_id is None:
            return None
        resolved = job_id.decode("utf-8") if isinstance(job_id, bytes) else str(job_id)
        return QueueJobRef(job_id=resolved, dequeued_at=datetime.now(timezone.utc))

    def ack(self, *, job_id: str) -> None:
        _ = job_id

    def nack(self, *, job_id: str, retry_at: datetime | None = None, dead_letter: bool = False) -> None:
        if dead_letter:
            self._client.rpush(self.dlq_key, job_id)
            return
        self.enqueue(job_id=job_id, available_at=retry_at)

    def _promote_due_jobs(self) -> None:
        now_score = str(time.time())
        job_ids = self._client.zrangebyscore(self.delayed_key, min="-inf", max=now_score)
        if not job_ids:
            return
        pipe = self._client.pipeline()
        for raw in job_ids:
            job_id = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
            pipe.rpush(self.ready_key, job_id)
            pipe.zrem(self.delayed_key, job_id)
        pipe.execute()
