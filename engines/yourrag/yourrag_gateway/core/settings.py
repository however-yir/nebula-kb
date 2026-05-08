"""Unified configuration for YourRAG Gateway.

Merges:
  - P1: Pydantic BaseSettings (.env) + Ollama/Chroma/Tool configs
  - P2: Dataclass env-driven + JWT/RBAC/Queue/OTEL configs
  - P3: YAML config + multi-LLM/vector-store configs

All settings are read from environment variables with sensible defaults.
PYPROJECT_ROOT/conf/service_conf.yaml is still respected by the P3 engine.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class YourRAGSettings(BaseSettings):
    """Single source of truth for all YourRAG Gateway configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="YOURRAG_",
    )

    # ── App ──────────────────────────────────────────────────────────
    app_name: str = "YourRAG"
    app_host: str = "0.0.0.0"
    app_port: int = 9382
    app_version: str = "1.0.0"
    log_level: str = "INFO"
    log_json: bool = True
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # ── LLM (P1 Ollama + P2 OpenAI + P3 LiteLLM) ────────────────────
    llm_provider: Literal["ollama", "openai", "litellm"] = "litellm"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1"
    embedding_model: str = "text-embedding-3-large"
    embedding_dimension: int = 1024

    # ── Vector Store (P1 Chroma + P2 Pinecone/SQLite + P3 ES/Infinity/OB) ──
    vector_store_backend: Literal["chroma", "sqlite", "pinecone", "elasticsearch", "infinity", "oceanbase", "opensearch"] = "elasticsearch"
    chroma_dir: str = "./data/chroma"
    chroma_collection: str = "yourrag_docs"
    pinecone_api_key: str = ""
    pinecone_index_name: str = "yourrag"
    retrieval_top_k: int = 4

    # ── RAG Pipeline ─────────────────────────────────────────────────
    chunk_size: int = 700
    chunk_overlap: int = 80

    # ── Agent (P1 ReAct + P3 Canvas) ─────────────────────────────────
    agent_mode: Literal["react", "canvas"] = "canvas"
    max_agent_steps: int = 5

    # ── P1: Tool Executor with Circuit Breaker ───────────────────────
    tool_timeout_seconds: int = 8
    tool_retry_attempts: int = 2
    tool_retry_backoff_seconds: float = 0.4
    tool_circuit_breaker_threshold: int = 3
    tool_circuit_breaker_cooldown_seconds: int = 30

    # ── P1: SSE Streaming ────────────────────────────────────────────
    sse_chunk_size: int = 14

    # ── P1: Session Memory (JSON file fallback) ──────────────────────
    memory_path: str = "./data/session_memory.json"

    # ── P2: Ingestion Queue ──────────────────────────────────────────
    ingestion_queue_backend: Literal["sqlite", "redis"] = "sqlite"
    ingestion_max_retries: int = 3
    ingestion_retry_backoff_seconds: int = 2
    ingestion_retry_max_backoff_seconds: int = 120
    ingestion_worker_poll_seconds: float = 1.0
    ingestion_worker_batch_size: int = 5
    ingestion_embedded_worker_enabled: bool = True

    # ── P2: JWT + RBAC Auth ──────────────────────────────────────────
    security_enabled: bool = True
    jwt_secret: str = "change-me-in-production"
    jwt_issuer: str = "yourrag"
    jwt_access_token_exp_minutes: int = 60
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: str = "admin123"

    # ── P2: Rate Limiting ────────────────────────────────────────────
    rate_limit_per_minute: int = 120

    # ── P2: Tavily Search ────────────────────────────────────────────
    tavily_api_key: str = ""
    tavily_max_results: int = 3

    # ── P2/P3: Redis ─────────────────────────────────────────────────
    redis_url: str = ""

    # ── P2: Observability ────────────────────────────────────────────
    prometheus_enabled: bool = True
    open_telemetry_enabled: bool = False
    open_telemetry_logs_enabled: bool = False
    otel_exporter_otlp_endpoint: str = ""
    otel_exporter_otlp_logs_endpoint: str = ""
    otel_service_name: str = "yourrag"
    otel_service_environment: str = "dev"

    # ── P2: Mock / Live Toggle ──────────────────────────────────────
    use_mock_services: bool = False
    enable_langgraph_agent: bool = True
    enable_langgraph_rag: bool = True

    # ── P3: Database ─────────────────────────────────────────────────
    database_path: str = "data/yourrag.db"

    # ── P3: Encryption at Rest ──────────────────────────────────────
    crypto_enabled: bool = False
    crypto_secret_key: str = ""

    # ── Computed helpers ─────────────────────────────────────────────
    @property
    def live_llm_ready(self) -> bool:
        if self.llm_provider == "ollama":
            return True  # always try local
        return bool(self.openai_api_key)

    @property
    def live_search_ready(self) -> bool:
        return bool(self.tavily_api_key)

    @property
    def live_vector_store_ready(self) -> bool:
        if self.vector_store_backend in ("chroma", "sqlite", "elasticsearch", "infinity", "oceanbase", "opensearch"):
            return True  # self-hosted backends
        return bool(self.pinecone_api_key and self.openai_api_key)


def get_settings() -> YourRAGSettings:
    """Return cached settings instance (fastapi Depends-friendly)."""
    return YourRAGSettings()
