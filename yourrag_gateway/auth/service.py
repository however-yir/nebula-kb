"""Authentication, token, and RBAC service (from P2, adapted for YourRAG)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import secrets
from typing import Any

from yourrag_gateway.auth.jwt_utils import decode_hs256, encode_hs256, issue_access_token_payload
from yourrag_gateway.auth.models import AuthContext
from yourrag_gateway.core.settings import YourRAGSettings


@dataclass(slots=True)
class LoginResult:
    access_token: str
    token_type: str
    expires_in_seconds: int
    context: AuthContext


class AuthService:
    """Stateless auth service — delegates persistence to the P3 engine's DB layer."""

    def __init__(self, settings: YourRAGSettings, user_lookup: Any = None) -> None:
        self.settings = settings
        self.user_lookup = user_lookup  # Will be wired to P3's api/db/services/user_service.py
        self._admin_bootstrapped = False

    def login_with_password(self, *, username: str, password: str) -> LoginResult:
        user = self._find_user(username)
        if user is None or not user.get("is_active", True):
            raise ValueError("Invalid credentials.")
        if not verify_password(password=password, password_hash=user["password_hash"]):
            raise ValueError("Invalid credentials.")

        roles = user.get("roles", ["user"])
        permissions = user.get("permissions", [])
        context = AuthContext(
            actor_id=user["id"],
            actor_name=username,
            actor_type="user",
            roles=roles,
            permissions=permissions,
            auth_type="jwt",
        )
        payload = issue_access_token_payload(
            subject=user["id"],
            username=username,
            roles=roles,
            permissions=permissions,
            issuer=self.settings.jwt_issuer,
            expires_in_minutes=self.settings.jwt_access_token_exp_minutes,
        )
        token = encode_hs256(payload, secret=self.settings.jwt_secret)
        return LoginResult(
            access_token=token,
            token_type="bearer",
            expires_in_seconds=self.settings.jwt_access_token_exp_minutes * 60,
            context=context,
        )

    def authenticate_bearer_token(self, token: str) -> AuthContext:
        payload = decode_hs256(token, secret=self.settings.jwt_secret)
        if payload.get("iss") != self.settings.jwt_issuer:
            raise ValueError("Invalid token issuer.")
        actor_id = str(payload.get("sub", ""))
        username = str(payload.get("username", ""))
        if not actor_id:
            raise ValueError("Token subject is missing.")
        return AuthContext(
            actor_id=actor_id,
            actor_name=username,
            actor_type="user",
            roles=[str(item) for item in payload.get("roles", [])],
            permissions=[str(item) for item in payload.get("permissions", [])],
            auth_type="jwt",
        )

    def authenticate_api_key(self, raw_key: str) -> AuthContext:
        # For now, simple token-based auth; can be wired to P3's APIToken model
        if raw_key.startswith("yourrag_"):
            return AuthContext(
                actor_id="api_user",
                actor_name="api_key_user",
                actor_type="api_key",
                roles=["user"],
                permissions=[],
                auth_type="api_key",
            )
        raise ValueError("Invalid API key.")

    def create_api_key(self, *, actor_id: str, name: str = "default") -> dict[str, str]:
        raw_key = f"yourrag_{secrets.token_urlsafe(24)}"
        return {
            "id": secrets.token_hex(8),
            "name": name,
            "key_prefix": raw_key[:12],
            "api_key": raw_key,
        }

    def _find_user(self, username: str) -> dict[str, Any] | None:
        """Look up user via P3's DB layer or local fallback."""
        if self.user_lookup is not None:
            return self.user_lookup(username)
        # Fallback: auto-bootstrap admin
        if not self._admin_bootstrapped and username == self.settings.bootstrap_admin_username:
            self._admin_bootstrapped = True
            return {
                "id": "admin-001",
                "username": username,
                "password_hash": hash_password(self.settings.bootstrap_admin_password),
                "is_active": True,
                "roles": ["admin"],
                "permissions": ["admin:full"],
            }
        return None


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 120_000
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_password(*, password: str, password_hash: str) -> bool:
    try:
        _, iterations_raw, salt, digest = password_hash.split("$", maxsplit=3)
        iterations = int(iterations_raw)
    except Exception:
        return False
    expected = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    ).hex()
    return secrets.compare_digest(expected, digest)


def utc_timestamp() -> int:
    return int(datetime.now(timezone.utc).timestamp())
