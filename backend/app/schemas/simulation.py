from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class StartSimulationRequest(BaseModel):
    day_type: Literal["weekday", "holiday", "solar_duck_curve"] = "weekday"
    bess_capacity_kwh: float = Field(default=500.0, gt=0)
    battery_soc: float = Field(default=0.5, ge=0.0, le=1.0)
    use_deep_agent: bool = False


class SimulationSessionRequest(BaseModel):
    session_id: str


class PlaySimulationRequest(BaseModel):
    session_id: str
    interval_ms: int = Field(default=250, ge=1, le=60_000)


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
