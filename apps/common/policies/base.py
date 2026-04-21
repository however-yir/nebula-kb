# coding=utf-8
"""Base policy primitives for domain access checks."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str = ""


class BasePolicy:
    """Marker base class for policy objects."""

    def allow(self) -> PolicyDecision:
        return PolicyDecision(True)

