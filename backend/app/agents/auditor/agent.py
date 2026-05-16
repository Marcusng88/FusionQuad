"""Auditor Agent — Deep Agent for post-dispatch evaluation.

Performs tool-based evaluations every tick:
1. evaluate_rules_tool — safety checks (non-negotiable)
2. evaluate_delta_tool — numeric scoring (always)

The deep agent uses CompositeBackend with FilesystemBackend scoped to
/experience/ and /strategies/ only — no access to other paths.
At end-of-day, it reads past audit reports and appends a summary.
"""

from datetime import datetime
from pathlib import Path
import json
from typing import TypedDict

_PROMPTS_DIR = Path(__file__).parent / "prompts"

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from deepagents.backends.state import StateBackend
from deepagents.backends.composite import CompositeBackend
from langchain.tools import tool

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
_AUDITOR_AGENT_EOD: object | None = None


def _build_auditor_backend() -> CompositeBackend:
    """Build a CompositeBackend scoped to /experience/ and /strategies/ only."""
    return CompositeBackend(
        default=StateBackend(),
        routes={
            "/experience/": FilesystemBackend(root_dir=str(_EXPERIENCE_DIR), virtual_mode=True),
            "/strategies/": FilesystemBackend(root_dir=str(_STRATEGIES_DIR), virtual_mode=True),
        },
    )


def _get_auditor_agent(system_prompt: str, is_eod: bool) -> object:
    global _AUDITOR_AGENT_TICK, _AUDITOR_AGENT_EOD
    backend = _build_auditor_backend()
    if is_eod:
        if _AUDITOR_AGENT_EOD is None:
            model = resolve_deepagents_model(_DEFAULT_MODEL)
            _AUDITOR_AGENT_EOD = create_deep_agent(
                name="auditor-agent-eod",
                model=model,
                system_prompt=system_prompt,
                tools=[evaluate_rules_tool, evaluate_delta_tool],
                backend=backend,
            )
        return _AUDITOR_AGENT_EOD
    else:
        if _AUDITOR_AGENT_TICK is None:
            model = resolve_deepagents_model(_DEFAULT_MODEL)
            _AUDITOR_AGENT_TICK = create_deep_agent(
                name="auditor-agent-tick",
                model=model,
                system_prompt=system_prompt,
                tools=[evaluate_rules_tool, evaluate_delta_tool],
                backend=backend,
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


def auditor_node(state: dict) -> dict:
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
    day_type = state.get("day_type", "unknown")
    is_end_of_day = state.get("is_end_of_day", False)

    battery = state.get("battery") or {}
    battery_soc = float(battery.get("soc") or 0.0)
    cycle_count = float(battery.get("cycle_count") or 0.0)

    tariff = state.get("tariff") or {}
    tariff_window = tariff.get("window") or "PEAK"

    timestamp_str = current_time.strftime("%Y-%m-%d %H:%M") if isinstance(current_time, datetime) else str(current_time or "")
    date_str = current_time.strftime("%Y-%m-%d") if isinstance(current_time, datetime) else ""

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

    if is_end_of_day:
        prompt = _build_eod_prompt(
            date_str=date_str,
            day_type=day_type,
            dispatch_result=dispatch_result,
            dispatch_action=dispatch_action,
            baseline_load=baseline_load,
            actual_load=actual_load,
            battery_soc=battery_soc,
            cycle_count=cycle_count,
            tariff_window=tariff_window,
            forecast_kw=forecast_kw,
            md_limit_kw=md_limit_kw,
            current_interval=current_interval,
            state=state,
        )
        agent = _get_auditor_agent(_AUDITOR_PROMPT_EOD, is_eod=True)
    else:
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
        agent = _get_auditor_agent(_AUDITOR_PROMPT_TICK, is_eod=False)

    rule_eval: RuleEvaluation = {"passed": True, "violations": []}
    delta_eval: DeltaEvaluation = {"shave_kw": 0.0, "shave_pct": 0.0, "forecast_error_pct": 0.0, "interval_savings_rm": 0.0, "delta_score": 0.0}
    llm_eval: LLMEvaluation | None = None

    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"configurable": {"thread_id": f"auditor-{state.get('session_id', 'main')}"}},
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
    except Exception:
        pass

    if llm_eval is None:
        rule_eval = evaluate_rules(
            dispatch_result=dispatch_result,
            battery_soc=battery_soc,
            cycle_count=cycle_count,
            tariff_window=tariff_window,
            dispatch_action=dispatch_action,
        )
        delta_eval = evaluate_delta(
            dispatch_result=dispatch_result,
            dispatch_action=dispatch_action,
            baseline_load=baseline_load,
            actual_load=actual_load,
            forecast_kw=forecast_kw,
            tariff_window=tariff_window,
            md_limit_kw=md_limit_kw,
        )
        if should_run_llm(delta_eval, rule_eval):
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

    decision_entry = {
        "timestamp": timestamp_str,
        "interval": current_interval,
        "perceive": perceive,
        "reason": reason,
        "act": act,
        "evaluate": auditor_result,
    }

    decision_log = state.get("decision_log", [])
    new_decision_log = decision_log + [decision_entry]

    interval_savings = delta_eval["interval_savings_rm"]
    new_total_savings = state.get("total_savings_rm", 0.0) + interval_savings

    new_within_limit = state.get("within_limit_ticks", 0)
    if actual_load <= md_limit_kw:
        new_within_limit += 1

    total_possible_shave = baseline_load - md_limit_kw if baseline_load > md_limit_kw else 0
    if total_possible_shave > 0:
        total_shave = sum(entry["evaluate"]["delta_eval"]["shave_kw"] for entry in new_decision_log)
        shave_percentage = (total_shave / (total_possible_shave * len(new_decision_log))) * 100 if new_decision_log else 0
    else:
        shave_percentage = 0.0

    return {
        "auditor_result": auditor_result,
        "decision_log": new_decision_log,
        "total_savings_rm": new_total_savings,
        "within_limit_ticks": new_within_limit,
        "total_intervals": state.get("total_intervals", 0) + 1,
        "shave_percentage": shave_percentage,
    }


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


def _build_eod_prompt(
    date_str: str,
    day_type: str,
    dispatch_result: dict | None,
    dispatch_action: dict | None,
    baseline_load: float,
    actual_load: float,
    battery_soc: float,
    cycle_count: float,
    tariff_window: str,
    forecast_kw: float,
    md_limit_kw: float,
    current_interval: int,
    state: dict,
) -> str:
    decision_log = state.get("decision_log", [])
    total_intervals = len(decision_log) if decision_log else current_interval + 1
    within_limit = state.get("within_limit_ticks", 0)
    total_savings = state.get("total_savings_rm", 0.0)

    return (
        f"END OF DAY — produce end-of-day audit summary.\n\n"
        f"DATE: {date_str} | DAY TYPE: {day_type}\n"
        f"TICK: {current_interval} | TOTAL TICKS: {total_intervals}\n"
        f"COMPLIANCE: {within_limit}/{total_intervals} ticks within MD limit\n"
        f"TOTAL SAVINGS: RM{total_savings:.2f}\n\n"
        f"STATE:\n"
        f"  dispatch_result: {dispatch_result}\n"
        f"  dispatch_action: {dispatch_action}\n"
        f"  baseline_load: {baseline_load}\n"
        f"  actual_load: {actual_load}\n"
        f"  battery_soc: {battery_soc}\n"
        f"  cycle_count: {cycle_count}\n"
        f"  tariff_window: {tariff_window}\n"
        f"  forecast_kw: {forecast_kw}\n"
        f"  md_limit_kw: {md_limit_kw}\n\n"
        f"STEPS:\n"
        f"1. Use read_file tool to read past experience files in /experience/ for context\n"
        f"2. Call evaluate_rules_tool\n"
        f"3. Call evaluate_delta_tool\n"
        f"4. Use write_file tool to append the end-of-day summary to /experience/{date_str}-{day_type}.md\n\n"
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
