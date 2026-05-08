"""Queue interface abstractions (from P2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(slots=True)
class QueueJobRef:
    job_id: str
    dequeued_at: datetime


class QueueBackend(Protocol):
    name: str

    def enqueue(self, *, job_id: str, available_at: datetime | None = None) -> None: ...
    def dequeue(self) -> QueueJobRef | None: ...
    def ack(self, *, job_id: str) -> None: ...
    def nack(self, *, job_id: str, retry_at: datetime | None = None, dead_letter: bool = False) -> None: ...
