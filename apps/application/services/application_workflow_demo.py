from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ApplicationRecord:
    id: str
    name: str
    application_type: str
    owner: str
    version: int = 0
    status: str = "draft"
    api_keys: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)
    published_at: datetime | None = None


@dataclass
class WorkflowNode:
    id: str
    node_type: str
    label: str


@dataclass
class WorkflowEdge:
    source: str
    target: str
    label: str = "next"


@dataclass
class WorkflowRunLog:
    run_id: str
    application_id: str
    status: str
    steps: list[dict[str, str]]
    started_at: datetime = field(default_factory=_now)
    completed_at: datetime | None = None


class ApplicationWorkflowPlatform:
    """Small acceptance model for application/workflow product contracts."""

    def __init__(self) -> None:
        self.applications: dict[str, ApplicationRecord] = {}
        self.run_logs: list[WorkflowRunLog] = []

    def create_application(self, name: str, application_type: str, owner: str) -> ApplicationRecord:
        if application_type not in {"simple", "workflow"}:
            raise ValueError("application_type must be simple or workflow")
        application = ApplicationRecord(
            id=f"app-{uuid4().hex[:8]}",
            name=name,
            application_type=application_type,
            owner=owner,
        )
        self.applications[application.id] = application
        return application

    def publish_version(self, application_id: str) -> ApplicationRecord:
        application = self._require_application(application_id)
        application.version += 1
        application.status = "published"
        application.published_at = _now()
        return application

    def create_api_key(self, application_id: str, name: str) -> str:
        application = self._require_application(application_id)
        key = f"nebula_{application.id}_{name}_{uuid4().hex[:12]}"
        application.api_keys.append(key)
        return key

    def node_catalog(self) -> list[dict[str, object]]:
        return [
            {
                "type": "start",
                "label": "Start",
                "description": "Entry point that receives user input and request metadata.",
                "inputs": [],
                "outputs": ["question", "user_id"],
            },
            {
                "type": "condition",
                "label": "Condition",
                "description": "Routes the workflow by evaluating one explicit rule.",
                "inputs": ["left", "operator", "right"],
                "outputs": ["true", "false"],
            },
            {
                "type": "answer",
                "label": "Answer",
                "description": "Returns the final response and records citations or fallback status.",
                "inputs": ["content"],
                "outputs": ["response"],
            },
        ]

    def validate_connections(self, nodes: list[WorkflowNode], edges: list[WorkflowEdge]) -> list[str]:
        errors: list[str] = []
        node_ids = {node.id for node in nodes}
        start_nodes = [node for node in nodes if node.node_type == "start"]
        if len(start_nodes) != 1:
            errors.append("workflow must contain exactly one start node")

        for edge in edges:
            if edge.source not in node_ids:
                errors.append(f"edge source does not exist: {edge.source}")
            if edge.target not in node_ids:
                errors.append(f"edge target does not exist: {edge.target}")
            if edge.source == edge.target:
                errors.append(f"self loop is not allowed: {edge.source}")

        for node in nodes:
            if node.node_type == "condition":
                labels = {edge.label for edge in edges if edge.source == node.id}
                if labels != {"true", "false"}:
                    errors.append(f"condition node requires true and false outputs: {node.id}")
        return errors

    def test_condition(self, left: object, operator: str, right: object) -> bool:
        if operator == "equals":
            return left == right
        if operator == "contains":
            return str(right) in str(left)
        if operator == "gt":
            return float(left) > float(right)
        raise ValueError(f"unsupported condition operator: {operator}")

    def debug_workflow(
        self,
        application_id: str,
        nodes: list[WorkflowNode],
        edges: list[WorkflowEdge],
        question: str,
    ) -> WorkflowRunLog:
        application = self._require_application(application_id)
        errors = self.validate_connections(nodes, edges)
        if errors:
            run = WorkflowRunLog(
                run_id=f"run-{uuid4().hex[:8]}",
                application_id=application.id,
                status="failed",
                steps=[{"event": "validation_failed", "detail": "; ".join(errors)}],
                completed_at=_now(),
            )
            self.run_logs.append(run)
            return run

        steps = [
            {"event": "workflow_started", "detail": f"{application.name} received: {question}"},
            {"event": "node_executed", "detail": "start"},
            {"event": "node_executed", "detail": "condition"},
            {"event": "node_executed", "detail": "answer"},
            {"event": "workflow_completed", "detail": "success"},
        ]
        run = WorkflowRunLog(
            run_id=f"run-{uuid4().hex[:8]}",
            application_id=application.id,
            status="success",
            steps=steps,
            completed_at=_now(),
        )
        self.run_logs.append(run)
        return run

    def list_run_logs(self, application_id: str) -> list[WorkflowRunLog]:
        return [run for run in self.run_logs if run.application_id == application_id]

    def _require_application(self, application_id: str) -> ApplicationRecord:
        application = self.applications.get(application_id)
        if application is None:
            raise KeyError(application_id)
        return application
