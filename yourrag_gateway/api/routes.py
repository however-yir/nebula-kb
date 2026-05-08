"""Unified API routes (merged P1 + P2 + P3).

This module provides a FastAPI router that bridges into:
  - P3's existing Quart-based API engine (knowledge bases, documents, chunks, canvas, etc.)
  - P2's production endpoints (auth, metrics, audit)
  - P1's demo endpoints (tools, SSE streaming, simple RAG)
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from yourrag_gateway.api.dependencies import (
    get_audit_service,
    get_auth_service,
    get_current_principal,
    get_settings,
    require_permissions,
)
from yourrag_gateway.api.schemas import (
    SearchHit,
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    LoginRequest,
    LoginResponse,
    MetricsResponse,
    PrincipalResponse,
    SearchRequest,
    SearchResponse,
    ToolDescriptor,
    UploadResponse,
)
from yourrag_gateway.audit.service import AuditService
from yourrag_gateway.auth.models import AuthContext
from yourrag_gateway.auth.service import AuthService
from yourrag_gateway.core.settings import YourRAGSettings
from yourrag_gateway.observability.metrics import get_metrics_registry

router = APIRouter()


# ── Health ───────────────────────────────────────────────────────────
@router.get("/health", response_model=HealthResponse)
def health(settings: YourRAGSettings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        mode="mock" if settings.use_mock_services else "live",
        engine="yourrag",
    )


# ── Auth (P2) ───────────────────────────────────────────────────────
@router.post("/auth/login", response_model=LoginResponse, tags=["auth"])
def login(
    payload: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> LoginResponse:
    result = auth_service.login_with_password(username=payload.username, password=payload.password)
    audit_service.record(
        principal=result.context, action="auth.login", resource_type="token",
        status="success", detail={"username": payload.username}, ip_address=request.client.host if request.client else "",
    )
    return LoginResponse(
        access_token=result.access_token, token_type=result.token_type,
        expires_in_seconds=result.expires_in_seconds,
        principal=PrincipalResponse(
            actor_id=result.context.actor_id, actor_name=result.context.actor_name,
            actor_type=result.context.actor_type, roles=result.context.roles,
            permissions=result.context.permissions, auth_type=result.context.auth_type,
        ),
    )


@router.get("/auth/me", response_model=PrincipalResponse, tags=["auth"])
def me(principal: AuthContext = Depends(get_current_principal)) -> PrincipalResponse:
    return PrincipalResponse(
        actor_id=principal.actor_id, actor_name=principal.actor_name,
        actor_type=principal.actor_type, roles=principal.roles,
        permissions=principal.permissions, auth_type=principal.auth_type,
    )


@router.post(
    "/auth/api-keys",
    response_model=ApiKeyCreateResponse,
    dependencies=[Depends(require_permissions("auth:manage_api_keys"))],
    tags=["auth"],
)
def create_api_key(
    payload: ApiKeyCreateRequest,
    request: Request,
    principal: AuthContext = Depends(get_current_principal),
    auth_service: AuthService = Depends(get_auth_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> ApiKeyCreateResponse:
    created = auth_service.create_api_key(actor_id=principal.actor_id, name=payload.name)
    audit_service.record(
        principal=principal, action="auth.create_api_key", resource_type="api_key",
        resource_id=created["id"], status="success",
        detail={"name": payload.name, "prefix": created["key_prefix"]},
        ip_address=request.client.host if request.client else "",
    )
    return ApiKeyCreateResponse.model_validate(created)


# ── Tools (P1) ──────────────────────────────────────────────────────
@router.get("/tools", response_model=list[ToolDescriptor], tags=["tools"])
def list_tools() -> list[ToolDescriptor]:
    """List all registered tools (P3's 20+ tools + P1's demo tools)."""
    try:
        from agent.tools import base as agent_tools_base
        return [
            ToolDescriptor(name=name, description=getattr(fn, "__doc__", "") or "", required_params=[])
            for name, fn in agent_tools_base.TOOLS.items()
        ]
    except ImportError:
        return []


# ── RAG Search ───────────────────────────────────────────────────────
@router.post("/rag/search", response_model=SearchResponse, tags=["rag"])
def rag_search(request: SearchRequest) -> SearchResponse:
    """Unified RAG search — delegates to P3's dealer retriever or P1/P2 fallback."""
    try:
        from rag.nlp.search import dealer
        # Use P3's advanced retriever
        hits = dealer(request.query, kb_name=request.knowledge_base, topn=request.top_k)
        return SearchResponse(
            query=request.query,
            hits=[SearchHit(content=h.get("content", ""), score=h.get("score", 0.0), metadata=h.get("metadata", {})) for h in hits],
        )
    except ImportError:
        # Fallback: return empty when P3 engine is not available
        return SearchResponse(query=request.query, hits=[])


# ── Document Upload ─────────────────────────────────────────────────
@router.post("/documents/upload", response_model=UploadResponse, tags=["ingestion"])
async def upload_document(
    file: UploadFile = File(...),
    department: str | None = Form(default=None),
) -> UploadResponse:
    try:
        payload = await file.read()
        # Delegate to P3's ingestion pipeline
        try:
            from rag.app.import_wrapper import import_document
            doc_id, chunk_count = import_document(filename=file.filename, payload=payload, department=department)
        except ImportError:
            doc_id, chunk_count = f"local-{len(payload)}", 0
        return UploadResponse(doc_id=doc_id, chunks_indexed=chunk_count, filename=file.filename or "unknown")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Chat / Agent (P1 ReAct + P3 Canvas) ────────────────────────────
@router.post("/agent/chat", response_model=ChatResponse, tags=["agent"])
def chat(request: ChatRequest) -> ChatResponse:
    """Unified agent chat — uses P3 Canvas or P1 ReAct fallback."""
    try:
        from agent.canvas import Canvas  # noqa: F401
        # TODO: Wire canvas execution per P3's flow
        return ChatResponse(session_id=request.session_id or "new", answer="Canvas agent not yet wired through gateway.", route="canvas")
    except ImportError:
        pass
    try:
        from yourrag_gateway.agent.react.service import react_agent_service
        return react_agent_service.run(request)
    except ImportError:
        return ChatResponse(session_id=request.session_id or "new", answer="No agent backend available.", route="none")


def _sse_event(event: str, data: dict[str, Any] | str) -> str:
    if isinstance(data, dict):
        payload = json.dumps(data, ensure_ascii=False)
    else:
        payload = data
    return f"event: {event}\ndata: {payload}\n\n"


def _chunk_text(text: str, size: int) -> list[str]:
    if size <= 0:
        return [text]
    return [text[i:i + size] for i in range(0, len(text), size)]


@router.post("/agent/chat/stream", tags=["agent"])
async def chat_stream(request: ChatRequest, settings: YourRAGSettings = Depends(get_settings)) -> StreamingResponse:
    """SSE streaming (from P1) — tokens streamed with trace events."""
    response = await asyncio.to_thread(chat, request)

    async def event_generator():
        for step in response.trace:
            yield _sse_event("trace", step.model_dump())
            await asyncio.sleep(0)
        for token in _chunk_text(response.answer, settings.sse_chunk_size):
            yield _sse_event("token", {"text": token})
            await asyncio.sleep(0.02)
        yield _sse_event("done", {"session_id": response.session_id})

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})


# ── Metrics (P2) ────────────────────────────────────────────────────
@router.get("/metrics", response_model=MetricsResponse, tags=["observability"])
def metrics() -> MetricsResponse:
    snapshot = get_metrics_registry().snapshot()
    return MetricsResponse(**snapshot)


@router.get("/metrics/prometheus", tags=["observability"])
def prometheus_metrics():
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(get_metrics_registry().prometheus_text(), media_type="text/plain; version=0.0.4; charset=utf-8")


# ── Proxy to P3 Engine ──────────────────────────────────────────────
# All P3 routes (KB, Document, Chunk, Canvas, LLM, etc.) are available
# via P3's existing Quart app on port 9380. The gateway proxies to it
# for /api/v1/* paths, or they can be accessed directly.
