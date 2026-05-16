from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class StartSimulationRequest(BaseModel):
    day_type: Literal["weekday", "holiday", "solar_duck_curve", "large_weekday"] = "weekday"
    bess_capacity_kwh: float = Field(default=500.0, gt=0)
    battery_soc: float = Field(default=0.5, ge=0.0, le=1.0)
    start_time: datetime | None = Field(default=None, description="Optional tick window start — must fall within CSV datetime range")
    end_time: datetime | None = Field(default=None, description="Optional tick window end — must fall within CSV datetime range")


class SimulationSessionRequest(BaseModel):
    session_id: str



class ScenarioMetadataResponse(BaseModel):
    day_type: str
    available_start: datetime
    available_end: datetime
    facility_name: str
    solar_installed_kwp: float
    total_rows: int


class AgentTraceEntry(BaseModel):
    timestamp: str
    agent: str
    decision: str
    reason: str
    action: str
    expected_reduction_kw: float | None = None
    estimated_saving_rm: float | None = None


class ScenarioMeta(BaseModel):
    key: str
    label: str
    blurb: str


class SimulationStateResponse(BaseModel):
    session_id: str
    status: Literal["paused", "completed"]
    day_type: str
    current_interval: int
    total_intervals: int
    current_time: datetime | None
    battery_soc: float
    bess_capacity_kwh: float
    baseline_load: float | None
    actual_load: float | None
    forecast_kw: float | None
    tariff_window: str | None
    total_savings_rm: float
    shave_percentage: float
    within_limit_ticks: int
    decision_log: list[dict[str, Any]]
    agent_trace: list[AgentTraceEntry] = Field(default_factory=list)
    last_dispatch_kw: float = 0.0
    md_limit_kw: float = 800.0
    md_rate: float = 97.06
    dispatch_action: dict[str, Any] | None = None
    scenarios: list[ScenarioMeta] = Field(default_factory=list)
