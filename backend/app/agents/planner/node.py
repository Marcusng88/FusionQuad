"""Planner node backed by a Deep Agent with BESS strategy skills."""

from __future__ import annotations

import json
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from deepagents.backends.state import StateBackend
from deepagents.backends.composite import CompositeBackend
from langchain.tools import tool

from app.agents.planner import STRATEGIES_DIR, EXPERIENCE_DIR, get_forecast_context, search_guidelines
from app.agents.state import AgentState, OptimizationStrategy
from app.core.model_selection import resolve_deepagents_model

_DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

_PLANNER_PROMPT = """You are the Planner Agent for FusionQuad — an AI-powered BESS peak shaving system.
Your role: Given the current forecast, tariff window, day type, and BESS state,
select the appropriate dispatch strategy from the guidelines.

Task:
1. Use read_file to search /strategies/ and /experience/ for matching guidelines
2. Read the most relevant guideline
3. Apply strategy rules given current BESS state and forecast
4. Output optimization_strategy dict

Output format:
{
  "strategy_name": "...",
  "shave_kw": ...,
  "reserve_soc_pct": ...,
  "target_soc_end": ...,
  "rationale": "...",
  "md_limit_kw": ...,
  "confidence": ...,
  "constraints": [...]
}
"""

@tool
def get_forecast_context_tool(state: dict[str, Any]) -> str:
    """Build a formatted forecast context string from agent state."""
    return get_forecast_context(state)


def _build_planner_backend() -> CompositeBackend:
    """Build a CompositeBackend scoped to /experience/ and /strategies/ only."""
    return CompositeBackend(
        default=StateBackend(),
        routes={
            "/experience/": FilesystemBackend(root_dir=str(EXPERIENCE_DIR), virtual_mode=True),
            "/strategies/": FilesystemBackend(root_dir=str(STRATEGIES_DIR), virtual_mode=True),
        },
    )


_PLANNER_AGENT: Any | None = None


def _get_planner_agent() -> Any:
    global _PLANNER_AGENT
    if _PLANNER_AGENT is None:
        model = resolve_deepagents_model(_DEFAULT_MODEL)
        _PLANNER_AGENT = create_deep_agent(
            name="planner-agent",
            model=model,
            system_prompt=_PLANNER_PROMPT,
            tools=[get_forecast_context_tool],
            backend=_build_planner_backend(),
        )
    return _PLANNER_AGENT


def _parse_strategy_payload(payload: Any) -> OptimizationStrategy | None:
    parsed: dict | None = None
    if isinstance(payload, dict):
        parsed = payload
    elif isinstance(payload, str):
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            start = payload.find("{")
            end = payload.rfind("}")
            if start >= 0 and end > start:
                try:
                    parsed = json.loads(payload[start : end + 1])
                except json.JSONDecodeError:
                    pass

    if parsed is None:
        return None

    return OptimizationStrategy(
        strategy_name=str(parsed.get("strategy_name", "")),
        shave_kw=float(parsed.get("shave_kw", 50.0)),
        reserve_soc_pct=float(parsed.get("reserve_soc_pct", 0.20)),
        target_soc_end=float(parsed.get("target_soc_end", 0.50)),
        rationale=str(parsed.get("rationale", "")),
        confidence=float(parsed.get("confidence", 0.5)),
        md_limit_kw=float(parsed.get("md_limit_kw", 800.0)),
        constraints=list(parsed.get("constraints") or []),
    )


def _fallback_strategy(state: AgentState) -> OptimizationStrategy:
    confidence = 0.5
    forecast = state.get("forecast") or {}
    forecast_conf = forecast.get("confidence") or {}
    if forecast_conf:
        confidence = sum(forecast_conf.values()) / max(1, len(forecast_conf))
    return OptimizationStrategy(
        strategy_name="conservative_shaving",
        shave_kw=50.0,
        reserve_soc_pct=0.30,
        target_soc_end=0.50,
        rationale="Fallback strategy used due to missing or invalid planner output.",
        confidence=confidence,
        md_limit_kw=float(state.get("md_limit_kw") or 800.0),
        constraints=["max_100kW_interval"],
    )


def planner_node(state: AgentState) -> dict:
    context = get_forecast_context(state)
    tariff = state.get("tariff") or {}
    guidelines = search_guidelines(f"{tariff.get('window', '')} {state.get('day_type', '')}")
    guidelines_text = chr(10).join(
        f"=== {item['source']} ===" + chr(10) + item['content'] for item in guidelines
    )

    prompt = (
        "Based on the following state and guidelines, select the optimal BESS strategy." + chr(10) + chr(10) +
        f"STATE:" + chr(10) + context + chr(10) + chr(10) + "GUIDELINES:" + chr(10) + guidelines_text + chr(10) + chr(10) +
        "You have access to /strategies/ and /experience/ via the filesystem backend." + chr(10) +
        "Use read_file to read strategy files as needed, then respond with optimization_strategy JSON only."
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

    if not strategy.get("md_limit_kw"):
        strategy = OptimizationStrategy(**{**strategy, "md_limit_kw": float(state.get("md_limit_kw") or 800.0)})

    return {"optimization_strategy": strategy}
