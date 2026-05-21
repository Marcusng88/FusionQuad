"""Auditor Agent — Deep Agent for post-dispatch evaluation.

Performs tool-based evaluations every tick:
1. evaluate_rules_tool — safety checks (non-negotiable)
2. evaluate_delta_tool — numeric scoring (always)

The deep agent uses CompositeBackend with FilesystemBackend scoped to
/experience/ and /strategies/ only — no access to other paths.
At end-of-day, it reads past audit reports and appends a summary.
"""

from datetime import datetime
import logging
from pathlib import Path
import json
from typing import TypedDict

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent / "prompts"

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from deepagents.backends.state import StateBackend
from deepagents.backends.composite import CompositeBackend
from langchain.tools import tool
from langgraph.checkpoint.memory import MemorySaver

from app.agents.auditor.evaluation import (
    DeltaEvaluation,
    LLMEvaluation,
    RuleEvaluation,
    evaluate_delta,
    evaluate_rules,
    should_run_llm,
)
from app.core.model_selection import resolve_deepagents_model

_DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
_EXPERIENCE_DIR = Path(__file__).parent.parent.parent.parent / "experience"
_STRATEGIES_DIR = Path(__file__).parent.parent.parent.parent / "strategies"
_LOGS_DIR = Path(__file__).parent.parent.parent / "logs"

_AUDITOR_PROMPT_TICK = (_PROMPTS_DIR / "tick.md").read_text(encoding="utf-8")
_AUDITOR_PROMPT_EOD = (_PROMPTS_DIR / "end_of_day.md").read_text(encoding="utf-8")


@tool
def evaluate_rules_tool(
    dispatch_result: dict | None,
    battery_soc: float,
    cycle_count: float,
    tariff_window: str,
    dispatch_action: dict | None,
) -> dict:
    """Mode 1 Safety checks — runs FIRST, non-negotiable.

    Args:
        dispatch_result: Result from mock_inverter_dispatch {new_soc, temp_increase_c, action_taken, actual_discharge_kw}
        battery_soc: Current BESS state-of-charge (0-1)
        cycle_count: Accumulated BESS cycle count
        tariff_window: PEAK | OFF_PEAK | WEEKEND
        dispatch_action: Planner's dispatch action {action, discharge_kw, charge_kw, duration_min}
    """
    return evaluate_rules(
        dispatch_result=dispatch_result,
        battery_soc=battery_soc,
        cycle_count=cycle_count,
        tariff_window=tariff_window,
        dispatch_action=dispatch_action,
    )


@tool
def evaluate_delta_tool(
    dispatch_result: dict | None,
    dispatch_action: dict | None,
    baseline_load: float,
    actual_load: float,
    forecast_kw: float,
    tariff_window: str,
    md_limit_kw: float = 800.0,
) -> dict:
    """Mode 2 Numeric scoring — calculate shave metrics and delta score.

    Args:
        dispatch_result: Result from mock_inverter_dispatch
        dispatch_action: Planner's dispatch action
        baseline_load: Grid import before BESS dispatch (kW)
        actual_load: Grid import after BESS dispatch (kW)
        forecast_kw: Forecasted load for this interval (kW)
        tariff_window: PEAK | OFF_PEAK | WEEKEND
        md_limit_kw: Maximum demand limit (default 800)
    """
    return evaluate_delta(
        dispatch_result=dispatch_result,
        dispatch_action=dispatch_action,
        baseline_load=baseline_load,
        actual_load=actual_load,
        forecast_kw=forecast_kw,
        tariff_window=tariff_window,
        md_limit_kw=md_limit_kw,
    )


class AuditorResult(TypedDict):
    """Complete auditor evaluation result for one tick."""
    delta_eval: DeltaEvaluation
    rule_eval: RuleEvaluation
    llm_eval: LLMEvaluation | None
    timestamp: str
    interval: int
    perceive: str
    reason: str
    act: str


_AUDITOR_AGENT_TICK: object | None = None


def _build_tick_backend() -> CompositeBackend:
    """Tick auditor backend — /experience/ and /strategies/ only. No log access."""
    return CompositeBackend(
        default=StateBackend(),
        routes={
            "/experience/": FilesystemBackend(root_dir=str(_EXPERIENCE_DIR), virtual_mode=True),
            "/strategies/": FilesystemBackend(root_dir=str(_STRATEGIES_DIR), virtual_mode=True),
        },
    )


def _build_eod_backend() -> CompositeBackend:
    """EOD auditor backend — adds /logs/ read access for post-finalize audit."""
    return CompositeBackend(
        default=StateBackend(),
        routes={
            "/logs/": FilesystemBackend(root_dir=str(_LOGS_DIR), virtual_mode=True),
            "/experience/": FilesystemBackend(root_dir=str(_EXPERIENCE_DIR), virtual_mode=True),
            "/strategies/": FilesystemBackend(root_dir=str(_STRATEGIES_DIR), virtual_mode=True),
        },
    )


def _get_tick_agent() -> object:
    global _AUDITOR_AGENT_TICK
    if _AUDITOR_AGENT_TICK is None:
        model = resolve_deepagents_model(_DEFAULT_MODEL)
        logger.info("auditor | initializing tick agent model=%s", model)
        _AUDITOR_AGENT_TICK = create_deep_agent(
            name="auditor-agent-tick",
            model=model,
            system_prompt=_AUDITOR_PROMPT_TICK,
            tools=[evaluate_rules_tool, evaluate_delta_tool],
            backend=_build_tick_backend(),
            checkpointer=MemorySaver(),
        )
    return _AUDITOR_AGENT_TICK


def _parse_llm_payload(payload: str) -> dict | None:
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


async def auditor_node(state: dict) -> dict:
    """Main auditor node — delegates tick evaluation to the deep agent."""
    # Read from value objects
    dispatch_result = state.get("dispatch_result")
    dispatch_action = state.get("dispatch_action")
    baseline_load = state.get("baseline_load", 0.0)
    actual_load = state.get("actual_load", 0.0)
    forecast_kw = state.get("forecast_kw", 0.0)
    md_limit_kw = state.get("md_limit_kw", 800.0)
    current_time = state.get("current_time")
    current_interval = state.get("current_interval", 0)

    battery = state.get("battery") or {}
    battery_soc = float(battery.get("soc") or 0.0)
    cycle_count = float(battery.get("cycle_count") or 0.0)

    tariff = state.get("tariff") or {}
    tariff_window = tariff.get("window") or "PEAK"

    timestamp_str = current_time.strftime("%Y-%m-%d %H:%M") if isinstance(current_time, datetime) else str(current_time or "")

    import_kw = actual_load
    perceive = f"Grid import {import_kw:.0f}kW"
    if import_kw > md_limit_kw:
        perceive += f" - exceeds {md_limit_kw:.0f}kW MD limit by {import_kw - md_limit_kw:.0f}kW"
    else:
        perceive += f" - within {md_limit_kw:.0f}kW MD limit"

    reason = f"BESS SoC at {battery_soc:.0%}"
    if dispatch_action:
        action = dispatch_action.get("action", "none")
        discharge_kw = dispatch_action.get("discharge_kw", 0)
        if action == "discharge":
            reason += f", sufficient for {discharge_kw:.0f}kW discharge"
        elif action == "hold":
            reason += " - holding charge"

    if dispatch_result:
        new_soc = dispatch_result.get("new_soc", battery_soc)
        action_taken = dispatch_result.get("action_taken", "none")
        actual_kw = dispatch_result.get("actual_discharge_kw", 0)
        if action_taken == "discharge":
            act = f"Dispatch {actual_kw:.0f}kW -> SOC drops to {new_soc:.0%}"
        else:
            act = f"Action: {action_taken}"
    else:
        act = "No dispatch result available"

    prompt = _build_tick_prompt(
        dispatch_result=dispatch_result,
        dispatch_action=dispatch_action,
        baseline_load=baseline_load,
        actual_load=actual_load,
        battery_soc=battery_soc,
        cycle_count=cycle_count,
        tariff_window=tariff_window,
        forecast_kw=forecast_kw,
        md_limit_kw=md_limit_kw,
    )
    agent = _get_tick_agent()

    # Always run deterministic safety checks first — non-negotiable (fix 2.2)
    rule_eval: RuleEvaluation = evaluate_rules(
        dispatch_result=dispatch_result,
        battery_soc=battery_soc,
        cycle_count=cycle_count,
        tariff_window=tariff_window,
        dispatch_action=dispatch_action,
    )
    delta_eval: DeltaEvaluation = evaluate_delta(
        dispatch_result=dispatch_result,
        dispatch_action=dispatch_action,
        baseline_load=baseline_load,
        actual_load=actual_load,
        forecast_kw=forecast_kw,
        tariff_window=tariff_window,
        md_limit_kw=md_limit_kw,
    )
    llm_eval: LLMEvaluation | None = None

    if should_run_llm(delta_eval, rule_eval):
        try:
            invoke_config = {"configurable": {"thread_id": f"auditor-{state.get('session_id', 'default')}"}}
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": prompt}]},
                invoke_config,
            )
            messages = result.get("messages", []) if isinstance(result, dict) else []
            last = messages[-1].content if messages else ""
            parsed = _parse_llm_payload(str(last))
            if parsed:
                llm_eval = LLMEvaluation(
                    reasoning=parsed.get("reasoning", ""),
                    recommendation=parsed.get("recommendation", ""),
                    confidence=float(parsed.get("confidence", 0.75)),
                )
        except Exception as exc:
            logger.warning("auditor | agent invoke failed, using deterministic fallback: %s", exc)
        if llm_eval is None:
            llm_eval = LLMEvaluation(
                reasoning=_generate_llm_reasoning(delta_eval, rule_eval),
                recommendation=_generate_recommendation(rule_eval, delta_eval),
                confidence=0.75,
            )

    auditor_result = AuditorResult(
        delta_eval=delta_eval,
        rule_eval=rule_eval,
        llm_eval=llm_eval,
        timestamp=timestamp_str,
        interval=current_interval,
        perceive=perceive,
        reason=reason,
        act=act,
    )

    logger.info(
        "auditor | tick=%d rules=%s delta_score=%.1f shave_kw=%.1f savings_rm=%.4f within_limit=%s",
        current_interval,
        "PASS" if rule_eval.get("passed") else "FAIL",
        delta_eval.get("delta_score", 0.0),
        delta_eval.get("shave_kw", 0.0),
        delta_eval.get("interval_savings_rm", 0.0),
        actual_load <= md_limit_kw,
    )

    decision_entry = {
        "timestamp": timestamp_str,
        "interval": current_interval,
        "perceive": perceive,
        "reason": reason,
        "act": act,
        "evaluate": auditor_result,
    }

    # Rolling forecast error: compare last tick's GRU T+1 prediction against this tick's actual load.
    # predicted_next_kw was written by the previous tick's controller; baseline_load is this tick's truth.
    _ROLLING_WINDOW = 6
    predicted_prev = state.get("predicted_next_kw")
    error_history: list[float] = list(state.get("forecast_error_history") or [])
    if predicted_prev is not None and baseline_load > 0:
        tick_err = abs(baseline_load - predicted_prev) / baseline_load * 100.0
        error_history = (error_history + [tick_err])[-_ROLLING_WINDOW:]
    trailing_mape = sum(error_history) / len(error_history) if error_history else None
    forecast_confidence = max(0.0, 1.0 - trailing_mape / 100.0) if trailing_mape is not None else None

    decision_log = state.get("decision_log", [])
    new_decision_log = decision_log + [decision_entry]

    interval_savings = delta_eval["interval_savings_rm"]
    new_total_savings = state.get("total_savings_rm", 0.0) + interval_savings

    # within_limit_ticks counts PEAK ticks only — MD charges only apply in PEAK
    new_within_limit = state.get("within_limit_ticks", 0)
    is_peak = tariff_window == "PEAK"
    if is_peak and actual_load <= md_limit_kw:
        new_within_limit += 1

    new_peak_ticks = int(state.get("peak_ticks") or 0) + (1 if is_peak else 0)
    new_peak_reduction_kw = float(state.get("peak_reduction_kw") or 0.0)
    if is_peak:
        new_peak_reduction_kw += max(0.0, baseline_load - actual_load)

    # Accumulate possible shave across all ticks (fix 2.7: was using only current tick)
    new_total_possible = float(state.get("total_possible_shave_kw") or 0.0) + max(baseline_load - md_limit_kw, 0.0)
    total_shave = sum(entry["evaluate"]["delta_eval"]["shave_kw"] for entry in new_decision_log)
    shave_percentage = (total_shave / new_total_possible * 100) if new_total_possible > 0 else 0.0

    planner_feedback = {
        "rules_passed": rule_eval.get("passed", True),
        "rule_violations": rule_eval.get("violations", []),
        "delta_score": delta_eval.get("delta_score", 0.0),
        "shave_kw": delta_eval.get("shave_kw", 0.0),
        # within_limit only meaningful in PEAK — OFF_PEAK exceedance has no MD penalty
        "within_limit": (actual_load <= md_limit_kw) if tariff_window == "PEAK" else None,
        "tariff_window": tariff_window,
        "recommendation": (
            llm_eval.get("recommendation", "") if llm_eval
            else _generate_recommendation(rule_eval, delta_eval)
        ),
        "forecast_confidence": forecast_confidence,
        "trailing_mape": trailing_mape,
    }

    return {
        "auditor_result": auditor_result,
        "planner_feedback": planner_feedback,
        "decision_log": new_decision_log,
        "total_savings_rm": new_total_savings,
        "within_limit_ticks": new_within_limit,
        "shave_percentage": shave_percentage,
        "total_possible_shave_kw": new_total_possible,
        "peak_ticks": new_peak_ticks,
        "peak_reduction_kw": new_peak_reduction_kw,
        "forecast_error_history": error_history,
    }


async def run_eod_audit(log_path: Path, day_type: str, date_str: str) -> None:
    """Fire-and-forget EOD audit. Reads JSON log, writes experience file.

    Called from simulation.py after finalize() — log_path is guaranteed to exist.
    """
    model = resolve_deepagents_model(_DEFAULT_MODEL)
    agent = create_deep_agent(
        name="auditor-agent-eod",
        model=model,
        system_prompt=_AUDITOR_PROMPT_EOD,
        tools=[evaluate_rules_tool, evaluate_delta_tool],
        backend=_build_eod_backend(),
    )
    log_filename = log_path.name
    prompt = _build_eod_prompt(log_filename=log_filename, date_str=date_str, day_type=day_type)
    invoke_config = {"configurable": {"thread_id": f"eod-{date_str}-{day_type}"}}
    await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]}, invoke_config)


def _build_eod_prompt(log_filename: str, date_str: str, day_type: str) -> str:
    return (
        f"END OF DAY AUDIT — {date_str} ({day_type})\n\n"
        f"The simulation has completed. The full tick log is at /logs/{log_filename}.\n\n"
        f"Steps:\n"
        f"1. Read /logs/{log_filename} for complete tick-by-tick data (ticks, summary)\n"
        f"2. Read past experience files in /experience/ for pattern comparison (same day_type)\n"
        f"3. Call evaluate_rules_tool and evaluate_delta_tool on the final tick state\n"
        f"4. Write end-of-day summary to /experience/{date_str}-{day_type}.md\n\n"
        f"Do NOT write to /logs/.\n\n"
        f"Return final JSON: {{\"reasoning\": \"...\", \"recommendation\": \"...\", \"confidence\": 0.0}}"
    )


def _build_tick_prompt(
    dispatch_result: dict | None,
    dispatch_action: dict | None,
    baseline_load: float,
    actual_load: float,
    battery_soc: float,
    cycle_count: float,
    tariff_window: str,
    forecast_kw: float,
    md_limit_kw: float,
) -> str:
    return (
        f"Evaluate this tick's BESS dispatch using your tools.\n\n"
        f"State:\n"
        f"  dispatch_result: {dispatch_result}\n"
        f"  dispatch_action: {dispatch_action}\n"
        f"  baseline_load: {baseline_load}\n"
        f"  actual_load: {actual_load}\n"
        f"  battery_soc: {battery_soc}\n"
        f"  cycle_count: {cycle_count}\n"
        f"  tariff_window: {tariff_window}\n"
        f"  forecast_kw: {forecast_kw}\n"
        f"  md_limit_kw: {md_limit_kw}\n\n"
        f"Steps:\n"
        f"1. Call evaluate_rules_tool\n"
        f"2. Call evaluate_delta_tool\n\n"
        f"Return final JSON: {{'reasoning': '...', 'recommendation': '...', 'confidence': 0.0}}"
    )



def _generate_llm_reasoning(delta_eval: DeltaEvaluation, rule_eval: RuleEvaluation) -> str:
    issues = []
    if not rule_eval["passed"]:
        for v in rule_eval["violations"]:
            issues.append(f"{v['severity'].upper()}: {v['detail']}")
    if delta_eval["delta_score"] < 50:
        issues.append(f"Low delta score: {delta_eval['delta_score']:.1f}")
    if delta_eval["forecast_error_pct"] > 20:
        issues.append(f"High forecast error: {delta_eval['forecast_error_pct']:.1f}%")
    return f"Complex case requiring review: {'; '.join(issues) if issues else 'Multiple issues detected'}"


def _generate_recommendation(rule_eval: RuleEvaluation, delta_eval: DeltaEvaluation) -> str:
    if not rule_eval["passed"]:
        violations = [v["rule"] for v in rule_eval["violations"]]
        return f"Safety violations detected: {', '.join(violations)}. Recommend immediate review."
    if delta_eval["delta_score"] < 50:
        return "Performance below target. Consider adjusting dispatch strategy."
    return "Operations within parameters."
