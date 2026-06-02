#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = ROOT / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from system_manage.services.platform_governance_demo import PlatformGovernanceDemo  # noqa: E402


def main() -> None:
    platform = PlatformGovernanceDemo()
    admin = platform.create_user("admin@example.com", "admin", "workspace-a")
    operator = platform.create_user("ops@example.com", "operator", "workspace-a")
    viewer = platform.create_user("viewer@example.com", "viewer", "workspace-b")

    provider = platform.onboard_model_provider("OpenAI", "https://api.example.com", {"api_key": "secret"})
    connection = platform.test_model_connection(provider.id)
    llm = platform.add_model(provider.id, "gpt-demo", "llm")
    embedding = platform.add_model(provider.id, "embedding-demo", "embedding")
    default_model = platform.set_default_model(llm.id)
    embedding_test = platform.test_embedding_model(embedding.id, "NebulaKB")

    tool = platform.create_tool(
        "policy-search",
        input_schema={"query": "string"},
        output_schema={"result": "string"},
        allowed_roles={"admin", "operator"},
    )
    tool_debug = platform.debug_tool(operator, tool.id, {"query": "refund", "api_key": "secret"})

    trigger = platform.create_trigger("daily-policy-check", tool.id, allowed_roles={"admin"})
    platform.set_trigger_enabled(trigger.id, True, admin)
    trigger_run = platform.run_trigger(trigger.id, admin)

    platform.authorize_resource(operator.id, tool.id, {"view", "debug"}, admin.id)
    platform.ensure_workspace_access(operator, "workspace-a")
    workspace_blocked = False
    try:
        platform.ensure_workspace_access(operator, "workspace-b")
    except PermissionError:
        workspace_blocked = True
    platform.disable_user(viewer.id, admin.id)

    sso = platform.configure_sso(
        "oidc",
        client_id="nebula-client",
        callback_url="https://nebulakb.example.com/sso/callback",
        enabled=True,
    )
    platform.record_audit(
        "api_key.rotated",
        admin.id,
        "api_key",
        "key-demo",
        {"api_key": "secret", "token": "token", "safe": "visible"},
    )

    print("NebulaKB demo: platform governance")
    print(f"Model provider onboarded: {provider.name}")
    print(f"Model connection: {connection['status']}")
    print(f"Embedding test dimension: {embedding_test['dimension']}")
    print(f"Default model: {default_model.name}, is_default={default_model.is_default}")
    print(f"Tool debug: {tool_debug['status']}, output={tool_debug['output']['result']}")
    print(f"Tool permissions: {sorted(tool.allowed_roles)}")
    print(f"Tool schema: input={tool.input_schema}, output={tool.output_schema}")
    print(f"Trigger enabled: {trigger.enabled}")
    print(f"Trigger target validated: {trigger.target_resource_id}")
    print(f"Trigger run count: {trigger_run['run_count']}")
    print(f"Permission matrix: {json.dumps(platform.permission_matrix(), ensure_ascii=False)}")
    print(f"Resource authorization: {sorted(platform.resource_grants[(operator.id, tool.id)])}")
    print(f"Workspace isolation blocked: {str(workspace_blocked).lower()}")
    print(f"User disabled: {viewer.email}, active={viewer.is_active}")
    print(f"SSO configured: {sso.provider}, enabled={sso.enabled}")
    print("Audit summary:")
    print(json.dumps(platform.audit_summary(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
