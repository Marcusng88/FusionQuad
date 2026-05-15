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


class PlaySimulationRequest(BaseModel):
    session_id: str
    interval_ms: int = Field(default=250, ge=1, le=60_000)


class SizingRecommendation(BaseModel):
    recommended_bess_capacity_kwh: float
    recommended_solar_capacity_kwp: float
    estimated_peak_reduction_kw: float
    estimated_monthly_savings_rm: float
    rationale: str


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
    status: Literal["paused", "playing", "completed"]
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
    sizing_recommendation: SizingRecommendation | None = None
    available_start: datetime | None = Field(default=None, description="Available datetime range start from CSV metadata")
    available_end: datetime | None = Field(default=None, description="Available datetime range end from CSV metadata")
    selected_start_time: datetime | None = Field(default=None, description="User-selected window start")
    selected_end_time: datetime | None = Field(default=None, description="User-selected window end")
    scenarios: list[ScenarioMeta] = Field(default_factory=list)
