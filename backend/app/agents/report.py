"""Report agent - generates final analysis report."""

import datetime

from app.agents.state import AgentState


def report_node(state: AgentState) -> dict:
    """Generate final analysis report.

    Compiles all agent outputs into a comprehensive report
    covering data quality, forecasts, tariff analysis, and optimization.
    """
    loaded_data = state.get("loaded_data") or {}
    data_quality = state.get("data_quality") or {}
    load_forecast = state.get("load_forecast") or {}
    forecast_confidence = state.get("forecast_confidence") or {}
    tariff_window = state.get("tariff_window", "UNKNOWN")
    energy_rate = state.get("energy_rate", 0.0)
    demand_charge = state.get("demand_charge", 0.0)
    optimization_plan = state.get("optimization_plan") or {}
    peak_shave_target = state.get("peak_shave_target", 0.0)
    savings_estimate = state.get("savings_estimate", 0.0)

    facilities = list(loaded_data.keys())

    report_lines = [
        "# GridWise AI - Energy Management Analysis Report",
        "",
        f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Executive Summary",
        f"- Facilities analyzed: {len(facilities)}",
        f"- Current tariff window: {tariff_window}",
        f"- Energy rate: {energy_rate:.2f} sen/kWh",
        f"- Demand charge: {demand_charge:.2f} RM/kW",
        f"- Estimated monthly savings: RM {savings_estimate:.2f}",
        "",
        "## Data Quality",
    ]

    for facility, metrics in data_quality.items():
        report_lines.append(
            f"- {facility}: {metrics.get('rows', 0)} rows, "
            f"{metrics.get('missing_kw_import', 0)} missing kw_import values"
        )

    report_lines.extend(["", "## Load Forecasts"])

    for facility in facilities:
        conf = forecast_confidence.get(facility, 0.0)
        forecast = load_forecast.get(facility, [])
        avg_forecast = sum(forecast) / len(forecast) if forecast else 0.0
        peak_forecast = max(forecast) if forecast else 0.0
        report_lines.append(
            f"- {facility}: avg={avg_forecast:.1f}kW, peak={peak_forecast:.1f}kW, "
            f"confidence={conf:.0%}"
        )

    report_lines.extend(["", "## Optimization Plan"])

    if optimization_plan:
        for facility, plan in optimization_plan.items():
            discharge_count = sum(1 for p in plan if p.get("action") == "discharge")
            charge_count = sum(1 for p in plan if p.get("action") == "charge")
            report_lines.append(
                f"- {facility}: {discharge_count} discharge intervals, {charge_count} charge intervals"
            )
    else:
        report_lines.append("- No optimization plan generated")

    report_lines.extend([
        "",
        "## Peak Shaving Targets",
        f"- Average peak shave target: {peak_shave_target:.1f} kW",
        "",
        "## Recommendations",
        "1. Schedule BESS discharge during PEAK window (2PM-10PM) for maximum MD savings",
        "2. Charge BESS during OFF_PEAK window (10PM-2PM) to minimize energy costs",
        "3. Consider solar PV expansion to further reduce grid import during peak hours",
    ])

    report = "\n".join(report_lines)

    return {
        "report": report,
        "messages": [
            {
                "role": "assistant",
                "content": "Final analysis report generated.",
            }
        ],
    }