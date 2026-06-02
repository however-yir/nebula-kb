from django.test import SimpleTestCase

from system_manage.services.platform_governance_demo import PlatformGovernanceDemo, redact_payload
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
