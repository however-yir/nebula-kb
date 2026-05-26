# coding=utf-8

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .action import ToolHarnessAction
from .sanitizer import sanitize_parameters


def _utc_iso(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


@dataclass
class ToolObservation:
    action: ToolHarnessAction | str
    workspace_id: str | None = None
    tool_id: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    record_id: str | None = None
    input: Any = None
    output: Any = None
    status: str = "started"
    error_type: str | None = None
    error_message: str | None = None
    started_at: float = field(default_factory=time.time)
    ended_at: float | None = None

    def finish_success(self, output: Any = None) -> "ToolObservation":
        self.status = "success"
        self.output = output
        self.ended_at = time.time()
        return self

    def finish_failure(self, exc: Exception) -> "ToolObservation":
        self.status = "failure"
        self.error_type = exc.__class__.__name__
        self.error_message = str(exc)
        self.output = "Error: " + str(exc)
        self.ended_at = time.time()
        return self

    @property
    def run_time(self) -> float:
        end_time = self.ended_at if self.ended_at is not None else time.time()
        return end_time - self.started_at

    def to_meta(self) -> dict:
        meta = {
            "input": sanitize_parameters(self.input),
            "output": sanitize_parameters(self.output),
            "harness": {
                "action": self.action.value if isinstance(self.action, ToolHarnessAction) else self.action,
                "status": self.status,
                "started_at": _utc_iso(self.started_at),
                "ended_at": _utc_iso(self.ended_at),
                "duration_ms": int(self.run_time * 1000),
                "error": None,
            },
        }
        if self.error_message:
            meta["err_message"] = self.error_message
            meta["harness"]["error"] = {
                "type": self.error_type,
                "message": self.error_message,
            }
        return meta

    def to_dict(self) -> dict:
        return {
            "id": self.record_id,
            "workspace_id": self.workspace_id,
            "tool_id": self.tool_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "state": self.status,
            "run_time": self.run_time,
            "meta": self.to_meta(),
        }
