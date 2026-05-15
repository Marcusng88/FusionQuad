"""Planner node backed by a Deep Agent with BESS strategy skills."""

from __future__ import annotations

import json
import os
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.tools import tool

from app.agents.planner import STRATEGIES_DIR, get_forecast_context, read_guideline_file, search_guidelines
from app.agents.state import AgentState

_DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

_PLANNER_PROMPT = """You are the Planner Agent for FusionQuad — an AI-powered BESS peak shaving system.
Your role: Given the current forecast, tariff window, day type, and BESS state,
select the appropriate dispatch strategy from the guidelines.

Task:
1. Search guidelines for strategy matching tariff_window + day_type
2. Read the most relevant guideline
3. Apply strategy rules given current BESS state and forecast
4. Output optimization_strategy dict

Output format:
{
  "strategy_name": "...",
  "targets": {"shave_kw": ..., "reserve_soc_pct": ...},
  "constraints": [...],
  "rationale": "...",
  "md_limit_kw": ...,
  "confidence": ...
}
"""


@tool
def search_guidelines_tool(query: str) -> list[dict[str, Any]]:
    """Search strategy files for matching guidelines.

    Args:
        query: Keywords such as tariff window, day type, and forecast profile.
    """
    return search_guidelines(query)


@tool
def read_guideline_file_tool(path: str) -> str:
    """Read a specific guideline file by name or path.

    Args:
        path: Strategy file name (e.g., "aggressive_peak_shaving.md").
    """
    return read_guideline_file(path)


@tool
def get_forecast_context_tool(state: dict[str, Any]) -> str:
    """Build a formatted forecast context string from agent state."""
    return get_forecast_context(state)


def _deep_agent_enabled(state: AgentState) -> bool:
    if state.get("use_deep_agent") is True:
        return True
    flag = os.getenv("DEEPAGENTS_ENABLED", "").strip().lower()
    return flag in {"1", "true", "yes", "on"}


def _build_planner_agent() -> Any:
    model = os.getenv("DEEPAGENTS_MODEL", _DEFAULT_MODEL)
    backend_root = STRATEGIES_DIR.parent
    return create_deep_agent(
        name="planner-agent",
        model=model,
        system_prompt=_PLANNER_PROMPT,
        tools=[search_guidelines_tool, read_guideline_file_tool, get_forecast_context_tool],
        backend=FilesystemBackend(root_dir=str(backend_root), virtual_mode=True),
        skills=[str(STRATEGIES_DIR)],
    )


_PLANNER_AGENT: Any | None = None


def _get_planner_agent() -> Any:
    global _PLANNER_AGENT
    if _PLANNER_AGENT is None:
        _PLANNER_AGENT = _build_planner_agent()
    return _PLANNER_AGENT


def _parse_strategy_payload(payload: Any) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        return payload
    if not isinstance(payload, str):
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        pass

    start = payload.find("{")
    end = payload.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(payload[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def _fallback_strategy(state: AgentState) -> dict[str, Any]:
    confidence = 0.5
    forecast_conf = state.get("forecast_confidence") or {}
    if forecast_conf:
        confidence = sum(forecast_conf.values()) / max(1, len(forecast_conf))
    return {
        "strategy_name": "conservative_shaving",
        "targets": {"shave_kw": 50.0, "reserve_soc_pct": 0.30},
        "constraints": ["max_100kW_interval"],
        "rationale": "Fallback strategy used due to missing or invalid planner output.",
        "md_limit_kw": state.get("md_limit_kw", 800.0),
        "confidence": confidence,
    }


def planner_node(state: AgentState) -> dict:
    """Planner node that selects an optimization strategy.

    Uses a Deep Agent when enabled; otherwise returns a safe fallback.
    """
    if not _deep_agent_enabled(state):
        return {"optimization_strategy": _fallback_strategy(state)}

    context = get_forecast_context(state)
    guidelines = search_guidelines(f"{state.get('tariff_window', '')} {state.get('day_type', '')}")
    guidelines_text = "\n\n".join(
        f"=== {item['source']} ===\n{item['content']}" for item in guidelines
    )

    prompt = (
        "Based on the following state and guidelines, select the optimal BESS strategy.\n\n"
        f"STATE:\n{context}\n\nGUIDELINES:\n{guidelines_text}\n\n"
        "Respond with optimization_strategy JSON only."
    )

    try:
        agent = _get_planner_agent()
        result = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"configurable": {"thread_id": "planner"}},
        )
        messages = result.get("messages", []) if isinstance(result, dict) else []
        last = messages[-1].content if messages else ""
        strategy = _parse_strategy_payload(last) or _fallback_strategy(state)
    except Exception:
        strategy = _fallback_strategy(state)

    strategy.setdefault("md_limit_kw", state.get("md_limit_kw", 800.0))
    return {"optimization_strategy": strategy}
