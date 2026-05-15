from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status

from app.agents.auditor.agent import auditor_node
from app.agents.controller.node import controller_node
from app.agents.data_loader.node import data_loader_node
from app.agents.optimization import optimization_node
from app.agents.planner.node import planner_node
from app.agents.tariff.node import TariffNode
from app.schemas.simulation import SimulationStateResponse


@dataclass
class SimulationSession:
    session_id: str
    day_type: str
    records: list[dict[str, Any]]
    state: dict[str, Any]
    status: str = "paused"
    current_interval: int = 0
    task: asyncio.Task[None] | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class SimulationService:
    """In-memory simulation coordinator for the FastAPI endpoints."""

    def __init__(self) -> None:
        self._sessions: dict[str, SimulationSession] = {}
        self._tariff_node = TariffNode()

    async def start(
        self,
        *,
        day_type: str,
        bess_capacity_kwh: float,
        battery_soc: float = 0.5,
        use_deep_agent: bool = False,
    ) -> SimulationStateResponse:
        loaded = data_loader_node({"day_type": day_type})
        current_facility = loaded["current_facility"]
        records = list(loaded["loaded_data"][current_facility]["data"])
        if not records:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No simulation records available for {day_type}.",
            )

        session_id = str(uuid4())
        state = {
            **loaded,
            "day_type": day_type,
            "current_interval": 0,
            "current_dispatch_index": 0,
            "battery_soc": battery_soc,
            "bess_capacity_kwh": bess_capacity_kwh,
            "cycle_count": 0.0,
            "temperature_c": 30.0,
            "decision_log": [],
            "total_savings_rm": 0.0,
            "within_limit_ticks": 0,
            "total_intervals": len(records),
            "shave_percentage": 0.0,
            "forecast_kw": None,
            "baseline_load": None,
            "actual_load": None,
            "tariff_window": None,
            "use_deep_agent": use_deep_agent,
            "messages": [],
        }

        session = SimulationSession(
            session_id=session_id,
            day_type=day_type,
            records=records,
            state=state,
        )
        self._sessions[session_id] = session
        return self._build_snapshot(session)

    async def step(self, session_id: str) -> SimulationStateResponse:
        session = self._get_session(session_id)
        async with session.lock:
            if session.current_interval >= len(session.records):
                session.status = "completed"
                return self._build_snapshot(session)

            record = session.records[session.current_interval]
            current_time = self._coerce_datetime(record.get("datetime"))
            baseline_load = float(record.get("kw_import", 0.0) or 0.0)

            state = session.state
            state["current_interval"] = session.current_interval
            state["current_time"] = current_time
            state["baseline_load"] = baseline_load
            state["actual_load"] = baseline_load

            state.update(self._tariff_node.invoke(state))

            forecast_values = self._build_forecast(session.records, session.current_interval)
            state["load_forecast"] = {session.day_type: forecast_values}
            state["forecast_confidence"] = {session.day_type: 0.8}
            state["forecast_kw"] = forecast_values[0] if forecast_values else baseline_load

            state.update(planner_node(state))
            state.update(optimization_node(state))
            state.update(controller_node(state))
            state.update(auditor_node(state))

            session.current_interval += 1
            state["current_interval"] = session.current_interval

            if session.current_interval >= len(session.records):
                session.status = "completed"

            return self._build_snapshot(session)

    async def play(self, session_id: str, *, interval_seconds: float) -> SimulationStateResponse:
        session = self._get_session(session_id)
        async with session.lock:
            if session.status == "completed":
                return self._build_snapshot(session)
            if session.task and not session.task.done():
                session.status = "playing"
                return self._build_snapshot(session)

            session.status = "playing"
            session.task = asyncio.create_task(self._autoplay(session_id, interval_seconds))
            return self._build_snapshot(session)

    async def pause(self, session_id: str) -> SimulationStateResponse:
        session = self._get_session(session_id)
        async with session.lock:
            if session.status != "completed":
                session.status = "paused"
            task = session.task
            session.task = None

        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        return self._build_snapshot(session)

    async def get_state(self, session_id: str) -> SimulationStateResponse:
        return self._build_snapshot(self._get_session(session_id))

    async def shutdown(self) -> None:
        tasks = [session.task for session in self._sessions.values() if session.task and not session.task.done()]
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _autoplay(self, session_id: str, interval_seconds: float) -> None:
        try:
            while True:
                snapshot = await self.step(session_id)
                if snapshot.status == "completed":
                    return

                session = self._get_session(session_id)
                if session.status != "playing":
                    return

                await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            raise
        finally:
            session = self._sessions.get(session_id)
            if session and session.status == "playing" and session.current_interval < len(session.records):
                session.status = "paused"

    def _get_session(self, session_id: str) -> SimulationSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Simulation session '{session_id}' was not found.",
            )
        return session

    def _build_snapshot(self, session: SimulationSession) -> SimulationStateResponse:
        state = session.state
        return SimulationStateResponse(
            session_id=session.session_id,
            status=session.status,
            day_type=session.day_type,
            current_interval=session.current_interval,
            total_intervals=len(session.records),
            current_time=state.get("current_time"),
            battery_soc=float(state.get("battery_soc", 0.5) or 0.5),
            bess_capacity_kwh=float(state.get("bess_capacity_kwh", 500.0) or 500.0),
            baseline_load=self._coerce_optional_float(state.get("baseline_load")),
            actual_load=self._coerce_optional_float(state.get("actual_load")),
            forecast_kw=self._coerce_optional_float(state.get("forecast_kw")),
            tariff_window=state.get("tariff_window"),
            total_savings_rm=float(state.get("total_savings_rm", 0.0) or 0.0),
            shave_percentage=float(state.get("shave_percentage", 0.0) or 0.0),
            within_limit_ticks=int(state.get("within_limit_ticks", 0) or 0),
            decision_log=list(state.get("decision_log", [])),
        )

    @staticmethod
    def _build_forecast(records: list[dict[str, Any]], start_index: int, horizon: int = 48) -> list[float]:
        window = records[start_index : start_index + horizon]
        values = [float(item.get("kw_import", 0.0) or 0.0) for item in window]
        return values or [0.0]

    @staticmethod
    def _coerce_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if hasattr(value, "to_pydatetime"):
            return value.to_pydatetime()
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _coerce_optional_float(value: Any) -> float | None:
        if value is None:
            return None
        return float(value)
