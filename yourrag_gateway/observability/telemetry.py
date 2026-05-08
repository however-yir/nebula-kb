"""OpenTelemetry integration (from P2)."""

from __future__ import annotations

from contextlib import contextmanager
import logging
from typing import Iterator, Mapping
import uuid

from yourrag_gateway.core.logging import get_logger
from yourrag_gateway.core.settings import YourRAGSettings

logger = get_logger(__name__)

_TELEMETRY_READY = False


def setup_open_telemetry(settings: YourRAGSettings) -> None:
    global _TELEMETRY_READY
    if _TELEMETRY_READY:
        return
    if not settings.open_telemetry_enabled and not settings.open_telemetry_logs_enabled:
        return
    resource = _build_resource(settings)
    configured = False
    if settings.open_telemetry_enabled:
        configured = _configure_trace_export(settings, resource) or configured
    if settings.open_telemetry_logs_enabled:
        configured = _configure_log_export(settings, resource) or configured
    _TELEMETRY_READY = configured


def _build_resource(settings: YourRAGSettings):
    from opentelemetry.sdk.resources import Resource
    return Resource.create({
        "service.name": settings.otel_service_name,
        "deployment.environment": settings.otel_service_environment,
        "service.version": settings.app_version,
    })


def _configure_trace_export(settings: YourRAGSettings, resource: object) -> bool:
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint or None)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        logger.info("OTEL_TRACES_ENABLED | endpoint=%s", settings.otel_exporter_otlp_endpoint or "default")
        return True
    except Exception as exc:
        logger.warning("OTEL_TRACES_DISABLED | error=%s", exc)
        return False


def _configure_log_export(settings: YourRAGSettings, resource: object) -> bool:
    try:
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        provider = LoggerProvider(resource=resource)
        exporter = OTLPLogExporter(endpoint=settings.otel_exporter_otlp_logs_endpoint or settings.otel_exporter_otlp_endpoint or None)
        provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
        set_logger_provider(provider)
        root_logger = logging.getLogger()
        root_logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=provider))
        return True
    except Exception as exc:
        logger.warning("OTEL_LOGS_DISABLED | error=%s", exc)
        return False


def resolve_trace_id() -> str:
    try:
        from opentelemetry.trace import get_current_span
        span = get_current_span()
        context = span.get_span_context()
        if context is not None and context.trace_id and getattr(context, "is_valid", True):
            return format(context.trace_id, "032x")
    except Exception:
        pass
    return uuid.uuid4().hex


@contextmanager
def start_span(
    name: str,
    *,
    attributes: Mapping[str, object] | None = None,
    kind: str = "internal",
) -> Iterator[object | None]:
    if not _TELEMETRY_READY:
        yield None
        return
    try:
        from opentelemetry import trace
        from opentelemetry.trace import SpanKind
        tracer = trace.get_tracer("yourrag")
        kind_map = {
            "server": SpanKind.SERVER, "client": SpanKind.CLIENT,
            "producer": SpanKind.PRODUCER, "consumer": SpanKind.CONSUMER,
            "internal": SpanKind.INTERNAL,
        }
        with tracer.start_as_current_span(name, kind=kind_map.get(kind.lower(), SpanKind.INTERNAL)) as span:
            for key, value in (attributes or {}).items():
                if value is not None:
                    span.set_attribute(key, _normalize_attribute(value))
            yield span
    except Exception:
        yield None


def _normalize_attribute(value: object) -> object:
    if isinstance(value, (bool, int, float, str)):
        return value
    return str(value)
