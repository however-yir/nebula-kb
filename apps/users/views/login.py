# coding=utf-8
"""
    @project: LZKB
    @Author：虎虎
    @file： user.py
    @date：2025/4/14 10:22
    @desc:
"""
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.views import APIView

from common import result
from common.auth.tokens import (
    clear_auth_cookies,
    get_request_access_token,
    get_request_refresh_token,
    refresh_session,
    revoke_by_access_token,
    revoke_by_refresh_token,
    set_auth_cookies,
)
from common.log.log import log
from common.utils.common import encryption
from models_provider.api.model import DefaultModelResponse
from users.api.login import LoginAPI, CaptchaAPI, RefreshTokenAPI, TokenPolicyAPI
from users.serializers.login import LoginSerializer, CaptchaSerializer, get_token_policy


def _get_details(request):
    path = request.path
    body = request.data
    query = request.query_params
    return {
        'path': path,
        'body': {**body, 'password': encryption(body.get('password', ''))},
        'query': query
    }


class LoginView(APIView):
    @extend_schema(methods=['POST'],
                   description=_("Log in"),
                   summary=_("Log in"),
                   operation_id=_("Log in"),  # type: ignore
                   tags=[_("User Management")],  # type: ignore
                   request=LoginAPI.get_request(),
                   responses=LoginAPI.get_response())
    @log(menu='User management', operate='Log in', get_user=lambda r: {'username': r.data.get('username', None)},
         get_details=_get_details,
         get_operation_object=lambda r, k: {'name': r.data.get('username')})
    def post(self, request: Request):
        payload = LoginSerializer().login(request.data, request=request)
        response = result.success(payload)
        return set_auth_cookies(response, payload)


class Logout(APIView):
    @extend_schema(methods=['POST'],
                   summary=_("Sign out"),
                   description=_("Sign out"),
                   operation_id=_("Sign out"),  # type: ignore
                   tags=[_("User Management")],  # type: ignore
                   responses=DefaultModelResponse.get_response())
    @log(menu='User management', operate='Sign out',
         get_user=lambda r: {},
         get_operation_object=lambda r, k: {'name': getattr(getattr(r, 'user', None), 'username', 'anonymous')})
    def post(self, request: Request):
        access_token = get_request_access_token(request)
        refresh_token = get_request_refresh_token(request)
        revoked = revoke_by_access_token(access_token, reason="logout")
        revoked = revoke_by_refresh_token(refresh_token, reason="logout") or revoked
        response = result.success(revoked or True)
        return clear_auth_cookies(response)


class RefreshTokenView(APIView):
    @extend_schema(methods=['POST'],
                   summary=_("Refresh token"),
                   description=_("Refresh token"),
                   operation_id=_("Refresh token"),  # type: ignore
                   tags=[_("User Management")],  # type: ignore
                   request=RefreshTokenAPI.get_request(),
                   responses=RefreshTokenAPI.get_response())
    def post(self, request: Request):
        payload = refresh_session(get_request_refresh_token(request))
        response = result.success(payload)
        return set_auth_cookies(response, payload)


class TokenPolicyView(APIView):
    @extend_schema(methods=['GET'],
                   summary=_("Get token policy"),
                   description=_("Get token policy"),
                   operation_id=_("Get token policy"),  # type: ignore
                   tags=[_("User Management")],  # type: ignore
                   responses=TokenPolicyAPI.get_response())
    def get(self, request: Request):
        return result.success(get_token_policy())


class CaptchaView(APIView):
    @extend_schema(methods=['GET'],
                   summary=_("Get captcha"),
                   description=_("Get captcha"),
                   operation_id=_("Get captcha"),  # type: ignore
                   tags=[_("User Management")],  # type: ignore
                   responses=CaptchaAPI.get_response())
    def get(self, request: Request):
        username = request.query_params.get('username', None)
        return result.success(CaptchaSerializer().generate(username))
