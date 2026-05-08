"""YourRAG Gateway — unified FastAPI application.

This is the **single entry point** that merges three RAG projects:
  - P1 (springboot-llm-rag-agent-demo): Ollama-first demo + circuit breaker + SSE streaming
  - P2 (rag-agent-production-starter): JWT/RBAC auth + rate limiting + queue + audit + OTEL
  - P3 (yourrag): DeepDoc + Canvas Agent + GraphRAG + multi-vector-store + MCP + SDK

Architecture:
  ┌──────────────────────────────────────┐
  │          FastAPI Gateway (9382)       │
  │  /health, /auth/*, /rag/*, /agent/*  │
  │  /tools, /metrics, /documents/*      │
  └────────────┬─────────────────────────┘
               │ delegates to
  ┌────────────┼─────────────────────────┐
  │  P3 Engine (Quart, 9380)             │
  │  /api/v1/kb, /api/v1/dataset, …     │
  │  Canvas Agent, DeepDoc, GraphRAG     │
  │  MCP Server, Memory, Connectors     │
  └──────────────────────────────────────┘
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from yourrag_gateway.api.dependencies import get_settings
from yourrag_gateway.api.routes import router
from yourrag_gateway.core.logging import configure_logging
from yourrag_gateway.core.settings import YourRAGSettings  # noqa: F401
from yourrag_gateway.middleware.request_context import RequestContextMiddleware
from yourrag_gateway.observability.telemetry import setup_open_telemetry


@asynccontextmanager
async def lifespan(application: FastAPI):
    settings = get_settings()
    setup_open_telemetry(settings)
    # TODO: Start P2's ingestion worker if enabled
    # TODO: Start P3's Quart engine in a thread if co-deployed
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(level=settings.log_level, use_json=settings.log_json)

    application = FastAPI(
        title="YourRAG Gateway",
        version=settings.app_version,
        description=(
            "Unified RAG Gateway — merging demo (P1), production starter (P2), "
            "and private deployment engine (P3) into one toolkit."
        ),
        lifespan=lifespan,
    )

    # CORS (from P3)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request context + metrics middleware (from P2)
    application.add_middleware(RequestContextMiddleware)

    # Register unified routes
    application.include_router(router, prefix="/api/v1")

    # Mount P3's existing Quart app if available (proxy or sub-app)
    _mount_p3_engine(application)

    return application


def _mount_p3_engine(application: FastAPI) -> None:
    """Optionally mount P3's Quart-based API engine as a sub-application."""
    try:
        from api.apps import app as quart_app  # type: ignore
        from asgiref.wsgi import WsgiToAsgi  # type: ignore  # noqa: F401
        # Quart is ASGI-native, mount directly
        application.mount("/engine", quart_app)  # type: ignore
    except ImportError:
        # P3 engine not available — gateway runs standalone
        pass


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "yourrag_gateway.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
