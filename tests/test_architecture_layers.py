import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = ROOT / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from common.contracts import FROZEN_MODULE_BOUNDARIES


def test_frozen_module_boundaries_cover_target_domains():
    domains = {boundary["domain"] for boundary in FROZEN_MODULE_BOUNDARIES}

    assert domains == {
        "users_auth",
        "knowledge",
        "retrieval_qa",
        "application_workflow",
        "files_connectors",
    }


def test_core_domain_layer_packages_exist():
    domains = [
        "users",
        "knowledge",
        "application",
        "trigger",
        "chat",
        "oss",
        "tools",
        "models_provider",
        "local_model",
    ]
    layers = ["services", "repositories", "policies"]

    for domain in domains:
        for layer in layers:
            assert (APPS_DIR / domain / layer / "__init__.py").exists()


def test_user_serializer_split_stays_under_large_file_threshold():
    user_serializer = APPS_DIR / "users" / "serializers" / "user.py"

    assert len(user_serializer.read_text(encoding="utf-8").splitlines()) < 800
