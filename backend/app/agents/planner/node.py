"""Planner node backed by a Deep Agent with BESS strategy skills."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from deepagents.backends.state import StateBackend
from deepagents.backends.composite import CompositeBackend
import logging

from app.agents.planner import STRATEGIES_DIR, EXPERIENCE_DIR, get_forecast_context, search_guidelines
from app.agents.shared_middleware import OutputFormatGuardMiddleware
from app.agents.state import AgentState, OptimizationStrategy
from app.core.model_selection import resolve_deepagents_model

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

_PLANNER_PROMPT = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")


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


def _build_planner_tools() -> list:
    tools: list = []
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if tavily_key:
        try:
            from langchain_tavily import TavilySearch
            tools.append(TavilySearch(max_results=3, api_key=tavily_key))
            logger.info("planner | Tavily search tool enabled")
        except ImportError:
            logger.warning("planner | langchain-community not installed, Tavily search unavailable")
    else:
        logger.debug("planner | TAVILY_API_KEY not set, search tool disabled")
    return tools


def _get_planner_agent() -> Any:
    global _PLANNER_AGENT
    if _PLANNER_AGENT is None:
        model = resolve_deepagents_model(_DEFAULT_MODEL)
        tools = _build_planner_tools()
        logger.info("planner | initializing agent model=%s tools=%d", model, len(tools))
        _PLANNER_AGENT = create_deep_agent(
            name="planner-agent",
            model=model,
            system_prompt=_PLANNER_PROMPT,
            tools=tools,
            backend=_build_planner_backend(),
            middleware=[OutputFormatGuardMiddleware(
                required_fields=["strategy", "shave"],
                agent_name="planner",
            )],
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


async def planner_node(state: AgentState) -> dict:
    context = get_forecast_context(state)
    tariff = state.get("tariff") or {}
    guidelines = search_guidelines(f"{tariff.get('window', '')} {state.get('day_type', '')}")
    guidelines_text = chr(10).join(
        f"=== {item['source']} ===" + chr(10) + item['content'] for item in guidelines
    )

    current_time = state.get("current_time")
    if current_time is not None:
        from datetime import datetime as _dt
        if isinstance(current_time, _dt):
            date_header = f"Simulation Date: {current_time.strftime('%Y-%m-%d')} | Time: {current_time.strftime('%H:%M')} | Day: {current_time.strftime('%A')}"
        else:
            date_header = f"Simulation Date: {current_time}"
    else:
        date_header = "Simulation Date: unknown"

    prompt = (
        date_header + chr(10) + chr(10) +
        "Based on the following state and guidelines, select the optimal BESS strategy." + chr(10) + chr(10) +
        f"STATE:" + chr(10) + context + chr(10) + chr(10) + "GUIDELINES:" + chr(10) + guidelines_text + chr(10) + chr(10) +
        "You have access to /strategies/ and /experience/ via the filesystem backend." + chr(10) +
        "Use read_file to read strategy files as needed, then respond with the strategy as JSON with fields: " +
        "strategy_name, shave_kw, reserve_soc_pct, target_soc_end, rationale, confidence, md_limit_kw, constraints."
    )

    try:
        agent = _get_planner_agent()
        session_id = state.get("session_id", "default")
        invoke_config = {"configurable": {"thread_id": f"planner-{session_id}"}}
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            invoke_config,
        )
        structured = result.get("structured_response") if isinstance(result, dict) else None
        if isinstance(structured, dict):
            strategy = _parse_strategy_payload(structured) or _fallback_strategy(state)
        else:
            messages = result.get("messages", []) if isinstance(result, dict) else []
            raw_content = messages[-1].content if messages else ""
            # LangChain returns content as list of blocks: [{"type": "text", "text": "..."}]
            if isinstance(raw_content, list):
                raw_content = " ".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in raw_content
                )
            strategy = _parse_strategy_payload(raw_content) or _fallback_strategy(state)
    except Exception as exc:
        logger.warning("planner | agent error, using fallback: %s", exc)
        strategy = _fallback_strategy(state)

    if not strategy.get("md_limit_kw"):
        strategy = OptimizationStrategy(**{**strategy, "md_limit_kw": float(state.get("md_limit_kw") or 800.0)})

    logger.info(
        "planner | strategy=%s shave_kw=%.1f reserve_soc=%.0f%% confidence=%.2f",
        strategy.get("strategy_name", "unknown"),
        strategy.get("shave_kw", 0.0),
        float(strategy.get("reserve_soc_pct", 0.0)) * 100,
        strategy.get("confidence", 0.0),
    )

    return {"optimization_strategy": strategy}
