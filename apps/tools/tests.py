import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from rest_framework import serializers

from application.flow.common import WorkflowMode
from application.flow.step_node.tool_lib_node.impl.base_tool_lib_node import BaseToolLibNodeNode
from common.exception.app_exception import AppUnauthorizedFailed
from knowledge.models.knowledge_action import State
from tools.harness import ToolHarnessPolicy, ToolHarnessService, sanitize_parameters
from tools.harness.action import ToolHarnessAction
from tools.serializers.tool import ToolSerializer, validate_mcp_config
from tools.models import ToolTaskTypeChoices


class ToolConnectionTests(SimpleTestCase):
    def test_test_connection_validates_transport_and_json_config(self):
        config_code = json.dumps({"demo-server": {"command": "python", "args": ["-V"]}})

        with (
            patch("tools.serializers.tool.ToolExecutor.validate_mcp_transport") as mock_validate_transport,
            patch("tools.serializers.tool.validate_mcp_config") as mock_validate_config,
        ):
            result = ToolSerializer.TestConnection(
                data={"workspace_id": "workspace-1", "code": config_code}
            ).test_connection()

        self.assertEqual(result["state"], "success")
        self.assertEqual(result["workspace_id"], "workspace-1")
        self.assertEqual(result["meta"]["harness"]["action"], ToolHarnessAction.TOOL_TEST_CONNECTION.value)
        self.assertTrue(result["meta"]["output"])
        mock_validate_transport.assert_called_once_with(config_code)
        mock_validate_config.assert_called_once_with({"demo-server": {"command": "python", "args": ["-V"]}})

    def test_test_connection_raises_for_invalid_json(self):
        bad_json = "{not-a-valid-json"

        with (
            patch("tools.serializers.tool.ToolExecutor.validate_mcp_transport"),
            patch("tools.serializers.tool.validate_mcp_config") as mock_validate_config,
        ):
            with self.assertRaises(json.JSONDecodeError):
                ToolSerializer.TestConnection(
                    data={"workspace_id": "workspace-1", "code": bad_json}
                ).test_connection()

        mock_validate_config.assert_not_called()

    def test_test_connection_propagates_config_validation_errors(self):
        config_code = json.dumps({"timeout-server": {"command": "python", "args": ["server.py"]}})

        with (
            patch("tools.serializers.tool.ToolExecutor.validate_mcp_transport"),
            patch(
                "tools.serializers.tool.validate_mcp_config",
                side_effect=serializers.ValidationError("MCP configuration is invalid"),
            ),
        ):
            with self.assertRaises(serializers.ValidationError):
                ToolSerializer.TestConnection(
                    data={"workspace_id": "workspace-1", "code": config_code}
                ).test_connection()

    def test_validate_mcp_config_wraps_timeout_as_validation_error(self):
        with patch("tools.serializers.tool.asyncio.run", side_effect=TimeoutError("connect timeout")):
            with self.assertRaises(serializers.ValidationError) as ctx:
                validate_mcp_config({"demo": {"command": "python", "args": ["-V"]}})

        self.assertIn("MCP configuration is invalid", str(ctx.exception))


class ToolHarnessTests(SimpleTestCase):
    def test_policy_rejects_cross_workspace_tool(self):
        tool = SimpleNamespace(id="tool-1", workspace_id="workspace-a")

        with self.assertRaises(AppUnauthorizedFailed):
            ToolHarnessPolicy().ensure_tool_workspace(tool, "workspace-b")

    def test_sanitize_parameters_masks_sensitive_nested_values(self):
        sanitized = sanitize_parameters({
            "api_key": "secret",
            "nested": {
                "password": "pw",
                "safe": "visible",
            },
            "items": [{"token": "t"}],
        })

        self.assertEqual(sanitized["api_key"], "********")
        self.assertEqual(sanitized["nested"]["password"], "********")
        self.assertEqual(sanitized["nested"]["safe"], "visible")
        self.assertEqual(sanitized["items"][0]["token"], "********")

    def test_execute_tool_writes_sanitized_tool_record(self):
        tool = SimpleNamespace(id="11111111-1111-1111-1111-111111111111", workspace_id="workspace-1")
        record = Mock()
        update_query = Mock()

        with (
            patch("tools.harness.service.ToolRecord", return_value=record) as tool_record,
            patch("tools.harness.service.QuerySet") as query_set,
        ):
            query_set.return_value.filter.return_value = update_query

            result, observation = ToolHarnessService().execute_tool(
                tool=tool,
                params={"api_key": "secret", "query": "hello"},
                execute=lambda: {"answer": "ok"},
                source_type=ToolTaskTypeChoices.APPLICATION.value,
                source_id="22222222-2222-2222-2222-222222222222",
                record_id="33333333-3333-3333-3333-333333333333",
            )

        self.assertEqual(result, {"answer": "ok"})
        self.assertEqual(observation.status, "success")
        tool_record.assert_called_once()
        record.save.assert_called_once()
        update_query.update.assert_called_once()
        update_kwargs = update_query.update.call_args.kwargs
        self.assertEqual(update_kwargs["state"], State.SUCCESS)
        self.assertEqual(update_kwargs["meta"]["input"]["api_key"], "********")
        self.assertEqual(update_kwargs["meta"]["input"]["query"], "hello")
        self.assertEqual(update_kwargs["meta"]["harness"]["action"], ToolHarnessAction.TOOL_EXECUTE.value)

    def test_workflow_tool_node_failure_is_not_swallowed(self):
        workflow_manage = SimpleNamespace(
            flow=SimpleNamespace(workflow_mode=WorkflowMode.APPLICATION),
            params={"application_id": "22222222-2222-2222-2222-222222222222"},
        )
        node = SimpleNamespace(workflow_manage=workflow_manage, context={})
        tool = SimpleNamespace(
            id="11111111-1111-1111-1111-111111111111",
            workspace_id="workspace-1",
            init_params=None,
            code="raise",
        )

        with patch("application.flow.step_node.tool_lib_node.impl.base_tool_lib_node.ToolHarnessService") as service:
            service.return_value.execute_tool.side_effect = RuntimeError("boom")

            with self.assertRaises(RuntimeError):
                BaseToolLibNodeNode.tool_exec_record(node, tool, {"password": "secret"})

        service.return_value.execute_tool.assert_called_once()
