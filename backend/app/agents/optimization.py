"""Optimization agent - generates BESS dispatch and load optimization plan."""

from datetime import datetime

from app.agents.state import AgentState


def optimization_node(state: AgentState) -> dict:
    """Generate BESS dispatch and load optimization plan.

    Uses forecast and tariff data to create optimal dispatch schedule
    targeting peak shaving and cost minimization.
    """
    forecasts = state.get("load_forecast") or {}
    tariff_window = state.get("tariff_window", "OFF_PEAK")
    energy_rate = state.get("energy_rate", 24.43)  # sen/kWh
    demand_rate = state.get("demand_charge", 0.0)  # RM/kW

    optimization_plans = {}
    peak_shave_targets = {}

    for facility, forecast_values in forecasts.items():
        if not forecast_values:
            continue

        # Ensure forecast_values is a list
        if isinstance(forecast_values, (int, float)):
            forecast_values = [forecast_values]

        # Find peak in forecast
        peak_value = max(forecast_values) if forecast_values else 0.0
        avg_value = sum(forecast_values) / len(forecast_values) if forecast_values else 0.0

        # Target: shave peaks to avg + 10%
        target_limit = avg_value * 1.10
        peak_shave_target = max(0.0, peak_value - target_limit)

        # Calculate optimal BESS dispatch
        dispatch_schedule = []
        for i, value in enumerate(forecast_values):
            if value > target_limit:
                shave_needed = value - target_limit
                dispatch_schedule.append({
                    "interval": i,
                    "discharge_kw": min(shave_needed, 100.0),  # Cap at 100kW per interval
                    "action": "discharge",
                })
            elif tariff_window == "OFF_PEAK" and value < avg_value * 0.5:
                # Valley filling opportunity
                dispatch_schedule.append({
                    "interval": i,
                    "charge_kw": 50.0,
                    "action": "charge",
                })

        # Calculate estimated savings
        # MD savings: RM 97.06/kW * peak_shave_target (per month, one spike)
        md_savings = demand_rate * peak_shave_target if tariff_window == "PEAK" else 0.0

        optimization_plans[facility] = dispatch_schedule
        peak_shave_targets[facility] = peak_shave_target

    # Aggregate savings
    total_md_savings = sum(
        demand_rate * target
        for target in peak_shave_targets.values()
        if demand_rate > 0
    )
    total_savings = total_md_savings  # Simplified: MD savings dominate

    return {
        "optimization_plan": optimization_plans,
        "peak_shave_target": sum(peak_shave_targets.values()) / max(1, len(peak_shave_targets)),
        "savings_estimate": total_savings,
        "messages": [
            {
                "role": "assistant",
                "content": (
                    f"Optimization plan generated. "
                    f"Avg peak shave target: {sum(peak_shave_targets.values()) / max(1, len(peak_shave_targets)):.1f} kW. "
                    f"Estimated savings: RM {total_savings:.2f}/month"
                ),
            }
        ],
    }