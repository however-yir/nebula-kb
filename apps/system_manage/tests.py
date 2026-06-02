from django.test import SimpleTestCase

from system_manage.services.platform_advanced_completion import PlatformAdvancedCompletion
from system_manage.services.platform_governance_demo import PlatformGovernanceDemo, redact_payload
from system_manage.services.release_acceptance import ReleaseAcceptanceDemo
from system_manage.serializers.knowledge_ops import KnowledgeOpsDashboardSerializer


class KnowledgeOpsDashboardSerializerTests(SimpleTestCase):
    def test_dashboard_contract_covers_enterprise_operating_modules(self):
        dashboard = KnowledgeOpsDashboardSerializer(data={"workspace_id": "default"}).get_dashboard()

        expected_keys = {
            "metrics",
            "knowledge_health",
            "feedback_governance_tasks",
            "low_quality_reviews",
            "missed_question_clusters",
            "lifecycle",
            "freshness",
            "conflicts",
            "source_credibility",
            "expiring_documents",
            "qa_hit_rate_daily",
            "feedback_loop",
            "department_permission_templates",
            "tenant_branding",
            "tenant_isolation",
            "assistant_templates",
            "industry_template_packs",
            "ingestion_wizard",
            "data_source_health",
            "retrieval_observability",
            "prompt_versions",
            "workflow_gray_release",
            "ab_experiments",
            "quality_evaluation",
            "rag_benchmarks",
            "pii_policy",
            "tamper_proof_audit",
            "api_key_scopes",
            "sso_role_mapping",
            "slo_error_budget",
            "release_acceptance",
            "backup_drill",
            "citation_chain",
            "visual_system",
        }

        assert dashboard["positioning"]["one_liner"] == "知识运营中枢"
        assert expected_keys.issubset(dashboard.keys())
        assert dashboard["tenant_isolation"]["enabled"] is True
        assert dashboard["workflow_gray_release"]["percent"] == 20
        assert dashboard["metrics"][0]["label"] == "知识命中率"
        assert dashboard["knowledge_health"][0]["knowledge_base_id"] == "kb-cs"
        assert dashboard["low_quality_reviews"][0]["status"] == "open"


class PlatformGovernanceDemoTests(SimpleTestCase):
    def setUp(self):
        self.platform = PlatformGovernanceDemo()
        self.admin = self.platform.create_user("admin@example.com", "admin", "workspace-a")
        self.operator = self.platform.create_user("ops@example.com", "operator", "workspace-a")
        self.outsider = self.platform.create_user("other@example.com", "viewer", "workspace-b")

    def test_model_provider_connection_embedding_and_default_model(self):
        provider = self.platform.onboard_model_provider(
            "OpenAI",
            "https://api.example.com",
            {"api_key": "secret"},
        )
        connection = self.platform.test_model_connection(provider.id)
        llm = self.platform.add_model(provider.id, "gpt-demo", "llm")
        embedding = self.platform.add_model(provider.id, "embedding-demo", "embedding")
        default = self.platform.set_default_model(llm.id)
        embedding_test = self.platform.test_embedding_model(embedding.id, "NebulaKB")

        self.assertEqual(connection["status"], "ok")
        self.assertTrue(default.is_default)
        self.assertEqual(embedding_test["status"], "ok")
        self.assertGreater(embedding_test["dimension"], 0)
        provider_event = [
            event for event in self.platform.audit_events if event.event_name == "model_provider.created"
        ][0]
        self.assertEqual(provider_event.payload["api_key"], "********")

    def test_tool_debug_permission_and_schema_validation(self):
        tool = self.platform.create_tool(
            "policy-search",
            input_schema={"query": "string"},
            output_schema={"result": "string"},
            allowed_roles={"admin", "operator"},
        )
        result = self.platform.debug_tool(self.operator, tool.id, {"query": "refund", "api_key": "secret"})

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["output"]["result"], "policy-search: refund")
        self.assertEqual(self.platform.audit_events[-1].payload["params"]["api_key"], "********")

        with self.assertRaisesRegex(ValueError, "missing field"):
            self.platform.debug_tool(self.operator, tool.id, {"api_key": "secret"})
        with self.assertRaises(PermissionError):
            self.platform.debug_tool(self.outsider, tool.id, {"query": "refund"})

    def test_trigger_enable_target_and_permission_validation(self):
        tool = self.platform.create_tool(
            "policy-search",
            input_schema={"query": "string"},
            output_schema={"result": "string"},
            allowed_roles={"admin"},
        )
        trigger = self.platform.create_trigger("daily-policy-check", tool.id, allowed_roles={"admin"})

        with self.assertRaises(PermissionError):
            self.platform.set_trigger_enabled(trigger.id, True, self.operator)

        self.platform.set_trigger_enabled(trigger.id, True, self.admin)
        run = self.platform.run_trigger(trigger.id, self.admin)

        self.assertTrue(trigger.enabled)
        self.assertEqual(run["status"], "success")
        self.assertEqual(run["run_count"], 1)

        broken = self.platform.create_trigger("missing-target", "missing-resource", allowed_roles={"admin"})
        self.platform.set_trigger_enabled(broken.id, True, self.admin)
        with self.assertRaisesRegex(ValueError, "target resource"):
            self.platform.run_trigger(broken.id, self.admin)

    def test_user_disable_permission_matrix_resource_grants_and_workspace_isolation(self):
        matrix = self.platform.permission_matrix()
        self.platform.authorize_resource(self.operator.id, "tool-1", {"view", "debug"}, self.admin.id)

        self.assertIn("debug", matrix["tool"])
        self.assertEqual(self.platform.resource_grants[(self.operator.id, "tool-1")], {"view", "debug"})
        self.platform.ensure_workspace_access(self.operator, "workspace-a")
        with self.assertRaises(PermissionError):
            self.platform.ensure_workspace_access(self.operator, "workspace-b")

        self.platform.disable_user(self.operator.id, self.admin.id)
        with self.assertRaises(PermissionError):
            self.platform.ensure_workspace_access(self.operator, "workspace-a")

    def test_sso_config_and_audit_redaction(self):
        config = self.platform.configure_sso(
            provider="oidc",
            client_id="nebula-client",
            callback_url="https://nebulakb.example.com/sso/callback",
            enabled=True,
        )
        self.platform.record_audit(
            "resource.updated",
            self.admin.id,
            "api_key",
            "key-1",
            {"api_key": "secret", "nested": {"password": "pw"}, "safe": "visible"},
        )

        self.assertTrue(config.enabled)
        self.assertEqual(self.platform.audit_events[-2].payload["client_secret"], "********")
        self.assertEqual(self.platform.audit_events[-1].payload["api_key"], "********")
        self.assertEqual(self.platform.audit_events[-1].payload["nested"]["password"], "********")
        self.assertEqual(self.platform.audit_events[-1].payload["safe"], "visible")
        self.assertEqual(redact_payload({"token": "abc"})["token"], "********")


class ReleaseAcceptanceDemoTests(SimpleTestCase):
    def test_api_security_deployment_observability_and_e2e_snapshot(self):
        snapshot = ReleaseAcceptanceDemo().snapshot()

        self.assertEqual(snapshot.api["api_v1_prefix"], "/api/v1")
        self.assertEqual(snapshot.api["openapi_version"], "3.1.0")
        self.assertIn("bearer", snapshot.api["auth_schemes"])
        self.assertEqual(snapshot.e2e["document_status"], "indexed")
        self.assertGreaterEqual(snapshot.e2e["citation_count"], 1)
        self.assertEqual(snapshot.e2e["feedback_rating"], 1)
        self.assertTrue(snapshot.permission["workspace_isolation_blocked"])
        self.assertIn("Content-Security-Policy", snapshot.security["headers"])
        self.assertEqual(
            snapshot.security["production_check_command"],
            "scripts/production-security-check.sh",
        )
        self.assertIn("docs/enterprise/deployment-guide.md", snapshot.deployment["docs"])
        self.assertEqual(snapshot.observability["request_id_header"], "X-Request-ID")


class PlatformAdvancedCompletionTests(SimpleTestCase):
    def setUp(self):
        self.platform = PlatformAdvancedCompletion()

    def test_model_tool_trigger_user_sso_audit_and_api_guidance(self):
        reranker = self.platform.register_model("rerank-demo", "reranker")
        voice = self.platform.register_model("voice-demo", "voice")
        image = self.platform.register_model("image-demo", "image")
        fallback = self.platform.register_model("fallback-llm", "llm")

        self.assertEqual(self.platform.test_model(reranker.id)["status"], "ok")
        self.assertEqual(self.platform.test_model(voice.id)["sample_rate"], 16000)
        self.assertEqual(self.platform.test_model(image.id)["width"], 512)
        self.assertEqual(self.platform.set_model_preset(fallback.id, {"temperature": 0.2})["temperature"], 0.2)
        self.assertEqual(
            self.platform.configure_model_fallback(fallback.id, reranker.id)["status"],
            "configured",
        )
        self.assertGreater(self.platform.record_model_cost(fallback.id, 1000, 500)["cost_usd"], 0)

        tool = self.platform.create_tool(
            "policy-search",
            category="retrieval",
            timeout_ms=3000,
            retry_limit=1,
            market_description="Internal retrieval tool market entry",
        )
        run = self.platform.execute_tool(tool.id, {"query": "refund"}, fail_once=True)
        self.assertEqual(tool.category, "retrieval")
        self.assertEqual(run["attempts"], 2)
        self.assertEqual(self.platform.tool_execution_logs(tool.id)[0]["status"], "success")
        self.assertIn("market", tool.market_description)

        scheduled = self.platform.create_trigger("daily-sync", "scheduled", {"cron": "0 9 * * *"})
        event = self.platform.create_trigger("feedback-created", "event", {"event": "feedback.created"})
        self.platform.set_trigger_enabled(scheduled.id, True)
        self.platform.record_trigger_run(scheduled.id, "failed")
        retry = self.platform.retry_trigger_failure(scheduled.id)
        self.platform.record_trigger_run(event.id, "success")
        self.assertTrue(scheduled.enabled)
        self.assertEqual(event.trigger_type, "event")
        self.assertEqual(self.platform.preview_trigger_params(scheduled.id)["cron"], "0 9 * * *")
        self.assertEqual(retry["status"], "success")
        self.assertEqual(self.platform.trigger_statistics(scheduled.id), {"total": 2, "success": 1, "failed": 1})

        users = self.platform.bulk_import_users(
            [
                {"email": "admin@example.com", "group": "platform", "role_template": "admin"},
                {"email": "ops@example.com", "group": "ops", "role_template": "operator"},
            ]
        )
        self.platform.record_login("ops@example.com", "failed", "10.0.0.1")
        self.platform.record_login("ops@example.com", "failed", "10.0.0.1")
        self.assertEqual(len(users), 2)
        self.assertEqual(self.platform.user_groups()["ops"], ["ops@example.com"])
        self.assertIn("audit_export", self.platform.role_templates()["admin"])
        self.assertEqual(self.platform.account_anomaly_hint("ops@example.com"), "account requires review")

        for provider in ["oidc", "saml", "ldap", "cas"]:
            self.platform.configure_sso(
                provider,
                f"https://nebulakb.example.com/sso/{provider}/callback",
                "email -> user.email",
                enabled=True,
            )
            self.assertEqual(self.platform.test_sso(provider)["status"], "ok")
        self.assertIn("/oidc/callback", self.platform.copy_callback_url("oidc"))
        self.assertFalse(self.platform.set_sso_enabled("cas", False))
        self.assertEqual(self.platform.default_login_method("oidc"), "oidc")
        self.assertEqual(self.platform.record_sso_error("oidc", "invalid nonce"), ["invalid nonce"])
        self.assertEqual(self.platform.user_mapping_rule("oidc"), "email -> user.email")

        self.assertEqual(len(self.platform.filter_audit("tool.executed")), 1)
        self.assertEqual(self.platform.export_audit()["format"], "jsonl")

        api = self.platform.api_guidance()
        self.assertEqual(api["rate_limits"]["user"], "300/min")
        self.assertIn("curl", api["curl_examples"][0])
        self.assertIn("fetch", api["frontend_example"])
        self.assertIn("stable", api["compatibility"])
