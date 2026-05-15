"""Optimization agent - generates BESS dispatch plan via MILP solver."""

from dataclasses import asdict

from app.agents.state import AgentState
from app.agents.optimization.solver import OptimizationInput, OptimizationSolver


def _select_facility_forecast(state: AgentState) -> tuple[str | None, list[float]]:
    forecasts = state.get("load_forecast") or {}
    facility = state.get("current_facility")
    if facility and facility in forecasts:
        return facility, forecasts.get(facility) or []
    if forecasts:
        first = next(iter(forecasts))
        return first, forecasts.get(first) or []
    return None, []


def _build_solver_strategy(strategy: dict | None) -> dict:
    if not strategy:
        return {}

    targets = strategy.get("targets") or {}
    solver_strategy = {
        "strategy": strategy.get("strategy") or strategy.get("strategy_name"),
        "shave_kw": targets.get("shave_kw", strategy.get("shave_kw", 0.0)),
        "reserve_soc_pct": targets.get("reserve_soc_pct", strategy.get("reserve_soc_pct", 0.20)),
        "target_soc_end": strategy.get("target_soc_end", 0.50),
    }
    return solver_strategy


def optimization_node(state: AgentState) -> dict:
    """Generate dispatch_plan and dispatch_action using the MILP solver."""
    facility, forecast_values = _select_facility_forecast(state)
    if isinstance(forecast_values, (int, float)):
        forecast_values = [forecast_values]

    solver = OptimizationSolver()
    solver_strategy = _build_solver_strategy(state.get("optimization_strategy"))

    input_data = OptimizationInput(
        optimization_strategy=solver_strategy,
        load_forecast=forecast_values,
        tariff_window=state.get("tariff_window", "OFF_PEAK"),
        battery_soc=state.get("battery_soc", 0.50),
        bess_capacity_kwh=state.get("bess_capacity_kwh", 500.0),
        md_limit_kw=state.get("md_limit_kw", 800.0),
        current_dispatch_index=state.get("current_dispatch_index", 0),
        previous_dispatch_plan=state.get("dispatch_plan"),
    )

    result = solver.solve(input_data)

    dispatch_plan = [asdict(interval) for interval in result.dispatch_plan]
    dispatch_action = asdict(result.dispatch_action)
    forecast_kw = forecast_values[0] if forecast_values else 0.0

    return {
        "dispatch_plan": dispatch_plan,
        "dispatch_action": dispatch_action,
        "current_dispatch_index": result.current_dispatch_index,
        "forecast_kw": forecast_kw,
        "messages": [
            {
                "role": "assistant",
                "content": f"Optimization complete for {facility or 'facility'}; {len(dispatch_plan)} intervals scheduled.",
            }
        ],
    }