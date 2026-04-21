# coding=utf-8
"""Password validation policy shared by user serializers."""

import re


PASSWORD_REGEX = re.compile(
    r"^"  # start
    r"(?=.*[a-z])"  # at least one lowercase letter
    r"(?=.*[-_!@#$%^&*`~.()+=])"  # at least one supported special character
    r"(?:(?=.*[A-Z])|(?=.*\d))"  # at least one uppercase letter or digit
    r"[a-zA-Z0-9-_!@#$%^&*`~.()+=]{6,20}"
    r"$"
)

