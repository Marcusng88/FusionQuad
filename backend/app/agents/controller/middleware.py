"""Dispatch validation middleware for the Controller deep agent.

Intercepts mock_inverter_dispatch tool calls and validates:
  - No transient exceptions (retries up to max_retries times)
  - new_soc within [0.0, 1.0]
  - action_taken matches the requested action

On exception: retries up to max_retries times, then returns error ToolMessage.
On validation failure: returns error ToolMessage immediately (deterministic —
  same inputs would produce same bad result; agent must fix its call args).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, ToolCallRequest
from langchain_core.messages import ToolMessage

_DISPATCH_TOOL = "mock_inverter_dispatch"


class DispatchValidationMiddleware(AgentMiddleware):
    """Ensures deterministic, valid BESS dispatch on every mock_inverter_dispatch call."""

    tools: list = []

    def __init__(self, max_retries: int = 2) -> None:
        self._max_retries = max_retries

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Any],
    ) -> ToolMessage | Any:
        tool_call = request.tool_call
        if tool_call.get("name") != _DISPATCH_TOOL:
            return handler(request)

        requested_action: str = (tool_call.get("args") or {}).get("action", "hold")
        tool_call_id: str = tool_call.get("id") or ""

        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                result = handler(request)
                error_msg = _validate(result, requested_action)
                if error_msg is None:
                    return result
                # Deterministic validation failure — return error for agent to fix
                return ToolMessage(
                    content=(
                        f"Dispatch validation failed: {error_msg}. "
                        "Fix dispatch parameters and retry."
                    ),
                    tool_call_id=tool_call_id,
                    status="error",
                )
            except Exception as exc:
                last_exc = exc

        return ToolMessage(
            content=(
                f"mock_inverter_dispatch failed after {self._max_retries + 1} attempts: "
                f"{last_exc}"
            ),
            tool_call_id=tool_call_id,
            status="error",
        )


def _validate(result: Any, requested_action: str) -> str | None:
    """Return error string if result is invalid, else None."""
    if isinstance(result, ToolMessage) and result.status == "error":
        return f"tool returned error: {result.content}"

    content = result.content if isinstance(result, ToolMessage) else result
    if isinstance(content, str):
        try:
            data: dict[str, Any] = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return None
    elif isinstance(content, dict):
        data = content
    else:
        return None

    new_soc = data.get("new_soc")
    if new_soc is not None:
        try:
            soc_f = float(new_soc)
        except (TypeError, ValueError):
            return f"new_soc={new_soc!r} is not numeric"
        if not (0.0 <= soc_f <= 1.0):
            return f"new_soc={soc_f:.4f} out of bounds [0.0, 1.0]"

    action_taken = data.get("action_taken")
    if action_taken is not None and action_taken != requested_action:
        return (
            f"action mismatch: requested={requested_action!r}, "
            f"got action_taken={action_taken!r}"
        )

    return None
