"""Auditor Agent - post-dispatch verification with 3 evaluation modes.

Per SPEC-auditor.md:
- evaluate_rules runs FIRST (safety non-negotiable)
- evaluate_delta runs SECOND (numeric scoring)
- evaluate_llm runs ONLY when: delta_score < 50 OR forecast_error > 20% OR violations
"""

from datetime import datetime
import json
import os
from typing import TypedDict

from deepagents import create_deep_agent
from app.agents.auditor.evaluation import (
    DeltaEvaluation,
    LLMEvaluation,
    RuleEvaluation,
    evaluate_delta,
    evaluate_rules,
    should_run_llm,
)


_DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

_AUDITOR_PROMPT = """You are the Auditor Agent for FusionQuad.
Evaluate dispatch outcomes and provide reasoning + recommendation when prompted.

Return JSON only with:
{
    "reasoning": "...",
    "recommendation": "...",
    "confidence": 0.0
}
"""


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


def _deep_agent_enabled(state: dict) -> bool:
    if state.get("use_deep_agent") is True:
        return True
    flag = os.getenv("DEEPAGENTS_ENABLED", "").strip().lower()
    return flag in {"1", "true", "yes", "on"}


_AUDITOR_AGENT = None


def _get_auditor_agent():
    global _AUDITOR_AGENT
    if _AUDITOR_AGENT is None:
        model = os.getenv("DEEPAGENTS_MODEL", _DEFAULT_MODEL)
        _AUDITOR_AGENT = create_deep_agent(
            name="auditor-agent",
            model=model,
            system_prompt=_AUDITOR_PROMPT,
        )
    return _AUDITOR_AGENT


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
    """Main auditor node - evaluates Controller dispatch results."""
    dispatch_result = state.get("dispatch_result")
    dispatch_action = state.get("dispatch_action")
    baseline_load = state.get("baseline_load", 0.0)
    actual_load = state.get("actual_load", 0.0)
    battery_soc = state.get("battery_soc", 0.0)
    cycle_count = state.get("cycle_count", 0.0)
    tariff_window = state.get("tariff_window", "PEAK")
    current_time = state.get("current_time")
    forecast_kw = state.get("forecast_kw", 0.0)
    md_limit_kw = state.get("md_limit_kw", 800.0)

    current_interval = state.get("current_interval", 0)
    decision_log = state.get("decision_log", [])
    total_savings_rm = state.get("total_savings_rm", 0.0)
    within_limit_ticks = state.get("within_limit_ticks", 0)
    total_intervals = state.get("total_intervals", 0)

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

    # MODE 1: Safety rules FIRST
    rule_eval = evaluate_rules(
        dispatch_result=dispatch_result,
        battery_soc=battery_soc,
        cycle_count=cycle_count,
        tariff_window=tariff_window,
        dispatch_action=dispatch_action,
    )

    # MODE 2: Delta scoring ALWAYS
    delta_eval = evaluate_delta(
        dispatch_result=dispatch_result,
        dispatch_action=dispatch_action,
        baseline_load=baseline_load,
        actual_load=actual_load,
        forecast_kw=forecast_kw,
        tariff_window=tariff_window,
        md_limit_kw=md_limit_kw,
    )

    interval_savings = delta_eval["interval_savings_rm"]
    new_total_savings = total_savings_rm + interval_savings

    new_within_limit = within_limit_ticks
    if actual_load <= md_limit_kw:
        new_within_limit += 1

    # MODE 3: LLM reasoning only when needed
    llm_eval = None
    if should_run_llm(delta_eval, rule_eval):
        if _deep_agent_enabled(state):
            prompt = (
                "Analyze the following evaluation data and provide reasoning and a recommendation.\n\n"
                f"Delta evaluation: {delta_eval}\n"
                f"Rule evaluation: {rule_eval}\n"
                f"Tariff window: {tariff_window}\n"
            )
            try:
                agent = _get_auditor_agent()
                result = agent.invoke(
                    {"messages": [{"role": "user", "content": prompt}]},
                    config={"configurable": {"thread_id": "auditor"}},
                )
                messages = result.get("messages", []) if isinstance(result, dict) else []
                last = messages[-1].content if messages else ""
                parsed = _parse_llm_payload(str(last)) or {}
                llm_eval = LLMEvaluation(
                    reasoning=parsed.get("reasoning", _generate_llm_reasoning(delta_eval, rule_eval)),
                    recommendation=parsed.get("recommendation", _generate_recommendation(rule_eval, delta_eval)),
                    confidence=float(parsed.get("confidence", 0.75)),
                )
            except Exception:
                llm_eval = LLMEvaluation(
                    reasoning=_generate_llm_reasoning(delta_eval, rule_eval),
                    recommendation=_generate_recommendation(rule_eval, delta_eval),
                    confidence=0.75,
                )
        else:
            llm_eval = LLMEvaluation(
                reasoning=_generate_llm_reasoning(delta_eval, rule_eval),
                recommendation=_generate_recommendation(rule_eval, delta_eval),
                confidence=0.75,
            )

    timestamp_str = current_time.strftime("%Y-%m-%d %H:%M") if isinstance(current_time, datetime) else str(current_time or "")

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
    new_decision_log = decision_log + [decision_entry]

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
        "total_intervals": total_intervals + 1,
        "shave_percentage": shave_percentage,
    }


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


def end_of_day_summary(state: dict) -> dict:
    decision_log = state.get("decision_log", [])
    total_intervals = len(decision_log)
    within_limit_ticks = state.get("within_limit_ticks", 0)
    compliance_rate = within_limit_ticks / total_intervals if total_intervals > 0 else 0.0
    total_savings = state.get("total_savings_rm", 0.0)
    shave_pct = state.get("shave_percentage", 0.0)
    critical_violations = []
    for entry in decision_log:
        eval_data = entry.get("evaluate", {})
        rule = eval_data.get("rule_eval", {})
        for v in rule.get("violations", []):
            if v["severity"] == "critical":
                critical_violations.append(v["detail"])
    return {
        "total_intervals": total_intervals,
        "within_limit_ticks": within_limit_ticks,
        "compliance_rate": compliance_rate,
        "total_savings_rm": total_savings,
        "peak_shave_pct": shave_pct,
        "avg_soc": 0.0,
        "max_temp_c": 0.0,
        "total_cycles_used": 0.0,
        "critical_violations": critical_violations,
        "recommendation": "Review critical violations before next dispatch cycle." if critical_violations else "All systems nominal.",
    }
