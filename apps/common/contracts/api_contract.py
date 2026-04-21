# coding=utf-8
"""Project-wide API contract constants.

These values freeze the public response envelope and common query vocabulary.
New API work should reference this module before view/serializer implementation.
"""

API_CONTRACT_VERSION = "2026-04-21"
VERSIONING_STRATEGY = "path-prefix-stable-v2"
FIELD_NAMING = "snake_case"

RESPONSE_FIELDS = ("code", "message", "data")
PAGINATION_FIELDS = ("total", "records", "current", "size")

SORT_DESC_PREFIX = "-"
QUERY_CONTRACT = {
    "pagination": ("current_page", "page_size"),
    "sorting": ("order_by",),
    "filtering": "explicit query params only; avoid opaque filter blobs",
}

ERROR_CODE_RANGES = {
    "success": (200, 299),
    "client": (400, 499),
    "auth": (1000, 1099),
    "domain": (3000, 4999),
    "validation": (5000, 5999),
    "server": (500, 599),
}

