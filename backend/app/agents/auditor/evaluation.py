"""Evaluation tools for the Auditor agent."""

from typing import TypedDict

from app.agents.tariff.rates import get_energy_rate as _get_central_rate


class DeltaEvaluation(TypedDict):
    """Result of evaluate_delta numeric scoring."""
    shave_kw: float
    shave_pct: float
    forecast_error_pct: float
    interval_savings_rm: float
    delta_score: float  # 0-100


class RuleViolation(TypedDict):
    """A single rule violation."""
    rule: str
    severity: str  # "critical" | "warning"
    detail: str


class RuleEvaluation(TypedDict):
    """Result of evaluate_rules safety checks."""
    passed: bool
    violations: list[RuleViolation]


class LLMEvaluation(TypedDict):
    """Result of evaluate_llm reasoning."""
    reasoning: str
    recommendation: str
    confidence: float  # 0-1


def evaluate_delta(
    dispatch_result: dict | None,
    dispatch_action: dict | None,
    baseline_load: float,
    actual_load: float,
    forecast_kw: float,
    tariff_window: str,
    md_limit_kw: float = 800.0,
) -> DeltaEvaluation:
    """Mode 2: Numeric scoring - calculate shave metrics and delta score."""
    if dispatch_result is None or dispatch_action is None:
        return DeltaEvaluation(
            shave_kw=0.0,
            shave_pct=0.0,
            forecast_error_pct=0.0,
            interval_savings_rm=0.0,
            delta_score=0.0,
        )

    action = dispatch_action.get("action", "none")
    discharge_kw = dispatch_action.get("discharge_kw", 0.0)
    duration_min = dispatch_action.get("duration_min", 30)

    # Shave metrics
    shave_kw = baseline_load - actual_load if actual_load < baseline_load else 0.0

    if baseline_load > 0:
        shave_pct = (shave_kw / baseline_load) * 100
    else:
        shave_pct = 0.0

    # Forecast error
    if forecast_kw > 0:
        forecast_error_pct = abs(actual_load - forecast_kw) / forecast_kw * 100
    else:
        forecast_error_pct = 0.0

    rate = _get_central_rate("C2", tariff_window)
    energy_savings_rm = shave_kw * (duration_min / 60) * rate
    # MD charge billed on monthly peak at RM97.06/kW — amortize over 1440 intervals/month
    _MD_RATE_RM_PER_KW = 97.06
    md_shave_kw = max(0.0, min(shave_kw, baseline_load - md_limit_kw)) if baseline_load > md_limit_kw else 0.0
    interval_savings_rm = energy_savings_rm + md_shave_kw * _MD_RATE_RM_PER_KW / 1440

    # Delta score: weighted combination of metrics
    # Higher shave = better, lower forecast error = better
    shave_score = min(shave_pct * 2, 100)  # up to 100 for 50%+ shave
    accuracy_score = max(0, 100 - forecast_error_pct)  # 100 if perfect

    delta_score = (shave_score * 0.6) + (accuracy_score * 0.4)

    return DeltaEvaluation(
        shave_kw=shave_kw,
        shave_pct=shave_pct,
        forecast_error_pct=forecast_error_pct,
        interval_savings_rm=interval_savings_rm,
        delta_score=delta_score,
    )


def evaluate_rules(
    dispatch_result: dict | None,
    battery_soc: float,
    cycle_count: float,
    tariff_window: str,
    dispatch_action: dict | None,
) -> RuleEvaluation:
    """Mode 1: Safety checks - runs FIRST, non-negotiable."""
    violations: list[RuleViolation] = []

    # Critical: SOC too low
    if battery_soc is not None and battery_soc < 0.20:
        violations.append(RuleViolation(
            rule="soc_minimum",
            severity="critical",
            detail=f"SOC {battery_soc:.1%} below 20% minimum threshold",
        ))

    # Critical: cycle count exceeded
    if cycle_count is not None and cycle_count > 3000:
        violations.append(RuleViolation(
            rule="cycle_count_max",
            severity="critical",
            detail=f"Cycle count {cycle_count:.0f} exceeds 3000 limit",
        ))

    # Check dispatch_result fields if available
    if dispatch_result is not None:
        temp_increase = dispatch_result.get("temp_increase_c", 0)
        if temp_increase > 5.0:
            violations.append(RuleViolation(
                rule="temperature_rise",
                severity="critical",
                detail=f"Temperature increase {temp_increase:.1f}°C exceeds 5°C limit",
            ))

        actual_discharge = dispatch_result.get("actual_discharge_kw", 0)
        if actual_discharge > 100:
            violations.append(RuleViolation(
                rule="inverter_power_limit",
                severity="critical",
                detail=f"Discharge {actual_discharge:.0f}kW exceeds 100kW inverter limit",
            ))

    # Warning: OFF_PEAK discharge
    if tariff_window == "OFF_PEAK" and dispatch_action:
        action = dispatch_action.get("action", "none")
        if action == "discharge":
            violations.append(RuleViolation(
                rule="off_peak_discharge",
                severity="warning",
                detail="Discharging during OFF_PEAK window - may be suboptimal",
            ))

    passed = not any(v["severity"] == "critical" for v in violations)
    return RuleEvaluation(passed=passed, violations=violations)


def should_run_llm(delta_eval: DeltaEvaluation, rule_eval: RuleEvaluation) -> bool:
    """Determine if LLM evaluation is needed."""
    if not rule_eval["passed"]:
        return True
    if delta_eval["delta_score"] < 50:
        return True
    if delta_eval["forecast_error_pct"] > 20:
        return True
    return False
