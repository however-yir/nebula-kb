"""Minimal HS256 JWT encode/decode helpers (from P2)."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hmac
import json
import hashlib
from typing import Any


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("ascii"))


def encode_hs256(payload: dict[str, Any], *, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_part = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode())
    payload_part = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    )
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_part = _b64url_encode(signature)
    return f"{header_part}.{payload_part}.{signature_part}"


def decode_hs256(token: str, *, secret: str, verify_exp: bool = True) -> dict[str, Any]:
    try:
        header_part, payload_part, signature_part = token.split(".")
    except ValueError as exc:
        raise ValueError("Malformed JWT token.") from exc

    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    actual_signature = _b64url_decode(signature_part)
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise ValueError("Invalid JWT signature.")

    payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
    if verify_exp and "exp" in payload:
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if int(payload["exp"]) < now_ts:
            raise ValueError("JWT token expired.")
    return payload


def issue_access_token_payload(
    *,
    subject: str,
    username: str,
    roles: list[str],
    permissions: list[str],
    issuer: str,
    expires_in_minutes: int,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=max(expires_in_minutes, 1))
    return {
        "sub": subject,
        "username": username,
        "roles": roles,
        "permissions": permissions,
        "iss": issuer,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
