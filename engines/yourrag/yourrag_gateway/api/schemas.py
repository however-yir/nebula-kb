"""Unified API schemas (merged P1 + P2 + P3)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Health ───────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    mode: str = "live"
    engine: str = "yourrag"


# ── Auth (P2) ───────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class PrincipalResponse(BaseModel):
    actor_id: str
    actor_name: str
    actor_type: str
    roles: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    auth_type: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    principal: PrincipalResponse


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(default="default", min_length=1)


class ApiKeyCreateResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    api_key: str


# ── RAG Search ───────────────────────────────────────────────────────
class SearchHit(BaseModel):
    content: str
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory={})


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=4, ge=1, le=100)
    department: str | None = None
    knowledge_base: str = "default"


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]


# ── Document Upload ─────────────────────────────────────────────────
class UploadResponse(BaseModel):
    doc_id: str
    chunks_indexed: int
    filename: str


# ── Chat / Agent ────────────────────────────────────────────────────
class AgentStep(BaseModel):
    step: int
    thought: str = ""
    action: str = ""
    action_input: dict[str, Any] = Field(default_factory=dict)
    observation: Any = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, alias="query")
    user_id: str = "anonymous"
    session_id: str | None = None
    department: str | None = None
    mode: Literal["live", "mock"] = "live"
    knowledge_base: str = "default"

    model_config = {"populate_by_name": True}


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    trace: list[AgentStep] = Field(default_factory=list)
    retrieval_preview: list[SearchHit] = Field(default_factory=list)
    route: str = "agent"
    evidence: list[SearchHit] = Field(default_factory=list)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Tool listing (P1) ───────────────────────────────────────────────
class ToolDescriptor(BaseModel):
    name: str
    description: str
    required_params: list[str] = Field(default_factory=list)


# ── Metrics (P2) ────────────────────────────────────────────────────
class MetricsResponse(BaseModel):
    http: dict[str, Any] = Field(default_factory=dict)
    rag: dict[str, Any] = Field(default_factory=dict)
    ingestion_jobs: dict[str, Any] = Field(default_factory=dict)
    prometheus_available: bool = False


# ── Ingestion (P2) ─────────────────────────────────────────────────
class IngestionTextRequest(BaseModel):
    knowledge_base: str = "default"
    source_name: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
