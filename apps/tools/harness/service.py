# coding=utf-8

from typing import Callable

import uuid_utils.compat as uuid
from django.db.models import QuerySet

from knowledge.models.knowledge_action import State
from tools.models import ToolRecord

from .action import ToolHarnessAction
from .observation import ToolObservation
from .policy import ToolHarnessPolicy


class ToolHarnessService:
    def __init__(self, policy: ToolHarnessPolicy | None = None):
        self.policy = policy or ToolHarnessPolicy()

    def test_connection(self, *, workspace_id: str, code: str, connect: Callable[[str], object], request=None):
        self.policy.ensure_allowed(
            ToolHarnessAction.TOOL_TEST_CONNECTION,
            request=request,
            workspace_id=workspace_id,
        )
        observation = ToolObservation(
            action=ToolHarnessAction.TOOL_TEST_CONNECTION,
            workspace_id=workspace_id,
            input={"code": code},
        )
        try:
            result = connect(code)
            observation.finish_success(result)
            return observation
        except Exception as exc:
            observation.finish_failure(exc)
            raise

    def observe_import(self, *, workspace_id: str, import_: Callable[[], object], request=None):
        return self._observe(
            action=ToolHarnessAction.TOOL_IMPORT,
            workspace_id=workspace_id,
            run=import_,
            request=request,
        )

    def observe_export(self, *, workspace_id: str, tool_id, export: Callable[[], object], request=None):
        return self._observe(
            action=ToolHarnessAction.TOOL_EXPORT,
            workspace_id=workspace_id,
            tool_id=str(tool_id),
            run=export,
            request=request,
        )

    def execute_tool(
        self,
        *,
        tool,
        params: dict,
        execute: Callable[[], object],
        source_type,
        source_id,
        record_id=None,
        workspace_id: str | None = None,
        output_serializer: Callable[[object], object] | None = None,
    ):
        workspace_id = workspace_id or tool.workspace_id
        self.policy.ensure_allowed(
            ToolHarnessAction.TOOL_EXECUTE,
            workspace_id=workspace_id,
            tool=tool,
        )
        observation = ToolObservation(
            action=ToolHarnessAction.TOOL_EXECUTE,
            workspace_id=workspace_id,
            tool_id=str(tool.id),
            source_type=source_type,
            source_id=str(source_id),
            record_id=str(record_id or uuid.uuid7()),
            input=params,
        )
        self._create_record(observation)
        try:
            result = execute()
            output = output_serializer(result) if output_serializer else result
            observation.finish_success(output)
            self._update_record(observation)
            return result, observation
        except Exception as exc:
            observation.finish_failure(exc)
            self._update_record(observation)
            raise

    def execute_workflow_tool_node(self, *, workspace_id: str, params: dict, execute: Callable[[], object]):
        observation = ToolObservation(
            action=ToolHarnessAction.WORKFLOW_TOOL_NODE_EXECUTE,
            workspace_id=workspace_id,
            input=params,
        )
        try:
            result = execute()
            observation.finish_success(result)
            return result, observation
        except Exception as exc:
            observation.finish_failure(exc)
            raise

    def _observe(self, *, action: ToolHarnessAction, workspace_id: str, run: Callable[[], object],
                 tool_id=None, request=None):
        self.policy.ensure_allowed(action, request=request, workspace_id=workspace_id, tool_id=tool_id)
        observation = ToolObservation(action=action, workspace_id=workspace_id, tool_id=tool_id)
        try:
            result = run()
            observation.finish_success(True)
            return result, observation
        except Exception as exc:
            observation.finish_failure(exc)
            raise

    @staticmethod
    def _create_record(observation: ToolObservation):
        ToolRecord(
            id=observation.record_id,
            workspace_id=observation.workspace_id,
            tool_id=observation.tool_id,
            source_type=observation.source_type,
            source_id=observation.source_id,
            meta=observation.to_meta(),
            state=State.STARTED,
        ).save()

    @staticmethod
    def _update_record(observation: ToolObservation):
        state = State.SUCCESS if observation.status == "success" else State.FAILURE
        QuerySet(ToolRecord).filter(id=observation.record_id).update(
            state=state,
            run_time=observation.run_time,
            meta=observation.to_meta(),
        )
