# coding=utf-8

from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from common.auth.authentication import get_is_permissions
from common.constants.permission_constants import (
    CompareConstants,
    PermissionConstants,
    RoleConstants,
    ViewPermission,
)
from common.exception.app_exception import AppUnauthorizedFailed
from tools.models import Tool

from .action import ToolHarnessAction


def _tool_view_permission():
    return ViewPermission(
        [RoleConstants.USER.get_workspace_role()],
        [PermissionConstants.TOOL.get_workspace_tool_permission()],
        CompareConstants.AND,
    )


class ToolHarnessPolicy:
    def ensure_tool_workspace(self, tool, workspace_id: str):
        if tool is None or str(tool.workspace_id) != str(workspace_id):
            raise AppUnauthorizedFailed(403, _("No permission to access"))
        return tool

    def get_workspace_tool(self, tool_id, workspace_id: str):
        tool = QuerySet(Tool).filter(id=tool_id).first()
        return self.ensure_tool_workspace(tool, workspace_id)

    def ensure_request_permissions(self, request, permissions: tuple, **kwargs):
        if request is None or not permissions:
            return
        is_permissions = get_is_permissions(request, **kwargs)
        if not is_permissions(*permissions):
            raise AppUnauthorizedFailed(403, _("No permission to access"))

    def ensure_allowed(self, action: ToolHarnessAction, request=None, workspace_id=None, tool=None, tool_id=None):
        if tool is not None:
            self.ensure_tool_workspace(tool, workspace_id)
            tool_id = str(tool.id)
        elif tool_id is not None and workspace_id is not None:
            self.get_workspace_tool(tool_id, workspace_id)

        permissions = self.get_action_permissions(action)
        self.ensure_request_permissions(
            request,
            permissions,
            workspace_id=workspace_id,
            tool_id=tool_id,
        )

    @staticmethod
    def get_action_permissions(action: ToolHarnessAction) -> tuple:
        if action == ToolHarnessAction.TOOL_TEST_CONNECTION:
            return (
                PermissionConstants.TOOL_CREATE.get_workspace_permission(),
                PermissionConstants.TOOL_CREATE.get_workspace_permission_workspace_manage_role(),
                PermissionConstants.TOOL_EDIT.get_workspace_permission(),
                PermissionConstants.TOOL_EDIT.get_workspace_permission_workspace_manage_role(),
                RoleConstants.WORKSPACE_MANAGE.get_workspace_role(),
                RoleConstants.USER.get_workspace_role(),
            )
        if action == ToolHarnessAction.TOOL_IMPORT:
            return (
                PermissionConstants.TOOL_IMPORT.get_workspace_permission(),
                PermissionConstants.TOOL_IMPORT.get_workspace_permission_workspace_manage_role(),
                RoleConstants.WORKSPACE_MANAGE.get_workspace_role(),
                RoleConstants.USER.get_workspace_role(),
            )
        if action == ToolHarnessAction.TOOL_EXPORT:
            return (
                PermissionConstants.TOOL_EXPORT.get_workspace_tool_permission(),
                PermissionConstants.TOOL_EXPORT.get_workspace_permission_workspace_manage_role(),
                RoleConstants.WORKSPACE_MANAGE.get_workspace_role(),
                _tool_view_permission(),
            )
        if action in (ToolHarnessAction.TOOL_EXECUTE, ToolHarnessAction.WORKFLOW_TOOL_NODE_EXECUTE):
            return (
                PermissionConstants.TOOL_READ.get_workspace_tool_permission(),
                PermissionConstants.TOOL_READ.get_workspace_permission_workspace_manage_role(),
                RoleConstants.WORKSPACE_MANAGE.get_workspace_role(),
                _tool_view_permission(),
            )
        return ()
