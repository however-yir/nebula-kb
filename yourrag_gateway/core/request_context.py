"""Request-scoped context (from P2) — contextvars-based."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
import uuid


@dataclass(slots=True)
class RequestContext:
    request_id: str = ""
    trace_id: str = ""
    session_id: str = ""
    job_id: str = ""
    actor_id: str = ""
    actor_type: str = ""


_CONTEXT: ContextVar[RequestContext] = ContextVar("request_context", default=RequestContext())


def get_request_context() -> RequestContext:
    return _CONTEXT.get()


def set_request_context(context: RequestContext) -> None:
    _CONTEXT.set(context)


def clear_request_context() -> None:
    _CONTEXT.set(RequestContext())


def ensure_ids(request_id: str | None = None, trace_id: str | None = None) -> RequestContext:
    current = get_request_context()
    resolved_request_id = request_id or current.request_id or str(uuid.uuid4())
    resolved_trace_id = trace_id or current.trace_id or str(uuid.uuid4())
    updated = RequestContext(
        request_id=resolved_request_id,
        trace_id=resolved_trace_id,
        session_id=current.session_id,
        job_id=current.job_id,
        actor_id=current.actor_id,
        actor_type=current.actor_type,
    )
    set_request_context(updated)
    return updated
