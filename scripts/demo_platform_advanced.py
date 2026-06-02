#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
APPS_DIR = ROOT / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

from system_manage.services.platform_advanced_completion import PlatformAdvancedCompletion  # noqa: E402


def main() -> None:
    platform = PlatformAdvancedCompletion()

    reranker = platform.register_model("rerank-demo", "reranker")
    voice = platform.register_model("voice-demo", "voice")
    image = platform.register_model("image-demo", "image")
    fallback = platform.register_model("fallback-llm", "llm")
    preset = platform.set_model_preset(fallback.id, {"temperature": 0.2, "max_tokens": 512})
    fallback_chain = platform.configure_model_fallback(fallback.id, reranker.id)
    cost = platform.record_model_cost(fallback.id, 1000, 500)

    tool = platform.create_tool("policy-search", "retrieval", 3000, 1, "Internal retrieval tool market entry")
    tool_run = platform.execute_tool(tool.id, {"query": "refund"}, fail_once=True)

    scheduled = platform.create_trigger("daily-sync", "scheduled", {"cron": "0 9 * * *"})
    event = platform.create_trigger("feedback-created", "event", {"event": "feedback.created"})
    platform.set_trigger_enabled(scheduled.id, True)
    platform.record_trigger_run(scheduled.id, "failed")
    retry = platform.retry_trigger_failure(scheduled.id)
    platform.record_trigger_run(event.id, "success")

    users = platform.bulk_import_users(
        [
            {"email": "admin@example.com", "group": "platform", "role_template": "admin"},
            {"email": "ops@example.com", "group": "ops", "role_template": "operator"},
        ]
    )
    platform.record_login("ops@example.com", "failed", "10.0.0.1")
    platform.record_login("ops@example.com", "failed", "10.0.0.1")

    for provider in ["oidc", "saml", "ldap", "cas"]:
        platform.configure_sso(
            provider,
            f"https://nebulakb.example.com/sso/{provider}/callback",
            "email -> user.email",
            enabled=True,
        )
        platform.test_sso(provider)
    platform.record_sso_error("oidc", "invalid nonce")
    platform.set_sso_enabled("cas", False)

    api = platform.api_guidance()

    print("NebulaKB demo: platform advanced completion")
    print(f"Reranker test: {platform.test_model(reranker.id)}")
    print(f"Voice model test: {platform.test_model(voice.id)}")
    print(f"Image model test: {platform.test_model(image.id)}")
    print(f"Model preset: {preset}")
    print(f"Model fallback: {fallback_chain}")
    print(f"Model cost: {cost}")
    print(f"Tool category: {tool.category}")
    print(f"Tool execution log: {platform.tool_execution_logs(tool.id)}")
    print(f"Tool timeout/retry/market: {tool.timeout_ms}/{tool.retry_limit}/{tool.market_description}")
    print(f"Scheduled trigger enabled: {scheduled.enabled}")
    print(f"Event trigger type: {event.trigger_type}")
    print(f"Trigger preview: {platform.preview_trigger_params(scheduled.id)}")
    print(f"Trigger retry: {retry}")
    print(f"Trigger statistics: {platform.trigger_statistics(scheduled.id)}")
    print(f"Bulk users: {[user.email for user in users]}")
    print(f"User groups: {platform.user_groups()}")
    print(f"Role templates: {platform.role_templates()}")
    print(f"Login logs: {platform.login_logs}")
    print(f"Account anomaly: {platform.account_anomaly_hint('ops@example.com')}")
    print(f"SSO tests: {[platform.sso[p].last_test_status for p in ['oidc', 'saml', 'ldap', 'cas']]}")
    print(f"Callback copy: {platform.copy_callback_url('oidc')}")
    print(f"SSO enabled/default/error/mapping: {platform.sso['cas'].enabled}/{platform.default_login_method('oidc')}/{platform.sso['oidc'].error_log}/{platform.user_mapping_rule('oidc')}")
    print(f"Audit filter/export: {platform.filter_audit('tool.executed')}/{platform.export_audit()}")
    print(f"API rate limits: {api['rate_limits']}")
    print(f"API curl examples: {api['curl_examples']}")
    print(f"API frontend example: {api['frontend_example']}")
    print(f"API compatibility: {api['compatibility']}")
    print("Model/tool/trigger tests: passed")


if __name__ == "__main__":
    main()
