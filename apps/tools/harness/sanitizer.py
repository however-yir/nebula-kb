# coding=utf-8

from typing import Any


MASK = "********"
SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "password",
    "private_key",
    "secret",
    "secret_key",
    "token",
)


def _is_sensitive_key(key: Any) -> bool:
    key_text = str(key).lower()
    return any(part in key_text for part in SENSITIVE_KEY_PARTS)


def sanitize_parameters(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: MASK if _is_sensitive_key(key) else sanitize_parameters(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_parameters(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_parameters(item) for item in value)
    return value
