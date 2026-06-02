# coding=utf-8
"""Project-wide API contract constants.

These values freeze the public response envelope and common query vocabulary.
New API work should reference this module before view/serializer implementation.
"""

API_CONTRACT_VERSION = "2026-04-21"
VERSIONING_STRATEGY = "path-prefix-stable-v2"
FIELD_NAMING = "snake_case"
API_V1_PREFIX = "/api/v1"
OPENAPI_VERSION = "3.1.0"

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

AUTH_SCHEMES = {
    "bearer": {
        "type": "http",
        "scheme": "bearer",
        "header": "Authorization",
        "description": "User and workspace API requests use Authorization: Bearer <token>.",
    },
    "application_api_key": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "Published application calls may use a scoped application API key.",
    },
}

ERROR_RESPONSE_SCHEMA = {
    "required": RESPONSE_FIELDS,
    "properties": {
        "code": "integer domain error code",
        "message": "human readable error message",
        "data": "object or null; validation errors include field details",
    },
}

API_V1_ENDPOINTS = (
    {
        "operation_id": "auth.login",
        "method": "POST",
        "path": f"{API_V1_PREFIX}/auth/login",
        "auth": "none",
        "success_code": 200,
    },
    {
        "operation_id": "knowledge_base.create",
        "method": "POST",
        "path": f"{API_V1_PREFIX}/knowledge-bases",
        "auth": "bearer",
        "success_code": 200,
    },
    {
        "operation_id": "document.upload",
        "method": "POST",
        "path": f"{API_V1_PREFIX}/knowledge-bases/{{knowledge_base_id}}/documents",
        "auth": "bearer",
        "success_code": 200,
    },
    {
        "operation_id": "question.ask",
        "method": "POST",
        "path": f"{API_V1_PREFIX}/knowledge-bases/{{knowledge_base_id}}/ask",
        "auth": "bearer",
        "success_code": 200,
    },
    {
        "operation_id": "feedback.submit",
        "method": "POST",
        "path": f"{API_V1_PREFIX}/feedback",
        "auth": "bearer",
        "success_code": 200,
    },
    {
        "operation_id": "application.publish",
        "method": "POST",
        "path": f"{API_V1_PREFIX}/applications/{{application_id}}/versions",
        "auth": "bearer",
        "success_code": 200,
    },
    {
        "operation_id": "permission.resource_grant",
        "method": "POST",
        "path": f"{API_V1_PREFIX}/permissions/resources",
        "auth": "bearer",
        "success_code": 200,
    },
)

E2E_MAIN_PATH = (
    "login",
    "create_knowledge_base",
    "upload_document",
    "parse_document",
    "ask_with_retrieval",
    "submit_feedback",
)
