# coding=utf-8
"""Authentication shared by the web process and the local-model service."""
import hmac

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from lzkb.const import CONFIG


LOCAL_MODEL_AUTH_HEADER = 'X-Nebula-Local-Model-Token'


def get_local_model_auth_token() -> str:
    """Return the shared service token, with Django's key as a compatibility fallback."""
    return str(CONFIG.get('LOCAL_MODEL_AUTH_TOKEN') or CONFIG.get('SECRET_KEY') or settings.SECRET_KEY or '')


def get_local_model_headers(extra_headers=None) -> dict:
    headers = dict(extra_headers or {})
    headers[LOCAL_MODEL_AUTH_HEADER] = get_local_model_auth_token()
    return headers


class LocalModelAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = request.headers.get(LOCAL_MODEL_AUTH_HEADER, '')
        expected = get_local_model_auth_token()
        if not expected or not token or not hmac.compare_digest(token, expected):
            raise AuthenticationFailed('Invalid local model service token')
        return AnonymousUser(), token
