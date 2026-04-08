import json
from unittest.mock import patch

from django.test import SimpleTestCase

from tools.serializers.tool import ToolSerializer


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
