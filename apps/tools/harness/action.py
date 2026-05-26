# coding=utf-8

from enum import Enum


class ToolHarnessAction(str, Enum):
    TOOL_TEST_CONNECTION = "tool.test_connection"
    TOOL_EXECUTE = "tool.execute"
    TOOL_IMPORT = "tool.import"
    TOOL_EXPORT = "tool.export"
    WORKFLOW_TOOL_NODE_EXECUTE = "workflow.tool_node.execute"
