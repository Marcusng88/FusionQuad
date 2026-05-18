"""Controller node that executes BESS dispatch via MILP + mock inverter tools."""

from __future__ import annotations

from dataclasses import asdict
import logging
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from langchain.tools import tool

from app.agents.controller.middleware import DispatchValidationMiddleware
from app.agents.optimization.solver import OptimizationInput, OptimizationSolver
from app.agents.state import AgentState, BatteryState, DispatchAction, DispatchResult
from app.core.model_selection import resolve_deepagents_model

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

_CONTROLLER_PROMPT = (Path(__file__).parent / "prompts" / "system.md").read_text(encoding="utf-8")


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


@tool
def milp_optimizer(
    load_forecast: list[float],
    tariff_window: str,
    battery_soc: float,
    bess_capacity_kwh: float,
    md_limit_kw: float,
    strategy_name: str = "conservative_shaving",
    shave_kw: float = 80.0,
    target_soc_end: float = 0.5,
    reserve_soc_pct: float = 0.2,
) -> dict:
    """MILP solver — computes optimal BESS dispatch action for this tick.

    Args:
        load_forecast: List of forecast kW values (at least 1 for current tick)
        tariff_window: PEAK | OFF_PEAK | WEEKEND
        battery_soc: Current state-of-charge (0-1)
        bess_capacity_kwh: Installed BESS capacity
        md_limit_kw: Maximum demand limit kW
        strategy_name: Strategy from planner e.g. conservative_shaving
        shave_kw: Target peak shave amount in kW
        target_soc_end: Target SOC at end of horizon (0-1)
        reserve_soc_pct: Minimum SOC reserve (0-1)
    """
    solver = OptimizationSolver()
    forecast_values = load_forecast if isinstance(load_forecast, list) and len(load_forecast) > 0 else []

    optimization_strategy = {
        "strategy_name": strategy_name,
        "shave_kw": shave_kw,
        "target_soc_end": target_soc_end,
        "reserve_soc_pct": reserve_soc_pct,
    }

    input_data = OptimizationInput(
        optimization_strategy=optimization_strategy,
        load_forecast=forecast_values,
        tariff_window=tariff_window,
        battery_soc=battery_soc,
        bess_capacity_kwh=bess_capacity_kwh,
        md_limit_kw=md_limit_kw,
        current_dispatch_index=0,
        previous_dispatch_plan=None,
    )

    result = solver.solve(input_data)
    dispatch_action = asdict(result.dispatch_action)
    dispatch_action["expected_soc_after"] = result.dispatch_action.expected_soc_after

    return {"dispatch_action": dispatch_action}


def mock_inverter_dispatch(
    action: str,
    power_kw: float,
    duration_min: int,
    current_soc: float,
    bess_capacity_kwh: float,
    temperature_c: float,
) -> dict[str, Any]:
    """Mock smart inverter dispatch - simulates BESS response.

    Args:
        action: discharge | charge | hold
        power_kw: Power in kW for charge/discharge
        duration_min: Duration in minutes (default 30)
        current_soc: SOC before dispatch (0-1)
        bess_capacity_kwh: Total BESS capacity
        temperature_c: Current BESS temperature
    """
    efficiency_loss_pct = 0.05
    charge_efficiency = 0.95

    if action == "discharge":
        energy_kwh = power_kw * (duration_min / 60)
        actual_discharge = energy_kwh * (1 - efficiency_loss_pct)
        new_soc = max(0.0, current_soc - (actual_discharge / bess_capacity_kwh))
        temp_increase = 0.5 * (power_kw / 100)
        cycle_increment = energy_kwh / (2 * bess_capacity_kwh)
        actual_kw = power_kw
    elif action == "charge":
        energy_kwh = power_kw * (duration_min / 60)
        new_soc = min(current_soc + (energy_kwh * charge_efficiency / bess_capacity_kwh), 0.95)
        temp_increase = 0.2 * (power_kw / 100)
        cycle_increment = 0.0
        actual_kw = power_kw
    else:
        new_soc = current_soc
        temp_increase = 0.1
        cycle_increment = 0.0
        actual_kw = 0.0

    return {
        "new_soc": new_soc,
        "temp_increase_c": temp_increase,
        "cycle_count_increment": cycle_increment,
        "action_taken": action,
        "actual_discharge_kw": actual_kw,
        "efficiency_loss_pct": efficiency_loss_pct,
    }


_AMBIENT_TEMP_C = 25.0
_COOLING_RATE = 0.05  # fraction of (T - ambient) dissipated per 30-min tick

_CONTROLLER_AGENT: Any | None = None


def _build_controller_agent() -> Any:
    model = resolve_deepagents_model(_DEFAULT_MODEL)
    logger.info("controller | initializing agent model=%s", model)
    return create_deep_agent(
        name="controller-agent",
        model=model,
        system_prompt=_CONTROLLER_PROMPT,
        tools=[milp_optimizer],
        middleware=[DispatchValidationMiddleware(max_retries=2)],
        response_format=DispatchAction,
    )


def _get_controller_agent() -> Any:
    global _CONTROLLER_AGENT
    if _CONTROLLER_AGENT is None:
        _CONTROLLER_AGENT = _build_controller_agent()
    return _CONTROLLER_AGENT


async def controller_node(state: AgentState) -> dict:
    """Execute BESS dispatch using MILP optimization + inverter execution."""
    facility, forecast_values = _select_facility_forecast(state)

    # Read battery state from value object
    battery = state.get("battery") or {}
    battery_soc = float(battery.get("soc") or 0.50)
    bess_capacity_kwh = float(battery.get("capacity_kwh") or 500.0)
    temperature_c = float(battery.get("temperature_c") or 30.0)
    cycle_count = float(battery.get("cycle_count") or 0.0)

    # Read tariff context from value object
    tariff = state.get("tariff") or {}
    tariff_window = tariff.get("window") or "OFF_PEAK"

    md_limit_kw = float(state.get("md_limit_kw") or 800.0)
    optimization_strategy = state.get("optimization_strategy") or {}

    forecast_kw = forecast_values[0] if forecast_values else 0.0
    baseline_load = state.get("baseline_load")
    if baseline_load is None:
        baseline_load = forecast_kw

    # Safety: force hold if SOC critically low
    forced_action: dict | None = None
    if battery_soc < 0.20:
        forced_action = {"action": "hold", "discharge_kw": None, "charge_kw": None, "duration_min": 30}

    messages: list[dict[str, str]] = []

    prompt = _build_controller_prompt(
        facility=facility,
        forecast_values=forecast_values,
        forecast_kw=forecast_kw,
        tariff_window=tariff_window,
        battery_soc=battery_soc,
        bess_capacity_kwh=bess_capacity_kwh,
        md_limit_kw=md_limit_kw,
        optimization_strategy=dict(optimization_strategy),
        temperature_c=temperature_c,
        baseline_load=baseline_load,
    )

    try:
        agent = _get_controller_agent()
        session_id = state.get("session_id", "default")
        invoke_config = {"configurable": {"thread_id": f"controller-{session_id}"}}
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            invoke_config,
        )
        structured = result.get("structured_response") if isinstance(result, dict) else None
        if isinstance(structured, dict) and structured.get("action"):
            forced_action = {
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
        forced_action = forced_action or None

    if forced_action is None:
        forced_action = _local_milp_fallback(
            forecast_values=forecast_values,
            tariff_window=tariff_window,
            battery_soc=battery_soc,
            bess_capacity_kwh=bess_capacity_kwh,
            md_limit_kw=md_limit_kw,
            optimization_strategy=dict(optimization_strategy),
        )

    # Safety override: during PEAK, if actual load exceeds MD limit and battery has capacity,
    # ensure minimum discharge regardless of what the planner/agent decided.
    # This prevents the monthly MD record being set by a single hold tick.
    reserve_soc = float((optimization_strategy or {}).get("reserve_soc_pct", 0.25))
    if (
        tariff_window == "PEAK"
        and baseline_load > md_limit_kw
        and battery_soc > reserve_soc + 0.05
    ):
        min_discharge_kw = min(baseline_load - md_limit_kw + 15.0, 100.0)
        current_kw = forced_action.get("discharge_kw") or 0.0
        if forced_action.get("action") != "discharge" or current_kw < min_discharge_kw:
            logger.info(
                "controller | MD override: baseline=%.1f > limit=%.1f, forcing discharge %.1f kW",
                baseline_load, md_limit_kw, min_discharge_kw,
            )
            forced_action = {
                "action": "discharge",
                "discharge_kw": min_discharge_kw,
                "charge_kw": None,
                "duration_min": 30,
            }

    raw_result = _execute_dispatch(
        action_dict=forced_action,
        battery_soc=battery_soc,
        bess_capacity_kwh=bess_capacity_kwh,
        temperature_c=temperature_c,
    )

    new_soc = raw_result.get("new_soc", battery_soc)
    heat_gain = raw_result.get("temp_increase_c", 0.0)
    cooling = _COOLING_RATE * max(0.0, temperature_c - _AMBIENT_TEMP_C)
    new_temp = temperature_c + heat_gain - cooling
    if new_temp >= 45.0:
        logger.warning("controller | battery temp=%.1f°C — thermal derating threshold reached", new_temp)
    new_cycle = cycle_count + raw_result.get("cycle_count_increment", 0.0)
    action_taken = raw_result.get("action_taken", "hold")
    actual_kw = raw_result.get("actual_discharge_kw", 0.0)

    actual_load = baseline_load
    if action_taken == "discharge":
        actual_load = max(0.0, baseline_load - actual_kw)
    elif action_taken == "charge":
        actual_load = baseline_load + actual_kw

    logger.info(
        "controller | action=%s power_kw=%.1f soc=%.2f->%.2f baseline=%.1f actual=%.1f",
        action_taken, actual_kw, battery_soc, new_soc, baseline_load, actual_load,
    )

    dispatch_action = DispatchAction(
        action=forced_action.get("action", "hold"),
        discharge_kw=forced_action.get("discharge_kw"),
        charge_kw=forced_action.get("charge_kw"),
        duration_min=int(forced_action.get("duration_min") or 30),
        expected_soc_after=forced_action.get("expected_soc_after"),
    )

    dispatch_result = DispatchResult(
        new_soc=new_soc,
        temp_increase_c=raw_result.get("temp_increase_c", 0.0),
        cycle_count_delta=raw_result.get("cycle_count_increment", 0.0),
        action_taken=action_taken,
        actual_discharge_kw=actual_kw,
        efficiency_loss_pct=raw_result.get("efficiency_loss_pct", 0.05),
    )

    return {
        "battery": BatteryState(
            soc=new_soc,
            capacity_kwh=bess_capacity_kwh,
            cycle_count=new_cycle,
            temperature_c=new_temp,
        ),
        "dispatch_action": dispatch_action,
        "dispatch_result": dispatch_result,
        "forecast_kw": forecast_kw,
        "baseline_load": baseline_load,
        "actual_load": actual_load,
        "last_dispatch_kw": actual_kw,
        "last_dispatch_duration_min": int(forced_action.get("duration_min") or 30),
        "messages": messages,
    }


def _build_controller_prompt(
    facility: str | None,
    forecast_values: list[float],
    forecast_kw: float,
    tariff_window: str,
    battery_soc: float,
    bess_capacity_kwh: float,
    md_limit_kw: float,
    optimization_strategy: dict,
    temperature_c: float,
    baseline_load: float,
) -> str:
    strategy_str = str(optimization_strategy)
    forecast_str = ", ".join(f"{f:.1f}" for f in forecast_values[:6]) if forecast_values else "N/A"

    return f"""You are the Controller Agent for FusionQuad.

CURRENT TICK STATE:
- Facility: {facility or 'unknown'}
- Forecast kW: {forecast_kw:.1f} (near-term: {forecast_str})
- Tariff window: {tariff_window}
- Battery SOC: {battery_soc:.2%} ({bess_capacity_kwh:.0f} kWh capacity)
- MD limit: {md_limit_kw:.0f} kW
- Temperature: {temperature_c:.1f}°C
- Baseline load: {baseline_load:.0f} kW

OPTIMIZATION STRATEGY (from Planner):
{strategy_str}

YOUR TASK:
1. Call milp_optimizer with the state parameters above
2. Extract the dispatch_action from the result
3. Respond with the dispatch action fields (action, discharge_kw, charge_kw, duration_min, expected_soc_after)

IMPORTANT:
- If SOC < 20%, respond with action="hold" and skip milp_optimizer
- Do NOT call mock_inverter_dispatch — hardware simulation is handled externally
- Respond ONLY with the structured dispatch action
"""


def _local_milp_fallback(
    forecast_values: list[float],
    tariff_window: str,
    battery_soc: float,
    bess_capacity_kwh: float,
    md_limit_kw: float,
    optimization_strategy: dict,
) -> dict:
    """Fallback MILP computation when the deep agent is unavailable."""
    solver = OptimizationSolver()

    input_data = OptimizationInput(
        optimization_strategy=optimization_strategy,
        load_forecast=forecast_values,
        tariff_window=tariff_window,
        battery_soc=battery_soc,
        bess_capacity_kwh=bess_capacity_kwh,
        md_limit_kw=md_limit_kw,
        current_dispatch_index=0,
        previous_dispatch_plan=None,
    )

    result = solver.solve(input_data)
    dispatch_action = asdict(result.dispatch_action)
    dispatch_action["expected_soc_after"] = result.dispatch_action.expected_soc_after
    return dispatch_action


def _execute_dispatch(
    action_dict: dict,
    battery_soc: float,
    bess_capacity_kwh: float,
    temperature_c: float,
) -> dict:
    """Execute dispatch via the mock inverter."""
    action = action_dict.get("action", "hold")
    duration_min = action_dict.get("duration_min", 30)

    power_kw = 0.0
    if action == "discharge":
        power_kw = action_dict.get("discharge_kw", 0.0) or 0.0
    elif action == "charge":
        power_kw = action_dict.get("charge_kw", 0.0) or 0.0

    return mock_inverter_dispatch(
        action=action,
        power_kw=power_kw,
        duration_min=duration_min,
        current_soc=battery_soc,
        bess_capacity_kwh=bess_capacity_kwh,
        temperature_c=temperature_c,
    )
