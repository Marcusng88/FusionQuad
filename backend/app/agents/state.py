"""Shared state definition for multi-agent energy management workflow."""

from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import add_messages


class AgentState(TypedDict):
    """State carried through the multi-agent workflow.

    Based on plan.md AgentState design from LangGraph section.
    """

    # Data loading
    loaded_data: dict | None  # CSV data per facility
    data_quality: dict | None  # Data quality metrics

    # Forecasting
    load_forecast: list[float] | None  # Predicted load values
    forecast_confidence: float | None  # Model confidence 0-1

    # Tariff analysis
    tariff_window: str | None  # PEAK | OFF_PEAK | WEEKEND
    energy_rate: float | None  # sen/kWh
    demand_charge: float | None  # RM/kW

    # Optimization
    optimization_plan: list[dict] | None  # BESS dispatch schedule
    peak_shave_target: float | None  # kW target reduction

    # Reporting
    report: str | None  # Final analysis report
    savings_estimate: float | None  # RM estimated savings

    # Accumulated messages
    messages: Annotated[list, add_messages]