"""Shared harness middleware for DeepAgent nodes.

OutputFormatGuardMiddleware — after_model hook that logs a warning
when the agent's response is missing expected keywords, giving the agent
a chance to self-correct on the next iteration.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware

logger = logging.getLogger(__name__)


class OutputFormatGuardMiddleware(AgentMiddleware):
    """Verify required keywords are present in model output after each LLM call.

    Non-blocking: logs a warning but does not retry or raise.
    Attach to Planner and Auditor (not Controller — it keeps structured output).
    """

    tools: list = []

    def __init__(self, required_fields: list[str], agent_name: str = "agent") -> None:
        self._required_fields = required_fields
        self._agent_name = agent_name

    def after_model(self, state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
        messages = state.get("messages", [])
        if not messages:
            return None
        last = messages[-1]
        content = last.content if hasattr(last, "content") else str(last)
        if not isinstance(content, str):
            return None
        missing = [f for f in self._required_fields if f.lower() not in content.lower()]
        if missing:
            logger.warning(
                "%s | response missing expected fields %s — agent may self-correct",
                self._agent_name,
                missing,
            )
        return None
