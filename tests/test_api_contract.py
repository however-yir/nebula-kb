import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = ROOT / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from common.contracts import FIELD_NAMING, PAGINATION_FIELDS, QUERY_CONTRACT, RESPONSE_FIELDS


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
