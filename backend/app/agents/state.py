"""Shared state definition for the multi-agent energy management workflow."""

from datetime import datetime
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import add_messages


class AgentState(TypedDict, total=False):
    """State carried through the multi-agent workflow."""

    # Simulation context
    day_type: str | None
    current_time: datetime | None
    forecast_window: int | None
    current_facility: str | None
    md_limit_kw: float | None

    # Data loading
    loaded_data: dict | None
    data_quality: dict | None

    # Forecasting
    load_forecast: dict[str, list[float]] | None
    forecast_confidence: dict[str, float] | None
    forecast_kw: float | None

    # Tariff analysis
    tariff_window: str | None
    energy_rate: float | None
    demand_charge: float | None
    tariff_type: str | None

    # Planner output
    optimization_strategy: dict | None

    # Optimization output
    dispatch_plan: list[dict] | None
    current_dispatch_index: int | None
    dispatch_action: dict | None

    # Controller inputs/outputs
    battery_soc: float | None
    bess_capacity_kwh: float | None
    cycle_count: float | None
    temperature_c: float | None
    dispatch_result: dict | None
    last_dispatch_kw: float | None
    last_dispatch_duration_min: int | None

    # Load tracking for Auditor
    baseline_load: float | None
    actual_load: float | None

    # Auditor outputs
    auditor_result: dict | None
    decision_log: list[dict] | None
    shave_percentage: float | None
    total_savings_rm: float | None
    within_limit_ticks: int | None
    total_intervals: int | None

    # Deep agent toggle
    use_deep_agent: bool | None

    # Accumulated messages
    messages: Annotated[list, add_messages]