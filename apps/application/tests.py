from django.test import SimpleTestCase

from application.services.application_experience_completion import ApplicationExperienceCompletion
from application.services.application_workflow_demo import (
    ApplicationWorkflowPlatform,
    WorkflowEdge,
    WorkflowNode,
)


class ApplicationWorkflowDemoTests(SimpleTestCase):
    def setUp(self):
        self.platform = ApplicationWorkflowPlatform()

    def test_application_create_type_version_and_api_key_contract(self):
        simple = self.platform.create_application("FAQ 助手", "simple", owner="app-ops")
        workflow = self.platform.create_application("反馈处理工作流", "workflow", owner="app-ops")
        published = self.platform.publish_version(workflow.id)
        api_key = self.platform.create_api_key(workflow.id, "demo")

        self.assertEqual(simple.application_type, "simple")
        self.assertEqual(workflow.application_type, "workflow")
        self.assertEqual(published.version, 1)
        self.assertEqual(published.status, "published")
        self.assertTrue(api_key.startswith(f"nebula_{workflow.id}_demo_"))
        self.assertEqual(workflow.api_keys, [api_key])

        with self.assertRaisesRegex(ValueError, "simple or workflow"):
            self.platform.create_application("坏类型", "agent", owner="app-ops")

    def test_workflow_docs_connection_condition_debug_and_run_logs(self):
        application = self.platform.create_application("反馈处理工作流", "workflow", owner="app-ops")
        nodes = [
            WorkflowNode("start", "start", "Start"),
            WorkflowNode("condition", "condition", "低分判断"),
            WorkflowNode("answer", "answer", "返回处理结果"),
        ]
        edges = [
            WorkflowEdge("start", "condition"),
            WorkflowEdge("condition", "answer", "true"),
            WorkflowEdge("condition", "answer", "false"),
        ]

        self.assertIn("condition", [node["type"] for node in self.platform.node_catalog()])
        self.assertEqual(self.platform.validate_connections(nodes, edges), [])
        self.assertTrue(self.platform.test_condition(1, "equals", 1))
        self.assertTrue(self.platform.test_condition("低质答案", "contains", "低质"))
        self.assertTrue(self.platform.test_condition(3, "gt", 2))

        run = self.platform.debug_workflow(application.id, nodes, edges, "点踩之后谁处理？")
        self.assertEqual(run.status, "success")
        self.assertEqual(
            [step["event"] for step in run.steps],
            [
                "workflow_started",
                "node_executed",
                "node_executed",
                "node_executed",
                "workflow_completed",
            ],
        )
        self.assertEqual(self.platform.list_run_logs(application.id), [run])

    def test_workflow_connection_validation_blocks_bad_edges(self):
        application = self.platform.create_application("坏工作流", "workflow", owner="app-ops")
        nodes = [
            WorkflowNode("start", "start", "Start"),
            WorkflowNode("condition", "condition", "低分判断"),
        ]
        edges = [
            WorkflowEdge("start", "missing"),
            WorkflowEdge("condition", "condition", "true"),
        ]

        errors = self.platform.validate_connections(nodes, edges)
        self.assertIn("edge target does not exist: missing", errors)
        self.assertIn("self loop is not allowed: condition", errors)
        self.assertIn("condition node requires true and false outputs: condition", errors)

        run = self.platform.debug_workflow(application.id, nodes, edges, "坏连线")
        self.assertEqual(run.status, "failed")
        self.assertEqual(run.steps[0]["event"], "validation_failed")


class ApplicationExperienceCompletionTests(SimpleTestCase):
    def setUp(self):
        self.platform = ApplicationExperienceCompletion()

    def test_feedback_dashboard_metrics_and_exports(self):
        first = self.platform.submit_feedback(
            "How do I validate citations?",
            1,
            "missing_citation",
            "The answer needs source evidence.",
        )
        self.platform.assign_feedback(first.id, "quality-owner")
        self.platform.update_feedback_status(first.id, "fixed", "Added missing citation.")
        self.platform.submit_feedback("Why is it slow?", 3, "slow_response", "Generation felt slow.")

        trend = self.platform.feedback_trend()
        dashboard = self.platform.operations_dashboard(
            time_range="30d",
            knowledge_base_id="kb-release",
            application_id="app-release",
            user_id="operator",
        )
        chart = self.platform.export_dashboard_chart("low_quality_answer_rate")
        daily = self.platform.export_daily_report()

        self.assertEqual(first.owner, "quality-owner")
        self.assertEqual(first.status, "fixed")
        self.assertEqual(first.note, "Added missing citation.")
        self.assertEqual(trend["by_reason"]["missing_citation"], 1)
        self.assertEqual(trend["by_status"]["fixed"], 1)
        self.assertEqual(dashboard["filters"]["time_range"], "30d")
        self.assertEqual(dashboard["filters"]["knowledge_base_id"], "kb-release")
        self.assertEqual(dashboard["filters"]["application_id"], "app-release")
        self.assertEqual(dashboard["filters"]["user_id"], "operator")
        self.assertEqual(dashboard["metrics"]["average_retrieval_latency_ms"], 42)
        self.assertEqual(dashboard["metrics"]["average_generation_latency_ms"], 180)
        self.assertEqual(dashboard["metrics"]["token_usage"], 1280)
        self.assertIn("How do I validate citations?", dashboard["top_questions"])
        self.assertEqual(dashboard["knowledge_health_trend"], [92, 94, 91])
        self.assertIn("knowledge_hit_rate", dashboard["tooltips"])
        self.assertIn("No data", dashboard["empty_state"])
        self.assertEqual(dashboard["anomaly_highlights"], ["low_quality_answer_rate"])
        self.assertEqual(chart["format"], "csv")
        self.assertEqual(daily["format"], "markdown")

    def test_application_templates_copy_rollback_embed_share_and_node_acceptance(self):
        app = self.platform.create_from_template("review", "Feedback Review App", "app-owner")
        self.platform.publish_application(app.id)
        self.platform.publish_application(app.id)
        self.platform.rollback_application(app.id, 1)
        copied = self.platform.copy_application(app.id, "Feedback Review Copy")
        access_count = self.platform.record_application_access(app.id, 12)
        embed = self.platform.configure_embed(app.id, ["support.example.com"], "light")
        share = self.platform.configure_share_link(app.id, "workspace", 7)

        self.assertEqual(app.template_id, "review")
        self.assertEqual(copied.application_type, "workflow")
        self.assertEqual(app.current_version, 1)
        self.assertEqual(access_count, 12)
        self.assertEqual(embed["domains"], ["support.example.com"])
        self.assertEqual(share["mode"], "workspace")
        self.assertEqual(share["expires_days"], 7)

        catalog = self.platform.workflow_node_catalog()
        search = self.platform.search_nodes("retrieval")
        snapped = self.platform.snap_node_position(53, 71)
        loop_hint = self.platform.loop_boundary_hint(10)
        preview = self.platform.preview_node_io("retrieval")
        debug = self.platform.debug_single_node("retrieval", {"query": "refund"})
        failed_debug = self.platform.debug_single_node("retrieval", {})
        summary = self.platform.node_acceptance_summary()

        self.assertEqual(len(catalog), 10)
        self.assertEqual(search[0]["type"], "retrieval")
        self.assertEqual(snapped, {"x": 48, "y": 72})
        self.assertIn("10 iterations", loop_hint)
        self.assertEqual(preview["inputs"], ["query"])
        self.assertEqual(preview["outputs"], ["hits"])
        self.assertEqual(debug["status"], "success")
        self.assertEqual(failed_debug["status"], "failed")
        self.assertEqual(summary["total"], 10)
        self.assertEqual(summary["passed"], 10)
        self.assertEqual(
            summary["types"],
            [
                "knowledge_write",
                "application",
                "retrieval",
                "tool",
                "variable",
                "loop",
                "condition",
                "extract",
                "reranker",
                "reply",
            ],
        )
