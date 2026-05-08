"""Tool executor with circuit breaker pattern (from P1).

This is a generic, reusable tool executor that wraps P3's 20+ agent/tools
with resilience patterns: retry, timeout, circuit breaker, fallback.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable

from yourrag_gateway.core.settings import YourRAGSettings

logger = logging.getLogger(__name__)


@dataclass
class CircuitState:
    failures: int = 0
    opened_at: float | None = None


class ToolExecutor:
    """Execute tool calls with retry, timeout, and circuit breaker."""

    def __init__(self, settings: YourRAGSettings | None = None) -> None:
        self._settings = settings or YourRAGSettings()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="yourrag-tool-exec")
        self._states: dict[str, CircuitState] = {}
        self._lock = Lock()
        self._registry: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, fn: Callable[..., Any]) -> None:
        """Register a tool function by name."""
        self._registry[name] = fn

    def execute(self, tool_name: str, action_input: dict[str, Any]) -> Any:
        if self._is_circuit_open(tool_name):
            return self._fallback(tool_name, "circuit_open")
        try:
            result = self._execute_with_retry(tool_name, action_input)
            self._reset_state(tool_name)
            return result
        except Exception as exc:
            self._mark_failure(tool_name)
            logger.warning("Tool %s execution degraded: %s", tool_name, exc)
            return self._fallback(tool_name, str(exc))

    def _execute_with_retry(self, tool_name: str, action_input: dict[str, Any]) -> Any:
        fn = self._registry.get(tool_name)
        if fn is None:
            raise ValueError(f"Unknown tool: {tool_name}")

        last_exc: Exception | None = None
        for attempt in range(self._settings.tool_retry_attempts + 1):
            if attempt > 0:
                time.sleep(self._settings.tool_retry_backoff_seconds)
            future = self._executor.submit(fn, **action_input)
            try:
                return future.result(timeout=self._settings.tool_timeout_seconds)
            except FuturesTimeoutError as exc:
                last_exc = exc
            except Exception as exc:
                last_exc = exc
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Unexpected retry loop exit")  # pragma: no cover

    def _state(self, tool_name: str) -> CircuitState:
        with self._lock:
            if tool_name not in self._states:
                self._states[tool_name] = CircuitState()
            return self._states[tool_name]

    def _is_circuit_open(self, tool_name: str) -> bool:
        state = self._state(tool_name)
        if state.opened_at is None:
            return False
        if time.time() - state.opened_at >= self._settings.tool_circuit_breaker_cooldown_seconds:
            self._reset_state(tool_name)
            return False
        return True

    def _mark_failure(self, tool_name: str) -> None:
        state = self._state(tool_name)
        state.failures += 1
        if state.failures >= self._settings.tool_circuit_breaker_threshold:
            state.opened_at = time.time()

    def _reset_state(self, tool_name: str) -> None:
        state = self._state(tool_name)
        state.failures = 0
        state.opened_at = None

    def _fallback(self, tool_name: str, reason: str) -> dict[str, Any]:
        return {
            "status": "degraded",
            "tool": tool_name,
            "reason": reason,
            "message": "Tool execution downgraded, please retry or handoff to human operator.",
        }


# Global singleton
_tool_executor: ToolExecutor | None = None


def get_tool_executor(settings: YourRAGSettings | None = None) -> ToolExecutor:
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor(settings)
    return _tool_executor
