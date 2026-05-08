"""SQLite queue backend (from P2) — polling-based, no external broker."""

from __future__ import annotations

from datetime import datetime

from yourrag_gateway.queue.base import QueueJobRef


class SqliteQueueBackend:
    name = "sqlite"

    def enqueue(self, *, job_id: str, available_at: datetime | None = None) -> None:
        _ = job_id, available_at  # Relies on DB polling

    def dequeue(self) -> QueueJobRef | None:
        return None

    def ack(self, *, job_id: str) -> None:
        _ = job_id

    def nack(self, *, job_id: str, retry_at: datetime | None = None, dead_letter: bool = False) -> None:
        _ = job_id, retry_at, dead_letter
