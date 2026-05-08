"""Middleware that attaches request context and records metrics (from P2)."""

from __future__ import annotations

import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from yourrag_gateway.core.logging import get_logger
from yourrag_gateway.core.request_context import RequestContext, clear_request_context, set_request_context
from yourrag_gateway.observability.metrics import get_metrics_registry
from yourrag_gateway.observability.telemetry import resolve_trace_id, start_span

logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started = time.perf_counter()
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        status_code = 500
        with start_span(
            "http.request",
            kind="server",
            attributes={"http.method": request.method, "http.path": request.url.path, "request_id": request_id},
        ) as span:
            trace_id = request.headers.get("X-Trace-Id") or resolve_trace_id()
            set_request_context(RequestContext(request_id=request_id, trace_id=trace_id))
            try:
                response = await call_next(request)
                status_code = response.status_code
                response.headers["X-Request-Id"] = request_id
                response.headers["X-Trace-Id"] = trace_id
                return response
            finally:
                latency_ms = (time.perf_counter() - started) * 1000.0
                get_metrics_registry().record_http_request(
                    method=request.method, path=request.url.path,
                    status_code=status_code, latency_ms=latency_ms,
                )
                if span is not None:
                    span.set_attribute("http.status_code", status_code)
                    span.set_attribute("http.latency_ms", round(latency_ms, 4))
                    span.set_attribute("trace_id", trace_id)
                clear_request_context()
