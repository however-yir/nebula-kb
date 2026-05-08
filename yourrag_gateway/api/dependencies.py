"""FastAPI dependency providers (merged P2 + P3)."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, Header, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from yourrag_gateway.audit.service import AuditService
from yourrag_gateway.auth.models import AuthContext, SYSTEM_CONTEXT
from yourrag_gateway.auth.service import AuthService
from yourrag_gateway.core.request_context import RequestContext, get_request_context, set_request_context
from yourrag_gateway.core.settings import YourRAGSettings
from yourrag_gateway.security.rate_limit import RateLimiter

_bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def get_settings() -> YourRAGSettings:
    return YourRAGSettings()


@lru_cache(maxsize=1)
def get_auth_service() -> AuthService:
    return AuthService(get_settings())


@lru_cache(maxsize=1)
def get_audit_service() -> AuditService:
    return AuditService()


@lru_cache(maxsize=1)
def get_rate_limiter() -> RateLimiter:
    return RateLimiter(redis_url=get_settings().redis_url)


def _apply_rate_limit(
    *,
    principal: AuthContext,
    request: Request,
    response: Response,
    settings: YourRAGSettings,
    limiter: RateLimiter,
) -> None:
    key = f"{principal.actor_type}:{principal.actor_id}:{request.url.path}"
    result = limiter.check(key=key, limit=settings.rate_limit_per_minute, window_seconds=60)
    response.headers["X-RateLimit-Limit"] = str(result.limit)
    response.headers["X-RateLimit-Remaining"] = str(result.remaining)
    if not result.allowed:
        response.headers["Retry-After"] = str(result.retry_after_seconds)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded.")


def _bind_principal_to_context(principal: AuthContext) -> None:
    current = get_request_context()
    set_request_context(RequestContext(
        request_id=current.request_id, trace_id=current.trace_id,
        session_id=current.session_id, job_id=current.job_id,
        actor_id=principal.actor_id, actor_type=principal.actor_type,
    ))


def get_current_principal(
    request: Request,
    response: Response,
    settings: YourRAGSettings = Depends(get_settings),
    auth_service: AuthService = Depends(get_auth_service),
    limiter: RateLimiter = Depends(get_rate_limiter),
    bearer: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    api_key_header: str | None = Header(default=None, alias="X-API-Key"),
) -> AuthContext:
    if not settings.security_enabled:
        _bind_principal_to_context(SYSTEM_CONTEXT)
        return SYSTEM_CONTEXT

    principal: AuthContext | None = None
    if bearer is not None and bearer.credentials:
        try:
            principal = auth_service.authenticate_bearer_token(bearer.credentials)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    elif api_key_header:
        try:
            principal = auth_service.authenticate_api_key(api_key_header)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")

    _bind_principal_to_context(principal)
    _apply_rate_limit(principal=principal, request=request, response=response, settings=settings, limiter=limiter)
    return principal


def require_permissions(*required_permissions: str):
    def _dependency(principal: AuthContext = Depends(get_current_principal)) -> AuthContext:
        if principal.is_admin:
            return principal
        missing = [p for p in required_permissions if p not in principal.permissions]
        if missing:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing required permissions: {', '.join(missing)}")
        return principal
    return _dependency
