from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


SENSITIVE_KEYS = {"password", "token", "api_key", "secret", "client_secret"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def redact_payload(payload: object) -> object:
    if isinstance(payload, dict):
        return {
            key: ("********" if any(marker in key.lower() for marker in SENSITIVE_KEYS) else redact_payload(value))
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    return payload


@dataclass
class ModelProviderRecord:
    id: str
    name: str
    endpoint: str
    credential: dict[str, str]
    connected: bool = False


@dataclass
class ModelRecord:
    id: str
    provider_id: str
    name: str
    model_type: str
    is_default: bool = False


@dataclass
class ToolRecord:
    id: str
    name: str
    input_schema: dict[str, str]
    output_schema: dict[str, str]
    allowed_roles: set[str] = field(default_factory=set)


@dataclass
class TriggerRecord:
    id: str
    name: str
    target_resource_id: str
    allowed_roles: set[str]
    enabled: bool = False
    run_count: int = 0


@dataclass
class UserRecord:
    id: str
    email: str
    role: str
    workspace_id: str
    is_active: bool = True


@dataclass
class SsoConfig:
    provider: str
    client_id: str
    callback_url: str
    enabled: bool


@dataclass
class AuditEvent:
    event_name: str
    actor_id: str
    resource_type: str
    resource_id: str
    payload: dict[str, object]
    created_at: datetime = field(default_factory=_now)


class PlatformGovernanceDemo:
    """In-memory acceptance model for platform governance contracts."""

    def __init__(self) -> None:
        self.model_providers: dict[str, ModelProviderRecord] = {}
        self.models: dict[str, ModelRecord] = {}
        self.tools: dict[str, ToolRecord] = {}
        self.triggers: dict[str, TriggerRecord] = {}
        self.users: dict[str, UserRecord] = {}
        self.resource_grants: dict[tuple[str, str], set[str]] = {}
        self.sso_configs: dict[str, SsoConfig] = {}
        self.audit_events: list[AuditEvent] = []

    def onboard_model_provider(self, name: str, endpoint: str, credential: dict[str, str]) -> ModelProviderRecord:
        provider = ModelProviderRecord(
            id=f"provider-{uuid4().hex[:8]}",
            name=name,
            endpoint=endpoint,
            credential=credential,
        )
        self.model_providers[provider.id] = provider
        self.record_audit("model_provider.created", "system", "model_provider", provider.id, credential)
        return provider

    def test_model_connection(self, provider_id: str) -> dict[str, object]:
        provider = self.model_providers[provider_id]
        provider.connected = provider.endpoint.startswith("http") and bool(provider.credential.get("api_key"))
        return {"provider_id": provider.id, "status": "ok" if provider.connected else "error"}

    def add_model(self, provider_id: str, name: str, model_type: str) -> ModelRecord:
        if model_type not in {"llm", "embedding"}:
            raise ValueError("model_type must be llm or embedding")
        model = ModelRecord(
            id=f"model-{uuid4().hex[:8]}",
            provider_id=provider_id,
            name=name,
            model_type=model_type,
        )
        self.models[model.id] = model
        self.record_audit("model.created", "system", "model", model.id, {"name": name, "type": model_type})
        return model

    def test_embedding_model(self, model_id: str, text: str) -> dict[str, object]:
        model = self.models[model_id]
        if model.model_type != "embedding":
            raise ValueError("model is not an embedding model")
        vector = [round((ord(char) % 31) / 31, 4) for char in text[:8]]
        return {"model_id": model.id, "status": "ok", "dimension": len(vector), "sample": vector}

    def set_default_model(self, model_id: str) -> ModelRecord:
        model = self.models[model_id]
        for candidate in self.models.values():
            if candidate.model_type == model.model_type:
                candidate.is_default = False
        model.is_default = True
        self.record_audit("model.default_changed", "system", "model", model.id, {"is_default": True})
        return model

    def create_tool(
        self,
        name: str,
        input_schema: dict[str, str],
        output_schema: dict[str, str],
        allowed_roles: set[str],
    ) -> ToolRecord:
        tool = ToolRecord(
            id=f"tool-{uuid4().hex[:8]}",
            name=name,
            input_schema=input_schema,
            output_schema=output_schema,
            allowed_roles=allowed_roles,
        )
        self.tools[tool.id] = tool
        self.record_audit("tool.created", "system", "tool", tool.id, {"name": name})
        return tool

    def debug_tool(self, user: UserRecord, tool_id: str, params: dict[str, object]) -> dict[str, object]:
        tool = self.tools[tool_id]
        self._require_active_user(user)
        if user.role not in tool.allowed_roles:
            raise PermissionError("user role cannot execute this tool")
        self._validate_schema("input", tool.input_schema, params)
        output = {"result": f"{tool.name}: {params.get('query', '')}"}
        self._validate_schema("output", tool.output_schema, output)
        self.record_audit("tool.debugged", user.id, "tool", tool.id, {"params": params, "output": output})
        return {"status": "success", "output": output}

    def create_trigger(
        self,
        name: str,
        target_resource_id: str,
        allowed_roles: set[str],
    ) -> TriggerRecord:
        trigger = TriggerRecord(
            id=f"trigger-{uuid4().hex[:8]}",
            name=name,
            target_resource_id=target_resource_id,
            allowed_roles=allowed_roles,
        )
        self.triggers[trigger.id] = trigger
        self.record_audit("trigger.created", "system", "trigger", trigger.id, {"target_resource_id": target_resource_id})
        return trigger

    def set_trigger_enabled(self, trigger_id: str, enabled: bool, actor: UserRecord) -> TriggerRecord:
        trigger = self.triggers[trigger_id]
        self._require_trigger_permission(trigger, actor)
        trigger.enabled = enabled
        self.record_audit("trigger.enabled_changed", actor.id, "trigger", trigger.id, {"enabled": enabled})
        return trigger

    def run_trigger(self, trigger_id: str, actor: UserRecord) -> dict[str, object]:
        trigger = self.triggers[trigger_id]
        self._require_trigger_permission(trigger, actor)
        if trigger.target_resource_id not in self.tools and trigger.target_resource_id not in self.models:
            raise ValueError("trigger target resource does not exist")
        if not trigger.enabled:
            raise ValueError("trigger is disabled")
        trigger.run_count += 1
        self.record_audit("trigger.ran", actor.id, "trigger", trigger.id, {"run_count": trigger.run_count})
        return {"status": "success", "run_count": trigger.run_count}

    def create_user(self, email: str, role: str, workspace_id: str) -> UserRecord:
        user = UserRecord(
            id=f"user-{uuid4().hex[:8]}",
            email=email,
            role=role,
            workspace_id=workspace_id,
        )
        self.users[user.id] = user
        self.record_audit("user.login", user.id, "user", user.id, {"email": email})
        return user

    def disable_user(self, user_id: str, actor_id: str) -> UserRecord:
        user = self.users[user_id]
        user.is_active = False
        self.record_audit("user.disabled", actor_id, "user", user.id, {"email": user.email})
        return user

    def permission_matrix(self) -> dict[str, list[str]]:
        return {
            "model": ["view", "test", "set_default"],
            "tool": ["view", "debug", "grant"],
            "trigger": ["view", "enable", "run"],
            "audit": ["view"],
        }

    def authorize_resource(self, user_id: str, resource_id: str, actions: set[str], actor_id: str) -> None:
        self.resource_grants[(user_id, resource_id)] = actions
        self.record_audit(
            "permission.changed",
            actor_id,
            "resource_permission",
            resource_id,
            {"user_id": user_id, "actions": sorted(actions)},
        )

    def ensure_workspace_access(self, user: UserRecord, workspace_id: str) -> None:
        self._require_active_user(user)
        if user.workspace_id != workspace_id:
            raise PermissionError("workspace isolation blocked access")

    def configure_sso(self, provider: str, client_id: str, callback_url: str, enabled: bool) -> SsoConfig:
        if provider not in {"oidc", "saml"}:
            raise ValueError("provider must be oidc or saml")
        if not callback_url.startswith("https://"):
            raise ValueError("callback_url must be https")
        config = SsoConfig(provider=provider, client_id=client_id, callback_url=callback_url, enabled=enabled)
        self.sso_configs[provider] = config
        self.record_audit(
            "sso.configured",
            "system",
            "sso",
            provider,
            {"client_id": client_id, "client_secret": "secret", "enabled": enabled},
        )
        return config

    def record_audit(
        self,
        event_name: str,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        payload: dict[str, object],
    ) -> AuditEvent:
        event = AuditEvent(
            event_name=event_name,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=redact_payload(payload),
        )
        self.audit_events.append(event)
        return event

    def audit_summary(self) -> list[dict[str, object]]:
        return [
            {
                "event_name": event.event_name,
                "actor_id": event.actor_id,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "payload": event.payload,
            }
            for event in self.audit_events
        ]

    def _validate_schema(self, schema_name: str, schema: dict[str, str], payload: dict[str, object]) -> None:
        for field_name, field_type in schema.items():
            if field_name not in payload:
                raise ValueError(f"{schema_name} schema missing field: {field_name}")
            if field_type == "string" and not isinstance(payload[field_name], str):
                raise ValueError(f"{schema_name} schema field must be string: {field_name}")

    def _require_active_user(self, user: UserRecord) -> None:
        if not user.is_active:
            raise PermissionError("disabled user cannot access resources")

    def _require_trigger_permission(self, trigger: TriggerRecord, actor: UserRecord) -> None:
        self._require_active_user(actor)
        if actor.role not in trigger.allowed_roles:
            raise PermissionError("user role cannot operate this trigger")
