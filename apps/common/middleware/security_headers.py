from django.utils.deprecation import MiddlewareMixin


DEFAULT_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "img-src 'self' data: blob:; "
    "style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; "
    "connect-src 'self'"
)


class SecurityHeadersMiddleware(MiddlewareMixin):

    def process_response(self, request, response):
        response.setdefault('X-Content-Type-Options', 'nosniff')
        response.setdefault('X-Frame-Options', 'DENY')
        response.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.setdefault('X-XSS-Protection', '1; mode=block')
        response.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        response.setdefault('Content-Security-Policy', DEFAULT_CONTENT_SECURITY_POLICY)
        return response
