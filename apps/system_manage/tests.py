from django.test import SimpleTestCase

from system_manage.serializers.knowledge_ops import KnowledgeOpsDashboardSerializer


class KnowledgeOpsDashboardSerializerTests(SimpleTestCase):
    def test_dashboard_contract_covers_enterprise_operating_modules(self):
        dashboard = KnowledgeOpsDashboardSerializer(data={"workspace_id": "default"}).get_dashboard()

        expected_keys = {
            "metrics",
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
