from django.test import SimpleTestCase

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
