"""Audit logging service (from P2)."""

from __future__ import annotations

import logging
from typing import Any

from yourrag_gateway.auth.models import AuthContext
from yourrag_gateway.core.request_context import get_request_context

logger = logging.getLogger(__name__)


class AuditService:
    """Records audit events — can log to structured logger and/or persist to P3's DB."""

    def __init__(self, repository: Any = None) -> None:
        self.repository = repository

    def record(
        self,
        *,
        principal: AuthContext,
        action: str,
        resource_type: str,
        resource_id: str = "",
        status: str = "success",
        detail: dict[str, object] | None = None,
        ip_address: str = "",
        session_id: str = "",
        job_id: str = "",
    ) -> int:
        context = get_request_context()
        event = {
            "actor_type": principal.actor_type,
            "actor_id": principal.actor_id,
            "actor_name": principal.actor_name,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "status": status,
            "detail": detail or {},
            "request_id": context.request_id,
            "trace_id": context.trace_id,
            "session_id": session_id or context.session_id,
            "job_id": job_id or context.job_id,
            "ip": ip_address,
        }
        logger.info("AUDIT | %s | %s/%s | actor=%s | status=%s", action, resource_type, resource_id, principal.actor_name, status)
        if self.repository is not None:
            return self.repository.add_event(**event)
        return 0
