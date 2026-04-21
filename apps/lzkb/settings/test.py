# coding=utf-8
"""Test settings for deterministic and faster CI execution."""

from . import *  # noqa: F401,F403

DEBUG = False

# Avoid external cache/redis dependencies in tests.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "lzkb-tests",
    }
}

# Speed up auth-related tests.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
