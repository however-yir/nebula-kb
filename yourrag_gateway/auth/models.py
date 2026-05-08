"""Auth domain models (from P2)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AuthContext:
    actor_id: str
    actor_name: str
    actor_type: str
    roles: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    auth_type: str = "unknown"
    api_key_id: str = ""

    @property
    def is_admin(self) -> bool:
        return "admin:full" in self.permissions or "admin" in self.roles


SYSTEM_CONTEXT = AuthContext(
    actor_id="system",
    actor_name="system",
    actor_type="system",
    roles=["admin"],
    permissions=["admin:full"],
    auth_type="system",
)
