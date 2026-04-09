import json
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework import serializers

from tools.serializers.tool import ToolSerializer, validate_mcp_config


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

        self.assertTrue(result)
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
