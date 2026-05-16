from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from math import ceil
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status

from app.agents.data_loader.node import DEFAULT_MD_LIMIT_KW, data_loader_node
from app.agents.state import AgentState, BatteryState
from app.agents.workflow import create_workflow
from app.schemas.simulation import (
    AgentTraceEntry,
    SimulationStateResponse,
    SizingRecommendation,
)


SIMULATION_WINDOW_INTERVALS = 48
FORECAST_WINDOW_INTERVALS = 6
MD_RATE = 97.06

LOGS_DIR = Path(__file__).parent.parent / "logs"

SCENARIO_META = [
    {"key": "weekday", "label": "Weekday Peak", "blurb": "Typical weekday load with the afternoon maximum demand breach."},
    {"key": "holiday", "label": "Holiday Surge", "blurb": "Higher holiday demand with broader peak exposure across the site."},
    {"key": "solar_duck_curve", "label": "Solar Duck Curve", "blurb": "Post-solar ramp where late-afternoon grid import rises into the tariff window."},
    {"key": "large_weekday", "label": "Large Facility", "blurb": "High-load weekday facility (1,000–1,400 kW) with solar, peak hours 8–10 AM and 2–6 PM."},
]


@dataclass
class SimulationSession:
    session_id: str
    day_type: str
    records: list[dict[str, Any]]
    record_offset: int
    state: dict[str, Any]
    status: str = "paused"
    current_interval: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    available_start: datetime | None = None
    available_end: datetime | None = None
    selected_start_time: datetime | None = None
    selected_end_time: datetime | None = None
    log_path: Path | None = None


class SimulationService:
    """Workflow-backed simulation coordinator for the FastAPI endpoints."""

    def __init__(self) -> None:
        self._sessions: dict[str, SimulationSession] = {}
        self._workflow = create_workflow()

    async def start(
        self,
        *,
        day_type: str,
        bess_capacity_kwh: float,
        battery_soc: float = 0.5,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> SimulationStateResponse:
        loaded = data_loader_node({"day_type": day_type})
        current_facility = loaded["current_facility"]
        full_records = list(loaded["loaded_data"][current_facility]["data"])
        metadata = loaded["loaded_data"][current_facility].get("metadata") or {}
        available_start = metadata.get("available_start")
        available_end = metadata.get("available_end")
        if not full_records:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No simulation records available for {day_type}.",
            )

        record_offset, records = self._select_simulation_window(
            full_records,
            start_time=start_time,
            end_time=end_time,
        )
        if not records:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to derive a simulation window for {day_type}.",
            )

        sizing_recommendation = self._build_sizing_recommendation(
            full_records=full_records,
            metadata=metadata,
            md_limit_kw=DEFAULT_MD_LIMIT_KW,
        )

        session_id = str(uuid4())
        state = {
            **loaded,
            "day_type": day_type,
            "current_interval": 0,
            "current_record_index": record_offset,
            "forecast_window": FORECAST_WINDOW_INTERVALS,
            # Battery state as value object
            "battery": BatteryState(
                soc=battery_soc,
                capacity_kwh=bess_capacity_kwh,
                cycle_count=0.0,
                temperature_c=30.0,
            ),
            "decision_log": [],
            "agent_trace": [],
            "total_savings_rm": 0.0,
            "within_limit_ticks": 0,
            "total_intervals": len(records),
            "shave_percentage": 0.0,
            "forecast_kw": None,
            "baseline_load": None,
            "actual_load": None,
            "tariff": None,
            "messages": [],
            "sizing_recommendation": sizing_recommendation,
        }

        date_str = (start_time or datetime.now()).strftime("%Y-%m-%d")
        log_path = LOGS_DIR / f"{date_str}-{day_type}.json"
        session = SimulationSession(
            session_id=session_id,
            day_type=day_type,
            records=records,
            record_offset=record_offset,
            state=state,
            available_start=available_start,
            available_end=available_end,
            selected_start_time=start_time,
            selected_end_time=end_time,
            log_path=log_path,
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
            current_time = _coerce_datetime(record.get("datetime"))
            baseline_load = float(record.get("kw_import", 0.0) or 0.0)
            absolute_index = session.record_offset + session.current_interval

            is_last_tick = session.current_interval + 1 >= len(session.records)
            state = {
                **session.state,
                "current_interval": session.current_interval,
                "current_record_index": absolute_index,
                "current_time": current_time,
                "baseline_load": baseline_load,
                "actual_load": baseline_load,
                "forecast_window": min(
                    FORECAST_WINDOW_INTERVALS,
                    max(len(session.records) - session.current_interval, 1),
                ),
                "is_end_of_day": is_last_tick,
            }

            result = self._workflow.invoke(
                state,
                config={"configurable": {"thread_id": session.session_id}},
            )

            agent_trace = list(session.state.get("agent_trace", []))
            agent_trace.extend(_build_agent_trace_entries(result))
            result["agent_trace"] = agent_trace

            session.state = result
            session.current_interval += 1
            session.state["current_interval"] = session.current_interval
            session.state["current_record_index"] = absolute_index

            self._append_tick_log(session, result, current_time)

            if session.current_interval >= len(session.records):
                session.status = "completed"
                self._finalize_log(session)

            return self._build_snapshot(session)

    async def run(self, session_id: str) -> SimulationStateResponse:
        while True:
            snapshot = await self.step(session_id)
            if snapshot.status == "completed":
                return snapshot

    async def get_state(self, session_id: str) -> SimulationStateResponse:
        return self._build_snapshot(self._get_session(session_id))

    async def shutdown(self) -> None:
        pass

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
        sizing = state.get("sizing_recommendation")
        agent_trace = [AgentTraceEntry.model_validate(entry) for entry in state.get("agent_trace", [])]

        battery = state.get("battery") or {}
        tariff = state.get("tariff") or {}

        return SimulationStateResponse(
            session_id=session.session_id,
            status=session.status,
            day_type=session.day_type,
            current_interval=session.current_interval,
            total_intervals=len(session.records),
            current_time=state.get("current_time"),
            battery_soc=float(battery.get("soc", 0.5) or 0.5),
            bess_capacity_kwh=float(battery.get("capacity_kwh", 500.0) or 500.0),
            baseline_load=_coerce_optional_float(state.get("baseline_load")),
            actual_load=_coerce_optional_float(state.get("actual_load")),
            forecast_kw=_coerce_optional_float(state.get("forecast_kw")),
            tariff_window=tariff.get("window"),
            total_savings_rm=float(state.get("total_savings_rm", 0.0) or 0.0),
            shave_percentage=float(state.get("shave_percentage", 0.0) or 0.0),
            within_limit_ticks=int(state.get("within_limit_ticks", 0) or 0),
            decision_log=list(state.get("decision_log", [])),
            agent_trace=agent_trace,
            last_dispatch_kw=float(state.get("last_dispatch_kw", 0.0) or 0.0),
            md_limit_kw=float(state.get("md_limit_kw", DEFAULT_MD_LIMIT_KW) or DEFAULT_MD_LIMIT_KW),
            md_rate=MD_RATE,
            dispatch_action=state.get("dispatch_action"),
            sizing_recommendation=(
                SizingRecommendation.model_validate(sizing) if isinstance(sizing, dict) else None
            ),
            available_start=session.available_start,
            available_end=session.available_end,
            selected_start_time=session.selected_start_time,
            selected_end_time=session.selected_end_time,
            scenarios=SCENARIO_META,
        )

    # ------------------------------------------------------------------
    # Execution Logging
    # ------------------------------------------------------------------

    def _append_tick_log(self, session: SimulationSession, result: dict, current_time: datetime | None) -> None:
        if session.log_path is None:
            return
        import json
        session_dir = session.log_path.parent
        session_dir.mkdir(parents=True, exist_ok=True)

        forecast = result.get("forecast") or {}
        forecast_conf = forecast.get("confidence") or {}
        first_conf = float(next(iter(forecast_conf.values()), 0.0)) if forecast_conf else 0.0

        tick_data = {
            "tick": session.current_interval,
            "datetime": (current_time or datetime.now()).strftime("%Y-%m-%dT%H:%M:%S") if current_time else None,
            "forecast_kw": _coerce_optional_float(result.get("forecast_kw")),
            "forecast_confidence": first_conf,
            "tariff_window": (result.get("tariff") or {}).get("window"),
            "optimization_strategy": result.get("optimization_strategy"),
            "dispatch_action": result.get("dispatch_action"),
            "dispatch_result": result.get("dispatch_result"),
            "actual_load_kw": _coerce_optional_float(result.get("actual_load")),
            "within_limit": bool(
                _coerce_optional_float(result.get("actual_load")) is not None
                and _coerce_optional_float(result.get("actual_load")) <= session.state.get("md_limit_kw", 800.0)
            ),
            "savings_rm": _coerce_optional_float(
                (result.get("auditor_result") or {}).get("delta_eval", {}).get("interval_savings_rm")
            ),
        }

        if session.log_path.exists():
            with open(session.log_path) as f:
                log = json.load(f)
        else:
            log = {"ticks": [], "summary": {}}

        log["ticks"].append(tick_data)
        with open(session.log_path, "w") as f:
            json.dump(log, f, indent=2)

    def _finalize_log(self, session: SimulationSession) -> None:
        if session.log_path is None:
            return
        import json
        if not session.log_path.exists():
            return
        with open(session.log_path) as f:
            log = json.load(f)

        state = session.state
        battery = state.get("battery") or {}
        within_limit = int(state.get("within_limit_ticks", 0))
        total = int(state.get("total_intervals", 0)) or len(log["ticks"])
        decision_log = state.get("decision_log", [])
        last_auditor = decision_log[-1] if decision_log else {}

        log["summary"] = {
            "total_ticks": total,
            "within_limit_ticks": within_limit,
            "total_savings_rm": float(state.get("total_savings_rm", 0.0)),
            "compliance_rate": round(within_limit / total, 4) if total > 0 else 0.0,
            "shave_percentage": float(state.get("shave_percentage", 0.0)),
            "final_soc_percent": int((float(battery.get("soc", 0.5)) or 0.5) * 100),
        }

        date_str = (session.available_start or datetime.now()).strftime("%Y-%m-%d")
        experience_path = Path(__file__).parent.parent / "experience" / f"{date_str}-{session.day_type}.md"
        if experience_path.exists():
            with open(experience_path) as f:
                log["audit_report"] = f.read()
        else:
            log["audit_report"] = last_auditor.get("reason", "") or "No experience report available."

        with open(session.log_path, "w") as f:
            json.dump(log, f, indent=2)

    # ------------------------------------------------------------------

    @staticmethod
    def _build_sizing_recommendation(
        *,
        full_records: list[dict[str, Any]],
        metadata: dict[str, Any],
        md_limit_kw: float,
    ) -> dict[str, Any]:
        loads = [float(item.get("kw_import", 0.0) or 0.0) for item in full_records]
        max_breach = max((max(load - md_limit_kw, 0.0) for load in loads), default=0.0)

        longest_energy_kwh = 0.0
        current_energy_kwh = 0.0
        for load in loads:
            breach = max(load - md_limit_kw, 0.0)
            if breach > 0:
                current_energy_kwh += breach * 0.5
                longest_energy_kwh = max(longest_energy_kwh, current_energy_kwh)
            else:
                current_energy_kwh = 0.0

        raw_bess_kwh = max(300.0, longest_energy_kwh * 1.15)
        recommended_bess = float(min(2000, max(300, ceil(raw_bess_kwh / 100) * 100)))

        solar_installed = float(metadata.get("solar_installed_kwp") or 0.0)
        daytime_loads = loads[20:32] if len(loads) >= 32 else loads
        daytime_target = max(daytime_loads, default=0.0) * 0.35
        recommended_solar = solar_installed if solar_installed > 0 else float(ceil(daytime_target / 50) * 50 if daytime_target > 0 else 0.0)

        estimated_peak_reduction = round(min(max_breach, recommended_bess / 5), 1)
        estimated_monthly_savings = round(estimated_peak_reduction * MD_RATE, 2)

        if solar_installed > 0:
            rationale = (
                f"Existing solar of {solar_installed:.0f} kWp already offsets part of the daytime load; "
                f"the recommended {recommended_bess:.0f} kWh BESS is sized around the longest MD breach window."
            )
        else:
            rationale = (
                f"Recommend {recommended_solar:.0f} kWp solar to offset daytime import and "
                f"{recommended_bess:.0f} kWh BESS to cover the longest breach streak above {md_limit_kw:.0f} kW."
            )

        return {
            "recommended_bess_capacity_kwh": recommended_bess,
            "recommended_solar_capacity_kwp": recommended_solar,
            "estimated_peak_reduction_kw": estimated_peak_reduction,
            "estimated_monthly_savings_rm": estimated_monthly_savings,
            "rationale": rationale,
        }

    @staticmethod
    def _select_simulation_window(
        full_records: list[dict[str, Any]],
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        if start_time is not None or end_time is not None:
            return _ticks_in_window(full_records, start_time, end_time)

        if len(full_records) <= SIMULATION_WINDOW_INTERVALS:
            return 0, full_records

        best_start = 0
        best_score = float("-inf")
        max_start = len(full_records) - SIMULATION_WINDOW_INTERVALS
        preferred_start = min(48, max_start)

        for start in range(preferred_start, max_start + 1):
            window = full_records[start : start + SIMULATION_WINDOW_INTERVALS]
            loads = [float(item.get("kw_import", 0.0) or 0.0) for item in window]
            score = max(loads, default=0.0) + sum(max(load - DEFAULT_MD_LIMIT_KW, 0.0) for load in loads) * 0.1
            if score > best_score:
                best_score = score
                best_start = start

        return best_start, full_records[best_start : best_start + SIMULATION_WINDOW_INTERVALS]


def _ticks_in_window(
    full_records: list[dict[str, Any]],
    start_time: datetime | None,
    end_time: datetime | None,
) -> tuple[int, list[dict[str, Any]]]:
    if not full_records:
        return 0, []

    if start_time is None and end_time is None:
        return 0, full_records

    records_with_index = list(enumerate(full_records))

    if start_time is not None:
        records_with_index = [
            (i, r) for i, r in records_with_index
            if _record_datetime(r) >= start_time
        ]

    if end_time is not None:
        records_with_index = [
            (i, r) for i, r in records_with_index
            if _record_datetime(r) <= end_time
        ]

    if not records_with_index:
        return 0, []

    offset = records_with_index[0][0]
    records = [r for _, r in records_with_index]
    return offset, records


def _record_datetime(record: dict[str, Any]) -> datetime:
    value = record.get("datetime")
    if isinstance(value, datetime):
        return value
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            pass
    return datetime.min


def _coerce_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


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


def _build_agent_trace_entries(state: dict[str, Any]) -> list[dict[str, Any]]:
    ts = state.get("current_time")
    timestamp_str = ts.strftime("%Y-%m-%d %H:%M") if isinstance(ts, datetime) else str(ts or "")

    forecast = state.get("forecast") or {}
    forecast_values = _first_forecast_values(forecast)
    forecast_conf = _first_forecast_confidence(forecast)

    strategy = state.get("optimization_strategy") or {}
    dispatch_result = state.get("dispatch_result") or {}
    auditor_result = state.get("auditor_result") or {}
    delta_eval = auditor_result.get("delta_eval") or {}
    latest_auditor = (state.get("decision_log") or [{}])[-1]
    battery = state.get("battery") or {}

    return [
        {
            "timestamp": timestamp_str,
            "agent": "Forecasting Agent",
            "decision": f"Forecast next {len(forecast_values)} intervals",
            "reason": f"Rolling GRU forecast generated with confidence {forecast_conf:.0%}.",
            "action": (
                f"Predicted next import at {state.get('forecast_kw', 0.0):.0f} kW"
                if state.get("forecast_kw") is not None
                else "Forecast unavailable"
            ),
        },
        {
            "timestamp": timestamp_str,
            "agent": "Planner Agent",
            "decision": str(strategy.get("strategy_name") or "Select safe fallback strategy"),
            "reason": str(strategy.get("rationale") or "Planner used the current tariff window, forecast, and BESS state."),
            "action": (
                f"Target shave {float(strategy.get('shave_kw', 0.0) or 0.0):.0f} kW with reserve "
                f"{float(strategy.get('reserve_soc_pct', 0.0) or 0.0):.0%}."
            ),
            "expected_reduction_kw": _optional_float(strategy.get("shave_kw")),
        },
        {
            "timestamp": timestamp_str,
            "agent": "Controller Agent",
            "decision": f"Executed {str(dispatch_result.get('action_taken', 'hold'))}",
            "reason": f"Battery SoC moved to {float(battery.get('soc', 0.0) or 0.0):.0%}.",
            "action": (
                f"Grid import adjusted to {float(state.get('actual_load', 0.0) or 0.0):.0f} kW "
                f"with {float(state.get('last_dispatch_kw', 0.0) or 0.0):.0f} kW battery power."
            ),
        },
        {
            "timestamp": timestamp_str,
            "agent": "Auditor Agent",
            "decision": str(latest_auditor.get("perceive") or "Audit completed."),
            "reason": str(latest_auditor.get("reason") or "Auditor verified the dispatch result."),
            "action": str(latest_auditor.get("act") or "No action recorded."),
            "expected_reduction_kw": _optional_float(delta_eval.get("shave_kw")),
            "estimated_saving_rm": _optional_float(delta_eval.get("interval_savings_rm")),
        },
    ]


def _first_forecast_values(forecast: dict[str, Any]) -> list[float]:
    load_forecast = forecast.get("load_forecast") or {}
    if not load_forecast:
        return []
    first = next(iter(load_forecast.values()))
    return [float(item) for item in first]


def _first_forecast_confidence(forecast: dict[str, Any]) -> float:
    confidence = forecast.get("confidence") or {}
    if not confidence:
        return 0.0
    return float(next(iter(confidence.values())))


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
