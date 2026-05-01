import uuid

from django.utils.deprecation import MiddlewareMixin

try:
    from opentelemetry import trace
    from opentelemetry.trace import StatusCode
    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False


class OTelTracingMiddleware(MiddlewareMixin):

    def process_request(self, request):
        request._correlation_id = request.META.get('HTTP_X_REQUEST_ID', str(uuid.uuid4()))
        if _OTEL_AVAILABLE:
            tracer = trace.get_tracer('nebula-kb')
            span = tracer.start_span(name=f"{request.method} {request.path}")
            span.set_attribute('http.method', request.method)
            span.set_attribute('http.url', request.build_absolute_uri())
            span.set_attribute('correlation_id', request._correlation_id)
            request._otel_span = span

    def process_response(self, request, response):
        correlation_id = getattr(request, '_correlation_id', '')
        if correlation_id:
            response['X-Request-ID'] = correlation_id

        if _OTEL_AVAILABLE:
            span = getattr(request, '_otel_span', None)
            if span:
                span.set_attribute('http.status_code', response.status_code)
                if response.status_code >= 400:
                    span.set_status(StatusCode.ERROR)
                span.end()
        return response
