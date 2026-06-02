from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional


@dataclass
class AdvancedModel:
    id: str
    name: str
    model_type: str
    preset: Dict[str, object] = field(default_factory=dict)
    fallback_to: Optional[str] = None
    cost_usd: float = 0.0


@dataclass
class ManagedTool:
    id: str
    name: str
    category: str
    timeout_ms: int
    retry_limit: int
    market_description: str
    logs: List[Dict[str, object]] = field(default_factory=list)


@dataclass
class ManagedTrigger:
    id: str
    name: str
    trigger_type: str
    params: Dict[str, object]
    enabled: bool = False
    records: List[Dict[str, object]] = field(default_factory=list)


@dataclass
class ManagedUser:
    id: str
    email: str
    group: str
    role_template: str
    active: bool = True


@dataclass
class SSOConfig:
    provider: str
    callback_url: str
    enabled: bool
    mapping_rule: str
    last_test_status: str = "untested"
    error_log: List[str] = field(default_factory=list)


class PlatformAdvancedCompletion:
    """Acceptance model for platform P1/P2 governance completion."""

    def __init__(self) -> None:
        self._counter = 0
        self.models: Dict[str, AdvancedModel] = {}
        self.tools: Dict[str, ManagedTool] = {}
        self.triggers: Dict[str, ManagedTrigger] = {}
        self.users: Dict[str, ManagedUser] = {}
        self.sso: Dict[str, SSOConfig] = {}
        self.audit_events: List[Dict[str, object]] = []
        self.login_logs: List[Dict[str, object]] = []

    def register_model(self, name: str, model_type: str) -> AdvancedModel:
        if model_type not in {"reranker", "voice", "image", "llm"}:
            raise ValueError("unsupported model type")
        model = AdvancedModel(id=self._next_id("model"), name=name, model_type=model_type)
        self.models[model.id] = model
        self._audit("model.registered", model.id, {"model_type": model_type})
        return model

    def test_model(self, model_id: str) -> Dict[str, object]:
        model = self._model(model_id)
        payload = {
            "reranker": {"status": "ok", "score": 0.97},
            "voice": {"status": "ok", "sample_rate": 16000},
            "image": {"status": "ok", "width": 512, "height": 512},
            "llm": {"status": "ok", "tokens": 12},
        }[model.model_type]
        self._audit("model.tested", model.id, payload)
        return payload

    def set_model_preset(self, model_id: str, preset: Dict[str, object]) -> Dict[str, object]:
        model = self._model(model_id)
        model.preset = dict(preset)
        self._audit("model.preset.updated", model.id, model.preset)
        return model.preset

    def configure_model_fallback(self, model_id: str, fallback_model_id: str) -> Dict[str, str]:
        model = self._model(model_id)
        self._model(fallback_model_id)
        model.fallback_to = fallback_model_id
        return {"primary": model_id, "fallback": fallback_model_id, "status": "configured"}

    def record_model_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> Dict[str, object]:
        model = self._model(model_id)
        model.cost_usd += round((input_tokens + output_tokens) * 0.000002, 6)
        return {"model_id": model_id, "cost_usd": model.cost_usd}

    def create_tool(
        self,
        name: str,
        category: str,
        timeout_ms: int,
        retry_limit: int,
        market_description: str,
    ) -> ManagedTool:
        tool = ManagedTool(
            id=self._next_id("tool"),
            name=name,
            category=category,
            timeout_ms=timeout_ms,
            retry_limit=retry_limit,
            market_description=market_description,
        )
        self.tools[tool.id] = tool
        self._audit("tool.created", tool.id, {"category": category})
        return tool

    def execute_tool(self, tool_id: str, params: Dict[str, object], fail_once: bool = False) -> Dict[str, object]:
        tool = self._tool(tool_id)
        attempts = 1 + (1 if fail_once and tool.retry_limit > 0 else 0)
        status = "success" if attempts <= tool.retry_limit + 1 else "failed"
        record = {
            "params": params,
            "attempts": attempts,
            "timeout_ms": tool.timeout_ms,
            "status": status,
        }
        tool.logs.append(record)
        self._audit("tool.executed", tool.id, record)
        return record

    def tool_execution_logs(self, tool_id: str) -> List[Dict[str, object]]:
        return list(self._tool(tool_id).logs)

    def create_trigger(self, name: str, trigger_type: str, params: Dict[str, object]) -> ManagedTrigger:
        if trigger_type not in {"scheduled", "event"}:
            raise ValueError("trigger_type must be scheduled or event")
        trigger = ManagedTrigger(
            id=self._next_id("trigger"),
            name=name,
            trigger_type=trigger_type,
            params=params,
        )
        self.triggers[trigger.id] = trigger
        return trigger

    def set_trigger_enabled(self, trigger_id: str, enabled: bool) -> ManagedTrigger:
        trigger = self._trigger(trigger_id)
        trigger.enabled = enabled
        return trigger

    def preview_trigger_params(self, trigger_id: str) -> Dict[str, object]:
        return dict(self._trigger(trigger_id).params)

    def record_trigger_run(self, trigger_id: str, status: str) -> Dict[str, object]:
        trigger = self._trigger(trigger_id)
        record = {"status": status, "attempt": len(trigger.records) + 1}
        trigger.records.append(record)
        return record

    def retry_trigger_failure(self, trigger_id: str) -> Dict[str, object]:
        trigger = self._trigger(trigger_id)
        if not trigger.records or trigger.records[-1]["status"] != "failed":
            raise ValueError("last trigger record is not failed")
        return self.record_trigger_run(trigger.id, "success")

    def trigger_statistics(self, trigger_id: str) -> Dict[str, int]:
        trigger = self._trigger(trigger_id)
        return {
            "total": len(trigger.records),
            "success": len([record for record in trigger.records if record["status"] == "success"]),
            "failed": len([record for record in trigger.records if record["status"] == "failed"]),
        }

    def bulk_import_users(self, rows: Iterable[Dict[str, str]]) -> List[ManagedUser]:
        users: List[ManagedUser] = []
        for row in rows:
            user = ManagedUser(
                id=self._next_id("user"),
                email=row["email"],
                group=row.get("group", "default"),
                role_template=row.get("role_template", "viewer"),
            )
            self.users[user.id] = user
            users.append(user)
        return users

    def user_groups(self) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = {}
        for user in self.users.values():
            groups.setdefault(user.group, []).append(user.email)
        return groups

    def role_templates(self) -> Dict[str, List[str]]:
        return {
            "admin": ["manage_users", "manage_models", "audit_export"],
            "operator": ["manage_knowledge", "handle_feedback"],
            "viewer": ["view_knowledge"],
        }

    def record_login(self, email: str, status: str, ip_address: str) -> Dict[str, str]:
        record = {"email": email, "status": status, "ip_address": ip_address}
        self.login_logs.append(record)
        return record

    def account_anomaly_hint(self, email: str) -> str:
        failures = [log for log in self.login_logs if log["email"] == email and log["status"] == "failed"]
        return "account requires review" if len(failures) >= 2 else "normal"

    def configure_sso(self, provider: str, callback_url: str, mapping_rule: str, enabled: bool) -> SSOConfig:
        if provider not in {"oidc", "saml", "ldap", "cas"}:
            raise ValueError("unsupported sso provider")
        config = SSOConfig(provider, callback_url, enabled, mapping_rule)
        self.sso[provider] = config
        return config

    def test_sso(self, provider: str) -> Dict[str, str]:
        config = self._sso(provider)
        config.last_test_status = "ok"
        return {"provider": provider, "status": "ok"}

    def copy_callback_url(self, provider: str) -> str:
        return self._sso(provider).callback_url

    def set_sso_enabled(self, provider: str, enabled: bool) -> bool:
        config = self._sso(provider)
        config.enabled = enabled
        return config.enabled

    def default_login_method(self, provider: str) -> str:
        self._sso(provider)
        return provider

    def record_sso_error(self, provider: str, message: str) -> List[str]:
        config = self._sso(provider)
        config.error_log.append(message)
        return config.error_log

    def user_mapping_rule(self, provider: str) -> str:
        return self._sso(provider).mapping_rule

    def filter_audit(self, event_name: str) -> List[Dict[str, object]]:
        return [event for event in self.audit_events if event["event_name"] == event_name]

    def export_audit(self) -> Dict[str, object]:
        return {"format": "jsonl", "count": len(self.audit_events)}

    def api_guidance(self) -> Dict[str, object]:
        return {
            "rate_limits": {"anon": "60/min", "user": "300/min", "knowledge_search": "30/min"},
            "curl_examples": [
                "curl -H 'Authorization: Bearer <token>' https://nebulakb.example.com/api/v1/knowledge-bases",
            ],
            "frontend_example": "fetch('/api/v1/knowledge-bases', {headers: {Authorization: `Bearer ${token}`}})",
            "compatibility": "v1 keeps envelope, pagination, and error-code semantics stable.",
        }

    def _audit(self, event_name: str, resource_id: str, payload: Dict[str, object]) -> None:
        self.audit_events.append(
            {"event_name": event_name, "resource_id": resource_id, "payload": payload}
        )

    def _model(self, model_id: str) -> AdvancedModel:
        try:
            return self.models[model_id]
        except KeyError as exc:
            raise KeyError(model_id) from exc

    def _tool(self, tool_id: str) -> ManagedTool:
        try:
            return self.tools[tool_id]
        except KeyError as exc:
            raise KeyError(tool_id) from exc

    def _trigger(self, trigger_id: str) -> ManagedTrigger:
        try:
            return self.triggers[trigger_id]
        except KeyError as exc:
            raise KeyError(trigger_id) from exc

    def _sso(self, provider: str) -> SSOConfig:
        try:
            return self.sso[provider]
        except KeyError as exc:
            raise KeyError(provider) from exc

    def _next_id(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}-{self._counter}"
