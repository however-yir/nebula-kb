# coding=utf-8
"""
    @project: LZKB
    @file： tokens.py
    @desc: 系统用户 access/refresh token 与设备会话管理
"""
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.translation import gettext_lazy as _

from common.exception.app_exception import AppAuthenticationFailed
from lzkb.const import CONFIG
from users.models import DeviceSession, User


ACCESS_TOKEN_COOKIE_NAME = CONFIG.get("AUTH_ACCESS_COOKIE_NAME", "lzkb_access_token")
REFRESH_TOKEN_COOKIE_NAME = CONFIG.get("AUTH_REFRESH_COOKIE_NAME", "lzkb_refresh_token")
AUTH_COOKIE_PATH = CONFIG.get("AUTH_COOKIE_PATH", "/")


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    access_expires_at: object
    refresh_expires_at: object


def get_access_token_ttl() -> int:
    return int(CONFIG.get("TOKEN_EXPIRE", CONFIG.get("AUTH_ACCESS_TOKEN_TTL_SECONDS", 15 * 60)))


def get_refresh_token_ttl() -> int:
    return int(CONFIG.get("AUTH_REFRESH_TOKEN_TTL_SECONDS", 7 * 24 * 60 * 60))


def get_cookie_secure() -> bool:
    configured = CONFIG.get("AUTH_COOKIE_SECURE")
    if configured is None:
        return not settings.DEBUG
    if isinstance(configured, bool):
        return configured
    return str(configured).lower() in {"1", "true", "yes", "on"}


def get_cookie_same_site() -> str:
    return CONFIG.get("AUTH_COOKIE_SAMESITE", "Lax")


def generate_token(prefix: str) -> str:
    return f"{prefix}.{secrets.token_urlsafe(48)}"


def hash_token(token: str) -> str:
    return salted_hmac("lzkb.auth.token", token, secret=settings.SECRET_KEY, algorithm="sha256").hexdigest()


def get_request_access_token(request):
    auth = request.META.get("HTTP_AUTHORIZATION")
    if auth and auth.startswith("Bearer "):
        return auth[7:]
    return request.COOKIES.get(ACCESS_TOKEN_COOKIE_NAME)


def get_request_refresh_token(request):
    body_token = None
    if hasattr(request, "data") and isinstance(request.data, dict):
        body_token = request.data.get("refresh_token")
    return body_token or request.COOKIES.get(REFRESH_TOKEN_COOKIE_NAME)


def get_request_ip(request) -> str:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def get_request_user_agent(request) -> str:
    return request.META.get("HTTP_USER_AGENT", "")[:2048]


def get_request_device_id(request) -> str:
    return request.META.get("HTTP_X_DEVICE_ID") or str(secrets.token_urlsafe(24))


def _new_token_pair(now=None) -> IssuedTokens:
    now = now or timezone.now()
    return IssuedTokens(
        access_token=generate_token("lzkb-at"),
        refresh_token=generate_token("lzkb-rt"),
        access_expires_at=now + timedelta(seconds=get_access_token_ttl()),
        refresh_expires_at=now + timedelta(seconds=get_refresh_token_ttl()),
    )


def _serialize_tokens(session: DeviceSession, tokens: IssuedTokens) -> dict:
    return {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": "Bearer",
        "expires_in": get_access_token_ttl(),
        "refresh_expires_in": get_refresh_token_ttl(),
        "user_id": str(session.user_id),
        "session_id": str(session.id),
        "device_id": session.device_id,
    }


@transaction.atomic
def create_device_session(user: User, request, login_method: str = "LOCAL") -> dict:
    now = timezone.now()
    tokens = _new_token_pair(now)
    session = DeviceSession.objects.create(
        user=user,
        device_id=get_request_device_id(request),
        access_token_hash=hash_token(tokens.access_token),
        refresh_token_hash=hash_token(tokens.refresh_token),
        password_hash=user.password,
        login_method=login_method,
        ip_address=get_request_ip(request),
        user_agent=get_request_user_agent(request),
        access_expires_at=tokens.access_expires_at,
        refresh_expires_at=tokens.refresh_expires_at,
        last_login=now,
        last_active=now,
    )
    User.objects.filter(id=user.id).update(last_login=now, last_active=now)
    return _serialize_tokens(session, tokens)


def get_valid_session_by_access_token(token: str) -> DeviceSession | None:
    if not token:
        return None
    session = (
        DeviceSession.objects
        .select_related("user")
        .filter(access_token_hash=hash_token(token))
        .first()
    )
    if session is None:
        return None
    now = timezone.now()
    if session.revoked_at is not None:
        raise AppAuthenticationFailed(1002, _("Login expired"))
    if session.access_expires_at <= now:
        raise AppAuthenticationFailed(1002, _("Login expired"))
    if session.refresh_expires_at <= now:
        revoke_session(session, "refresh_expired")
        raise AppAuthenticationFailed(1002, _("Login expired"))
    return session


def touch_session(session: DeviceSession, user: User):
    now = timezone.now()
    DeviceSession.objects.filter(id=session.id, revoked_at__isnull=True).update(last_active=now)
    User.objects.filter(id=user.id).update(last_active=now)


@transaction.atomic
def refresh_session(refresh_token: str) -> dict:
    if not refresh_token:
        raise AppAuthenticationFailed(1003, _("Not logged in, please log in first"))
    session = (
        DeviceSession.objects
        .select_related("user")
        .select_for_update()
        .filter(refresh_token_hash=hash_token(refresh_token))
        .first()
    )
    if session is None:
        raise AppAuthenticationFailed(1002, _("Authentication information is incorrect! illegal user"))
    now = timezone.now()
    if session.revoked_at is not None or session.refresh_expires_at <= now:
        raise AppAuthenticationFailed(1002, _("Login expired"))
    if not session.user.is_active or session.user.password != session.password_hash:
        revoke_session(session, "user_changed")
        raise AppAuthenticationFailed(1002, _("Authentication information is incorrect"))

    tokens = _new_token_pair(now)
    session.access_token_hash = hash_token(tokens.access_token)
    session.refresh_token_hash = hash_token(tokens.refresh_token)
    session.access_expires_at = tokens.access_expires_at
    session.refresh_expires_at = tokens.refresh_expires_at
    session.last_active = now
    session.save(update_fields=[
        "access_token_hash",
        "refresh_token_hash",
        "access_expires_at",
        "refresh_expires_at",
        "last_active",
        "update_time",
    ])
    User.objects.filter(id=session.user_id).update(last_active=now)
    return _serialize_tokens(session, tokens)


def revoke_session(session: DeviceSession, reason: str = "logout"):
    if session.revoked_at is not None:
        return
    session.revoked_at = timezone.now()
    session.revoke_reason = reason
    session.save(update_fields=["revoked_at", "revoke_reason", "update_time"])


def revoke_by_access_token(access_token: str, reason: str = "logout") -> bool:
    if not access_token:
        return False
    session = DeviceSession.objects.filter(access_token_hash=hash_token(access_token)).first()
    if session is None:
        return False
    revoke_session(session, reason)
    return True


def revoke_by_refresh_token(refresh_token: str, reason: str = "logout") -> bool:
    if not refresh_token:
        return False
    session = DeviceSession.objects.filter(refresh_token_hash=hash_token(refresh_token)).first()
    if session is None:
        return False
    revoke_session(session, reason)
    return True


def revoke_user_sessions(user_id, reason: str = "password_changed"):
    DeviceSession.objects.filter(user_id=user_id, revoked_at__isnull=True).update(
        revoked_at=timezone.now(),
        revoke_reason=reason,
    )


def set_auth_cookies(response, payload: dict):
    cookie_kwargs = {
        "path": AUTH_COOKIE_PATH,
        "httponly": True,
        "secure": get_cookie_secure(),
        "samesite": get_cookie_same_site(),
    }
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        payload["access_token"],
        max_age=int(payload.get("expires_in", get_access_token_ttl())),
        **cookie_kwargs,
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE_NAME,
        payload["refresh_token"],
        max_age=int(payload.get("refresh_expires_in", get_refresh_token_ttl())),
        **cookie_kwargs,
    )
    return response


def clear_auth_cookies(response):
    response.delete_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        path=AUTH_COOKIE_PATH,
        samesite=get_cookie_same_site(),
    )
    response.delete_cookie(
        REFRESH_TOKEN_COOKIE_NAME,
        path=AUTH_COOKIE_PATH,
        samesite=get_cookie_same_site(),
    )
    return response
