#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = ROOT / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from system_manage.services.release_acceptance import ReleaseAcceptanceDemo  # noqa: E402


def main() -> None:
    snapshot = ReleaseAcceptanceDemo().snapshot()

    print("NebulaKB demo: API, security, deployment, observability release acceptance")
    print(f"API v1 prefix: {snapshot.api['api_v1_prefix']}")
    print(f"OpenAPI version: {snapshot.api['openapi_version']}")
    print(f"Auth schemes: {', '.join(snapshot.api['auth_schemes'])}")
    print(f"Pagination fields: {', '.join(snapshot.api['pagination_fields'])}")
    print(f"Error code ranges: {json.dumps(snapshot.api['error_code_ranges'], sort_keys=True)}")
    print(f"E2E path: {' -> '.join(snapshot.e2e['path'])}")
    print(f"Login flow: {snapshot.e2e['login']}")
    print(f"Document parse status: {snapshot.e2e['document_status']}")
    print(f"Retrieval service test: citations={snapshot.e2e['citation_count']}")
    print(f"Feedback service test: rating={snapshot.e2e['feedback_rating']}")
    print(
        "Permission service test: workspace isolation blocked="
        f"{str(snapshot.permission['workspace_isolation_blocked']).lower()}"
    )
    print(f"Security headers: {', '.join(snapshot.security['headers'].keys())}")
    print(
        "Upload MIME policy: "
        f"{json.dumps(snapshot.security['upload']['allowed_mime_types'], sort_keys=True)}"
    )
    print(f"Upload size limit: {snapshot.security['upload']['max_upload_bytes']} bytes")
    print(f"Production security check command: {snapshot.security['production_check_command']}")
    print(f"Deployment docs: {', '.join(snapshot.deployment['docs'])}")
    print(
        "Observability: "
        f"{snapshot.observability['trace']}, "
        f"{snapshot.observability['dashboard']}, "
        f"{snapshot.observability['request_id_header']}"
    )


if __name__ == "__main__":
    main()
