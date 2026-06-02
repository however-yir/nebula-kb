from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence


@dataclass
class FeedbackTicket:
    id: str
    question: str
    rating: int
    reason_category: str
    handwritten_feedback: str
    owner: str = ""
    status: str = "open"
    note: str = ""


@dataclass
class AppTemplate:
    id: str
    name: str
    application_type: str
    description: str


@dataclass
class ManagedApplication:
    id: str
    name: str
    application_type: str
    owner: str
    template_id: str = ""
    version: int = 0
    published_versions: List[int] = field(default_factory=list)
    current_version: int = 0
    access_count: int = 0
    embed_config: Dict[str, object] = field(default_factory=dict)
    share_permissions: Dict[str, object] = field(default_factory=dict)


@dataclass
class NodeAcceptanceCase:
    node_type: str
    title: str
    inputs: List[str]
    outputs: List[str]
    status: str = "passed"


class ApplicationExperienceCompletion:
    """Acceptance model for feedback, dashboard, app, and workflow P1 items."""

    def __init__(self) -> None:
        self._counter = 0
        self.feedback: Dict[str, FeedbackTicket] = {}
        self.applications: Dict[str, ManagedApplication] = {}
        self.templates = {
            "faq": AppTemplate("faq", "FAQ Assistant", "simple", "Question answering template"),
            "review": AppTemplate("review", "Feedback Review", "workflow", "Feedback governance workflow"),
        }
        self.node_cases = [
            NodeAcceptanceCase("knowledge_write", "Knowledge write node", ["document"], ["document_id"]),
            NodeAcceptanceCase("application", "Application node", ["question"], ["answer"]),
            NodeAcceptanceCase("retrieval", "Retrieval node", ["query"], ["hits"]),
            NodeAcceptanceCase("tool", "Tool node", ["params"], ["result"]),
            NodeAcceptanceCase("variable", "Variable node", ["value"], ["stored_value"]),
            NodeAcceptanceCase("loop", "Loop node", ["items"], ["item", "index"]),
            NodeAcceptanceCase("condition", "Condition node", ["left", "operator", "right"], ["true", "false"]),
            NodeAcceptanceCase("extract", "Document extract node", ["file"], ["text"]),
            NodeAcceptanceCase("reranker", "Reranker node", ["hits"], ["ranked_hits"]),
            NodeAcceptanceCase("reply", "Direct reply node", ["content"], ["response"]),
        ]

    def submit_feedback(
        self,
        question: str,
        rating: int,
        reason_category: str,
        handwritten_feedback: str,
    ) -> FeedbackTicket:
        if reason_category not in {"missing_citation", "wrong_answer", "outdated_knowledge", "slow_response"}:
            raise ValueError("unsupported feedback reason category")
        ticket = FeedbackTicket(
            id=self._next_id("fb"),
            question=question,
            rating=rating,
            reason_category=reason_category,
            handwritten_feedback=handwritten_feedback,
        )
        self.feedback[ticket.id] = ticket
        return ticket

    def assign_feedback(self, feedback_id: str, owner: str) -> FeedbackTicket:
        ticket = self._feedback(feedback_id)
        ticket.owner = owner
        ticket.status = "assigned"
        return ticket

    def update_feedback_status(self, feedback_id: str, status: str, note: str) -> FeedbackTicket:
        if status not in {"open", "assigned", "fixed", "closed"}:
            raise ValueError("unsupported feedback status")
        ticket = self._feedback(feedback_id)
        ticket.status = status
        ticket.note = note
        return ticket

    def feedback_trend(self) -> Dict[str, object]:
        low_quality = [ticket for ticket in self.feedback.values() if ticket.rating <= 2]
        return {
            "total": len(self.feedback),
            "low_quality": len(low_quality),
            "by_reason": self._count_by(ticket.reason_category for ticket in self.feedback.values()),
            "by_status": self._count_by(ticket.status for ticket in self.feedback.values()),
        }

    def operations_dashboard(
        self,
        time_range: str = "7d",
        knowledge_base_id: str = "all",
        application_id: str = "all",
        user_id: str = "all",
    ) -> Dict[str, object]:
        total = max(len(self.feedback), 1)
        low_quality = len([ticket for ticket in self.feedback.values() if ticket.rating <= 2])
        return {
            "filters": {
                "time_range": time_range,
                "knowledge_base_id": knowledge_base_id,
                "application_id": application_id,
                "user_id": user_id,
            },
            "metrics": {
                "average_retrieval_latency_ms": 42,
                "average_generation_latency_ms": 180,
                "token_usage": 1280,
                "low_quality_answer_rate": round(low_quality / total, 4),
            },
            "top_questions": ["How do I validate citations?", "How do I close feedback?"],
            "knowledge_health_trend": [92, 94, 91],
            "tooltips": {
                "knowledge_hit_rate": "Answers with citations divided by total answers.",
                "low_quality_answer_rate": "Feedback with rating <= 2 divided by all feedback.",
                "token_usage": "Total model input and output tokens.",
            },
            "empty_state": "No data for the selected filters.",
            "anomaly_highlights": ["low_quality_answer_rate"],
        }

    def export_dashboard_chart(self, metric: str) -> Dict[str, object]:
        return {"metric": metric, "format": "csv", "rows": 3}

    def export_daily_report(self) -> Dict[str, object]:
        return {"format": "markdown", "sections": ["summary", "top_questions", "feedback"]}

    def create_from_template(self, template_id: str, name: str, owner: str) -> ManagedApplication:
        template = self.templates.get(template_id)
        if template is None:
            raise ValueError("unknown application template")
        app = ManagedApplication(
            id=self._next_id("app"),
            name=name,
            application_type=template.application_type,
            owner=owner,
            template_id=template_id,
        )
        self.applications[app.id] = app
        return app

    def copy_application(self, application_id: str, name: str) -> ManagedApplication:
        source = self._application(application_id)
        copied = ManagedApplication(
            id=self._next_id("app"),
            name=name,
            application_type=source.application_type,
            owner=source.owner,
            template_id=source.template_id,
            version=source.version,
            published_versions=list(source.published_versions),
            current_version=source.current_version,
            embed_config=dict(source.embed_config),
            share_permissions=dict(source.share_permissions),
        )
        self.applications[copied.id] = copied
        return copied

    def publish_application(self, application_id: str) -> ManagedApplication:
        app = self._application(application_id)
        app.version += 1
        app.current_version = app.version
        app.published_versions.append(app.version)
        return app

    def rollback_application(self, application_id: str, version: int) -> ManagedApplication:
        app = self._application(application_id)
        if version not in app.published_versions:
            raise ValueError("version is not published")
        app.current_version = version
        return app

    def record_application_access(self, application_id: str, count: int = 1) -> int:
        app = self._application(application_id)
        app.access_count += count
        return app.access_count

    def configure_embed(self, application_id: str, domains: Sequence[str], theme: str) -> Dict[str, object]:
        app = self._application(application_id)
        app.embed_config = {"domains": list(domains), "theme": theme}
        return app.embed_config

    def configure_share_link(self, application_id: str, mode: str, expires_days: int) -> Dict[str, object]:
        if mode not in {"private", "workspace", "public"}:
            raise ValueError("unsupported share mode")
        app = self._application(application_id)
        app.share_permissions = {"mode": mode, "expires_days": expires_days}
        return app.share_permissions

    def workflow_node_catalog(self) -> List[Dict[str, object]]:
        return [
            {
                "type": case.node_type,
                "title": case.title,
                "inputs": case.inputs,
                "outputs": case.outputs,
            }
            for case in self.node_cases
        ]

    def search_nodes(self, query: str) -> List[Dict[str, object]]:
        return [
            node
            for node in self.workflow_node_catalog()
            if query.lower() in node["title"].lower() or query.lower() in node["type"].lower()
        ]

    def snap_node_position(self, x: int, y: int, grid: int = 24) -> Dict[str, int]:
        return {"x": round(x / grid) * grid, "y": round(y / grid) * grid}

    def loop_boundary_hint(self, max_iterations: int) -> str:
        if max_iterations <= 0:
            raise ValueError("max_iterations must be positive")
        return f"Loop stops after {max_iterations} iterations or an explicit break."

    def preview_node_io(self, node_type: str) -> Dict[str, List[str]]:
        case = self._node_case(node_type)
        return {"inputs": case.inputs, "outputs": case.outputs}

    def debug_single_node(self, node_type: str, payload: Dict[str, object]) -> Dict[str, object]:
        case = self._node_case(node_type)
        missing = [key for key in case.inputs if key not in payload]
        if missing:
            return {"status": "failed", "missing": missing}
        return {"status": "success", "node_type": node_type, "outputs": case.outputs}

    def node_acceptance_summary(self) -> Dict[str, object]:
        return {
            "total": len(self.node_cases),
            "passed": len([case for case in self.node_cases if case.status == "passed"]),
            "types": [case.node_type for case in self.node_cases],
        }

    def _feedback(self, feedback_id: str) -> FeedbackTicket:
        try:
            return self.feedback[feedback_id]
        except KeyError as exc:
            raise KeyError(feedback_id) from exc

    def _application(self, application_id: str) -> ManagedApplication:
        try:
            return self.applications[application_id]
        except KeyError as exc:
            raise KeyError(application_id) from exc

    def _node_case(self, node_type: str) -> NodeAcceptanceCase:
        for case in self.node_cases:
            if case.node_type == node_type:
                return case
        raise ValueError(f"unknown node type: {node_type}")

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}-{self._counter}"

    @staticmethod
    def _count_by(values: Iterable[str]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        return counts
