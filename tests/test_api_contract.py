import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = ROOT / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from common.contracts import (
    API_V1_ENDPOINTS,
    API_V1_PREFIX,
    AUTH_SCHEMES,
    E2E_MAIN_PATH,
    ERROR_CODE_RANGES,
    FIELD_NAMING,
    OPENAPI_VERSION,
    PAGINATION_FIELDS,
    QUERY_CONTRACT,
    RESPONSE_FIELDS,
)
from system_manage.services.release_acceptance import ReleaseAcceptanceDemo


def test_response_contract_keys_are_stable():
    assert RESPONSE_FIELDS == ("code", "message", "data")


def test_page_contract_keys_are_stable():
    assert PAGINATION_FIELDS == ("total", "records", "current", "size")


def test_query_and_field_contract_are_explicit():
    assert FIELD_NAMING == "snake_case"
    assert QUERY_CONTRACT["pagination"] == ("current_page", "page_size")
    assert QUERY_CONTRACT["sorting"] == ("order_by",)


def test_result_module_uses_contract_constants():
    result_source = (APPS_DIR / "common" / "result" / "result.py").read_text(encoding="utf-8")

    assert "RESPONSE_FIELDS" in result_source
    assert "PAGINATION_FIELDS" in result_source


def test_api_v1_auth_error_and_e2e_contract_are_explicit():
    assert API_V1_PREFIX == "/api/v1"
    assert "bearer" in AUTH_SCHEMES
    assert AUTH_SCHEMES["bearer"]["header"] == "Authorization"
    assert "application_api_key" in AUTH_SCHEMES
    assert ERROR_CODE_RANGES["auth"] == (1000, 1099)
    assert E2E_MAIN_PATH == (
        "login",
        "create_knowledge_base",
        "upload_document",
        "parse_document",
        "ask_with_retrieval",
        "submit_feedback",
    )
    assert {endpoint["operation_id"] for endpoint in API_V1_ENDPOINTS} >= {
        "auth.login",
        "knowledge_base.create",
        "document.upload",
        "question.ask",
        "feedback.submit",
        "permission.resource_grant",
    }


def test_openapi_v1_document_matches_contract():
    spec = json.loads((ROOT / "docs" / "api" / "openapi-v1.json").read_text(encoding="utf-8"))

    assert spec["openapi"] == OPENAPI_VERSION
    assert spec["info"]["version"] == "v1"
    assert "BearerAuth" in spec["components"]["securitySchemes"]
    assert "ApplicationApiKey" in spec["components"]["securitySchemes"]

    for endpoint in API_V1_ENDPOINTS:
        path = endpoint["path"]
        method = endpoint["method"].lower()
        assert path in spec["paths"]
        assert method in spec["paths"][path]


def test_release_acceptance_snapshot_covers_contract_security_and_e2e():
    snapshot = ReleaseAcceptanceDemo().snapshot()

    assert snapshot.api["api_v1_prefix"] == API_V1_PREFIX
    assert snapshot.e2e["login"] == "token-issued"
    assert snapshot.e2e["document_status"] == "indexed"
    assert snapshot.e2e["citation_count"] >= 1
    assert snapshot.e2e["feedback_rating"] == 1
    assert snapshot.permission["workspace_isolation_blocked"] is True
    assert "Content-Security-Policy" in snapshot.security["headers"]
    assert snapshot.security["upload"]["max_upload_bytes"] > 0
    assert "X-Request-ID" == snapshot.observability["request_id_header"]
