"""In-memory metrics registry + Prometheus (from P2)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import re
from threading import Lock
from typing import Any

from yourrag_gateway.core.logging import get_logger

logger = get_logger(__name__)

try:
    from prometheus_client import Counter, Histogram, generate_latest
    _PROMETHEUS_AVAILABLE = True
except Exception:
    Counter = None  # type: ignore
    Histogram = None  # type: ignore
    generate_latest = None  # type: ignore
    _PROMETHEUS_AVAILABLE = False


if _PROMETHEUS_AVAILABLE:
    _HTTP_REQUEST_COUNTER = Counter(
        "http_requests_total", "HTTP request totals", ["method", "path", "status_code"],
    )
    _HTTP_REQUEST_LATENCY = Histogram(
        "http_request_latency_ms", "HTTP request latency in milliseconds", ["method", "path"],
    )
    _RAG_CALL_COUNTER = Counter("rag_call_total", "Total RAG calls")
    _RAG_HIT_COUNTER = Counter("rag_hit_total", "RAG calls with hits")
    _INGESTION_JOB_COUNTER = Counter(
        "ingestion_job_total", "Ingestion job transitions", ["status", "backend"],
    )
else:
    _HTTP_REQUEST_COUNTER = None
    _HTTP_REQUEST_LATENCY = None
    _RAG_CALL_COUNTER = None
    _RAG_HIT_COUNTER = None
    _INGESTION_JOB_COUNTER = None


@dataclass(slots=True)
class LatencyAggregate:
    count: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0

    def record(self, latency_ms: float) -> None:
        self.count += 1
        self.total_ms += latency_ms
        self.max_ms = max(self.max_ms, latency_ms)

    def snapshot(self) -> dict[str, float]:
        average = self.total_ms / self.count if self.count else 0.0
        return {"count": float(self.count), "avg_ms": round(average, 4), "max_ms": round(self.max_ms, 4)}


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._http_requests: dict[str, int] = defaultdict(int)
        self._http_latencies: dict[str, LatencyAggregate] = defaultdict(LatencyAggregate)
        self._rag_hits: list[int] = []
        self._ingestion_jobs: dict[str, int] = defaultdict(int)

    def record_http_request(self, *, method: str, path: str, status_code: int, latency_ms: float) -> None:
        normalized_path = normalize_http_path(path)
        key = f"{method.upper()} {normalized_path} {status_code}"
        latency_key = f"{method.upper()} {normalized_path}"
        with self._lock:
            self._http_requests[key] += 1
            self._http_latencies[latency_key].record(latency_ms)
        if _HTTP_REQUEST_COUNTER is not None:
            _HTTP_REQUEST_COUNTER.labels(method=method.upper(), path=normalized_path, status_code=str(status_code)).inc()
        if _HTTP_REQUEST_LATENCY is not None:
            _HTTP_REQUEST_LATENCY.labels(method=method.upper(), path=normalized_path).observe(latency_ms)

    def record_rag_hit(self, evidence_count: int) -> None:
        with self._lock:
            self._rag_hits.append(evidence_count)
        if _RAG_CALL_COUNTER is not None:
            _RAG_CALL_COUNTER.inc()
        if evidence_count > 0 and _RAG_HIT_COUNTER is not None:
            _RAG_HIT_COUNTER.inc()

    def record_ingestion_job(self, *, status: str, backend: str) -> None:
        key = f"{backend.lower()}:{status.lower()}"
        with self._lock:
            self._ingestion_jobs[key] += 1
        if _INGESTION_JOB_COUNTER is not None:
            _INGESTION_JOB_COUNTER.labels(status=status.lower(), backend=backend.lower()).inc()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            total_rag_calls = len(self._rag_hits)
            total_rag_hits = sum(1 for c in self._rag_hits if c > 0)
            return {
                "http": {
                    "requests": dict(self._http_requests),
                    "latency": {name: agg.snapshot() for name, agg in self._http_latencies.items()},
                },
                "rag": {
                    "calls": total_rag_calls,
                    "hits": total_rag_hits,
                    "hit_rate": round(total_rag_hits / total_rag_calls, 4) if total_rag_calls else 0.0,
                },
                "ingestion_jobs": dict(self._ingestion_jobs),
                "prometheus_available": _PROMETHEUS_AVAILABLE,
            }

    def prometheus_text(self) -> str:
        if generate_latest is None:
            return "# Prometheus client is not installed.\n"
        return generate_latest().decode("utf-8")


_REGISTRY = MetricsRegistry()


def get_metrics_registry() -> MetricsRegistry:
    return _REGISTRY


def normalize_http_path(path: str) -> str:
    normalized = path.strip() or "/"
    normalized = re.sub(r"/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}", "/{id}", normalized)
    normalized = re.sub(r"/[0-9]+(?=/|$)", "/{id}", normalized)
    return normalized
