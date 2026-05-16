"""Shared state definition for the multi-agent energy management workflow."""

from datetime import datetime
from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import add_messages


# ---------------------------------------------------------------------------
# Value objects — each represents one agent's input/output contract
# ---------------------------------------------------------------------------

class BatteryState(TypedDict, total=False):
    """Physical BESS state owned by the Controller."""
    soc: float
    capacity_kwh: float
    cycle_count: float
    temperature_c: float


class ForecastResult(TypedDict, total=False):
    """Rolling load forecasts produced by the Forecasting agent."""
    load_forecast: dict[str, list[float]]
    confidence: dict[str, float]
    horizon: int


class TariffContext(TypedDict, total=False):
    """TNB tariff classification produced by the Tariff agent."""
    window: str
    energy_rate: float
    demand_charge: float
    tariff_type: str


class DispatchAction(TypedDict, total=False):
    """Dispatch instruction resolved by the Controller (from MILP solver)."""
    action: str
    discharge_kw: float | None
    charge_kw: float | None
    duration_min: int
    expected_soc_after: float | None


class DispatchResult(TypedDict, total=False):
    """Observed outcome after inverter dispatch (from mock_inverter_dispatch)."""
    new_soc: float
    temp_increase_c: float
    cycle_count_delta: float
    action_taken: str
    actual_discharge_kw: float
    efficiency_loss_pct: float


class OptimizationStrategy(TypedDict, total=False):
    """Dispatch strategy selected by the Planner agent."""
    strategy_name: str
    shave_kw: float
    reserve_soc_pct: float
    target_soc_end: float
    rationale: str
    confidence: float
    md_limit_kw: float
    constraints: list


# ---------------------------------------------------------------------------
# Workflow state — composition of value objects + simulation context
# ---------------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    """State carried through the multi-agent workflow."""

    # Simulation context (flat — no natural grouping)
    day_type: str | None
    current_time: datetime | None
    forecast_window: int | None
    current_facility: str | None
    md_limit_kw: float | None
    current_record_index: int | None

    # Raw data (flat — loaded once, referenced by all agents)
    loaded_data: dict | None
    data_quality: dict | None

    # Value objects — one per agent boundary
    battery: BatteryState | None
    forecast: ForecastResult | None
    tariff: TariffContext | None
    optimization_strategy: OptimizationStrategy | None
    dispatch_action: DispatchAction | None
    dispatch_result: DispatchResult | None

    # Operational scalars (Controller writes; Auditor + SimulationService read)
    forecast_kw: float | None
    baseline_load: float | None
    actual_load: float | None
    last_dispatch_kw: float | None
    last_dispatch_duration_min: int | None

    # Auditor accumulation
    auditor_result: dict | None
    decision_log: list[dict] | None
    agent_trace: list[dict] | None
    shave_percentage: float | None
    total_savings_rm: float | None
    within_limit_ticks: int | None
    total_intervals: int | None
    # Workflow metadata
    messages: Annotated[list, add_messages]
    is_end_of_day: bool | None
