# coding=utf-8
"""
    @project: LZKB
    @Author：虎虎
    @file： cross_domain_middleware.py
    @date：2024/5/8 13:36
    @desc:
"""
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

from common.cache_data.application_api_key_cache import get_application_api_key
from lzkb.const import CONFIG


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def get_configured_cors_origins():
    origins = _as_list(CONFIG.get("CORS_ALLOWED_ORIGINS"))
    if CONFIG.get_debug():
        origins.extend([
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ])
    return set(origins)


def is_allowed_origin(origin, extra_origins=None):
    if not origin:
        return False
    configured_origins = get_configured_cors_origins()
    resource_origins = set(_as_list(extra_origins))
    return origin in configured_origins or origin in resource_origins


def build_cors_headers(origin, extra_origins=None):
    if not is_allowed_origin(origin, extra_origins):
        return {}
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET,POST,DELETE,PUT,OPTIONS",
        "Access-Control-Allow-Headers": "Origin,X-Requested-With,Content-Type,Accept,Authorization,token",
        "Vary": "Origin",
    }


class CrossDomainMiddleware(MiddlewareMixin):

    def process_request(self, request):
        if request.method == 'OPTIONS':
            return HttpResponse(status=200, headers=build_cors_headers(request.META.get('HTTP_ORIGIN')))

    def process_response(self, request, response):
        auth = request.META.get('HTTP_AUTHORIZATION')
        origin = request.META.get('HTTP_ORIGIN')

        if auth is not None and any([str(auth).startswith(prefix) for prefix in
                                     ['Bearer application-', 'Bearer agent-']]) and origin is not None:
            application_api_key = get_application_api_key(str(auth), True)
            cross_domain_list = application_api_key.get('cross_domain_list', [])
            allow_cross_domain = application_api_key.get('allow_cross_domain', False)
            if allow_cross_domain:
                for key, value in build_cors_headers(origin, cross_domain_list).items():
                    response[key] = value
        return response
