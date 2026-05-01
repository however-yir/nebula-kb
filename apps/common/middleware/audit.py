import json
import logging
import time
import uuid

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('nebula.audit')

SENSITIVE_FIELDS = frozenset({
    'password', 'token', 'secret', 'authorization', 'cookie',
    'api_key', 'access_token', 'refresh_token', 'client_secret',
})

AUTH_PATHS = ('/login', '/logout', '/token', '/refresh')


def _redact_value(key, value):
    if isinstance(key, str) and key.lower() in SENSITIVE_FIELDS:
        return '***REDACTED***'
    return value


def redact_dict(data):
    if not isinstance(data, dict):
        return data
    return {k: _redact_value(k, redact_dict(v) if isinstance(v, dict) else v) for k, v in data.items()}


def redact_body(body_str):
    if not body_str:
        return body_str
    try:
        data = json.loads(body_str)
        if isinstance(data, dict):
            return json.dumps(redact_dict(data))
    except (json.JSONDecodeError, TypeError):
        pass
    return body_str


class AuditLogMiddleware(MiddlewareMixin):

    def process_request(self, request):
        request._audit_start_time = time.monotonic()
        request._audit_request_id = str(uuid.uuid4())

    def process_response(self, request, response):
        try:
            duration_ms = 0.0
            start = getattr(request, '_audit_start_time', None)
            if start is not None:
                duration_ms = (time.monotonic() - start) * 1000

            request_id = getattr(request, '_audit_request_id', '')
            path = getattr(request, 'path', '')
            method = getattr(request, 'method', '')
            status_code = getattr(response, 'status_code', 0)

            user_id = ''
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_id = str(getattr(request.user, 'id', ''))

            is_auth_event = any(p in path for p in AUTH_PATHS)

            if is_auth_event:
                body = ''
                if hasattr(request, 'body'):
                    try:
                        body = request.body.decode('utf-8', errors='replace')
                    except Exception:
                        body = ''
                logger.info(json.dumps({
                    'event': 'auth',
                    'request_id': request_id,
                    'user_id': user_id,
                    'method': method,
                    'path': path,
                    'status_code': status_code,
                    'ip': request.META.get('REMOTE_ADDR', ''),
                    'duration_ms': round(duration_ms, 2),
                    'body': redact_body(body),
                }))
        except Exception:
            pass
        return response
