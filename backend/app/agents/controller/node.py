"""Controller node — validates planner strategy, runs MILP via BatteryManager, executes dispatch."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from langchain.tools import tool
from typing_extensions import TypedDict

from app.agents.config import PEAK_END_HOUR, RESERVE_SOC
from app.agents.state import AgentState, BatteryState, DispatchAction, DispatchResult
from app.core.model_selection import resolve_deepagents_model
from app.services.battery_manager import BatteryManager

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
_CONTROLLER_PROMPT = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")


class ControllerResponse(TypedDict, total=False):
    action: str
    discharge_kw: float | None
    charge_kw: float | None
    duration_min: int
    expected_soc_after: float | None
    rejected: bool
    rejection_reason: str | None


@tool
def check_battery_guardrails(
    action: str,
    power_kw: float,
    battery_soc: float,
    temperature_c: float,
    cycle_count: float,
) -> dict:
    """Check if dispatch action is safe given current BESS physical state.

    Args:
        action: proposed action (discharge | charge | hold)
        power_kw: proposed power in kW
        battery_soc: current state-of-charge (0-1)
        temperature_c: current battery temperature °C
        cycle_count: cumulative charge/discharge cycles
    """
    result = BatteryManager.get().check_guardrails(action, power_kw, battery_soc, temperature_c, cycle_count)
    return {"allowed": result.allowed, "reason": result.reason, "override_action": result.override_action}


@tool
def run_milp_optimization(
    load_forecast: list[float],
    tariff_window: str,
    strategy_name: str,
    shave_kw: float,
    reserve_soc_pct: float,
    target_soc_end: float,
    battery_soc: float,
    bess_capacity_kwh: float,
    md_limit_kw: float,
    max_discharge_kw: float,
) -> dict:
    """Compute optimal BESS dispatch schedule using MILP.

    Args:
        load_forecast: list of forecast kW values for the remaining window
        tariff_window: PEAK | OFF_PEAK | WEEKEND
        strategy_name: strategy name from planner (e.g. aggressive_peak_shaving)
        shave_kw: target peak shave amount in kW
        reserve_soc_pct: minimum SOC reserve (0-1)
        target_soc_end: target SOC at end of horizon (0-1)
        battery_soc: current SOC (0-1)
        bess_capacity_kwh: total BESS capacity kWh
        md_limit_kw: maximum demand limit kW
        max_discharge_kw: max discharge rate kW
    """
    strategy_params = {
        "strategy_name": strategy_name,
        "shave_kw": shave_kw,
        "reserve_soc_pct": reserve_soc_pct,
        "target_soc_end": target_soc_end,
    }
    return BatteryManager.get().optimize_dispatch(
        load_forecast, tariff_window, strategy_params,
        battery_soc, bess_capacity_kwh, md_limit_kw, max_discharge_kw,
    )


def _select_facility_forecast(state: AgentState) -> tuple[str | None, list[float]]:
    forecast = state.get("forecast") or {}
    forecasts = forecast.get("load_forecast") or {}
    facility = state.get("current_facility")
    if facility and facility in forecasts:
        return facility, forecasts.get(facility) or []
    if forecasts:
        first = next(iter(forecasts))
        return first, forecasts.get(first) or []
    return None, []


def _compute_remaining_peak_ticks(current_time: Any, tariff_window: str) -> int:
    if tariff_window != "PEAK" or current_time is None:
        return 1
    peak_end_min = PEAK_END_HOUR * 60
    current_min = current_time.hour * 60 + current_time.minute
    remaining_min = max(30, peak_end_min - current_min)
    return remaining_min // 30


def _extend_forecast_to_peak(forecast_values: list[float], remaining_ticks: int) -> list[float]:
    if not forecast_values:
        return forecast_values
    if remaining_ticks <= len(forecast_values):
        return forecast_values[:remaining_ticks]
    pad_value = forecast_values[-1]
    return list(forecast_values) + [pad_value] * (remaining_ticks - len(forecast_values))


_CONTROLLER_AGENT: Any | None = None


def _build_controller_agent() -> Any:
    model = resolve_deepagents_model(_DEFAULT_MODEL)
    logger.info("controller | initializing agent model=%s", model)
    return create_deep_agent(
        name="controller-agent",
        model=model,
        system_prompt=_CONTROLLER_PROMPT,
        tools=[check_battery_guardrails, run_milp_optimization],
        response_format=ControllerResponse,
    )


def _get_controller_agent() -> Any:
    global _CONTROLLER_AGENT
    if _CONTROLLER_AGENT is None:
        _CONTROLLER_AGENT = _build_controller_agent()
    return _CONTROLLER_AGENT


async def controller_node(state: AgentState) -> dict:
    """Validate planner strategy, run MILP dispatch, execute on BESS."""
    facility, forecast_values = _select_facility_forecast(state)

    battery = state.get("battery") or {}
    battery_soc = float(battery.get("soc") or 0.50)
    bess_capacity_kwh = float(battery.get("capacity_kwh") or 500.0)
    temperature_c = float(battery.get("temperature_c") or 30.0)
    cycle_count = float(battery.get("cycle_count") or 0.0)

    tariff = state.get("tariff") or {}
    tariff_window = tariff.get("window") or "PEAK"

    md_limit_kw = float(state.get("md_limit_kw") or 800.0)
    max_discharge_kw = float(state.get("max_discharge_kw") or bess_capacity_kwh)
    optimization_strategy = state.get("optimization_strategy") or {}

    forecast_kw = forecast_values[0] if forecast_values else 0.0
    baseline_load = state.get("baseline_load") or forecast_kw

    current_time = state.get("current_time")
    remaining_peak_ticks = _compute_remaining_peak_ticks(current_time, tariff_window)
    milp_forecast = _extend_forecast_to_peak(forecast_values, remaining_peak_ticks)
    revision_count = state.get("revision_count") or 0

    strategy_str = str(optimization_strategy)
    forecast_str = ", ".join(f"{f:.1f}" for f in forecast_values[:6]) if forecast_values else "N/A"
    milp_str = ", ".join(f"{f:.1f}" for f in milp_forecast) if milp_forecast else "N/A"

    prompt = f"""CURRENT TICK STATE:
- Facility: {facility or 'unknown'}
- Forecast kW: {forecast_kw:.1f} (near-term 6 steps: {forecast_str})
- Tariff window: {tariff_window}
- Battery SOC: {battery_soc:.2%} ({bess_capacity_kwh:.0f} kWh capacity)
- Temperature: {temperature_c:.1f}°C | Cycle count: {cycle_count:.0f}
- MD limit: {md_limit_kw:.0f} kW | Max discharge: {max_discharge_kw:.0f} kW
- Baseline load: {baseline_load:.0f} kW
- Remaining PEAK ticks: {remaining_peak_ticks}
- Full PEAK forecast ({len(milp_forecast)} steps): [{milp_str}]
- Revision attempt: {revision_count} of 2

PLANNER STRATEGY:
{strategy_str}"""

    messages: list[dict[str, str]] = []
    action_dict: dict | None = None
    rejected = False
    rejection_reason: str | None = None

    try:
        agent = _get_controller_agent()
        session_id = state.get("session_id", "default")
        invoke_config = {"configurable": {"thread_id": f"controller-{session_id}"}}
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            invoke_config,
        )
        structured = result.get("structured_response") if isinstance(result, dict) else None
        if isinstance(structured, dict):
            if structured.get("rejected"):
                rejected = True
                rejection_reason = structured.get("rejection_reason", "Plan validation failed")
            elif structured.get("action"):
                action_dict = {
                    "action": structured.get("action", "hold"),
                    "discharge_kw": structured.get("discharge_kw"),
                    "charge_kw": structured.get("charge_kw"),
                    "duration_min": int(structured.get("duration_min") or 30),
                    "expected_soc_after": structured.get("expected_soc_after"),
                }
        if isinstance(result, dict):
            response = result.get("messages", [])
            if response:
                messages.append({"role": "assistant", "content": str(response[-1].content)})
    except Exception as exc:
        logger.warning("controller | agent error, falling back to MILP: %s", exc)

    # If rejected and still within revision budget, send back to planner
    if rejected and revision_count < 2:
        logger.info("controller | rejecting plan (attempt %d): %s", revision_count + 1, rejection_reason)
        return {
            "revision_count": revision_count + 1,
            "rejection_reason": rejection_reason,
            "messages": messages,
        }

    if rejected:
        logger.warning("controller | max revisions hit, forcing hold")

    # Fallback to direct MILP if agent didn't produce an action
    if action_dict is None:
        milp_result = BatteryManager.get().optimize_dispatch(
            milp_forecast, tariff_window, dict(optimization_strategy),
            battery_soc, bess_capacity_kwh, md_limit_kw, max_discharge_kw,
        )
        action_dict = milp_result.get("dispatch_action") or {"action": "hold", "discharge_kw": None, "charge_kw": None, "duration_min": 30}

    # Budget-aware MD override (silent — physical necessity)
    reserve_soc = float((optimization_strategy or {}).get("reserve_soc_pct", RESERVE_SOC))
    action_dict = BatteryManager.get().apply_md_override(
        action_dict, baseline_load, md_limit_kw, battery_soc, bess_capacity_kwh,
        remaining_peak_ticks, max_discharge_kw, reserve_soc, tariff_window,
    )

    # Execute dispatch
    action = action_dict.get("action", "hold")
    power_kw = action_dict.get("discharge_kw") or action_dict.get("charge_kw") or 0.0
    duration_min = int(action_dict.get("duration_min") or 30)
    exec_result = BatteryManager.get().execute_action(action, power_kw, duration_min, battery_soc, bess_capacity_kwh, temperature_c)

    new_temp = temperature_c + exec_result.net_temp_delta_c
    new_cycle = cycle_count + exec_result.cycle_count_delta
    if new_temp >= 45.0:
        logger.warning("controller | battery temp=%.1f°C — thermal derating threshold reached", new_temp)

    actual_load = baseline_load
    if exec_result.action_taken == "discharge":
        actual_load = max(0.0, baseline_load - exec_result.actual_discharge_kw)
    elif exec_result.action_taken == "charge":
        actual_load = baseline_load + power_kw

    logger.info(
        "controller | action=%s power_kw=%.1f soc=%.2f->%.2f baseline=%.1f actual=%.1f",
        exec_result.action_taken, exec_result.actual_discharge_kw,
        battery_soc, exec_result.new_soc, baseline_load, actual_load,
    )

    return {
        "battery": BatteryState(
            soc=exec_result.new_soc,
            capacity_kwh=bess_capacity_kwh,
            cycle_count=new_cycle,
            temperature_c=new_temp,
        ),
        "dispatch_action": DispatchAction(
            action=action,
            discharge_kw=action_dict.get("discharge_kw"),
            charge_kw=action_dict.get("charge_kw"),
            duration_min=duration_min,
            expected_soc_after=action_dict.get("expected_soc_after"),
        ),
        "dispatch_result": DispatchResult(
            new_soc=exec_result.new_soc,
            temp_increase_c=exec_result.net_temp_delta_c,
            cycle_count_delta=exec_result.cycle_count_delta,
            action_taken=exec_result.action_taken,
            actual_discharge_kw=exec_result.actual_discharge_kw,
            efficiency_loss_pct=exec_result.efficiency_loss_pct,
        ),
        "forecast_kw": forecast_kw,
        "baseline_load": baseline_load,
        "actual_load": actual_load,
        "last_dispatch_kw": exec_result.actual_discharge_kw,
        "last_dispatch_duration_min": duration_min,
        "rejection_reason": None,
        "messages": messages,
    }
