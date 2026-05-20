from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status

from app.agents.auditor.agent import run_eod_audit
from app.agents.data_loader.node import DEFAULT_MD_LIMIT_KW, data_loader_node
from app.agents.state import BatteryState
from app.agents.workflow import create_workflow
from app.schemas.simulation import (
    AgentTraceEntry,
    ScenarioMetadataResponse,
    SimulationStateResponse,
)
from app.services.tick_logger import TickLogger


SIMULATION_WINDOW_INTERVALS = 48
FORECAST_WINDOW_INTERVALS = 6
MD_RATE = 97.06

LOGS_DIR = Path(__file__).parent.parent / "logs"

SCENARIO_META = [
    {"key": "weekday", "label": "Load Profile (No Solar) E", "blurb": "Typical weekday load with the afternoon maximum demand breach."},
    {"key": "holiday", "label": "Load Profile (No Solar) SuN", "blurb": "Higher holiday demand with broader peak exposure across the site."},
    {"key": "solar_duck_curve", "label": "Load Profile (With Solar Installed) SoL", "blurb": "Post-solar ramp where late-afternoon grid import rises into the tariff window."},
    {"key": "large_weekday", "label": "Load Profile (With Solar) Mi2", "blurb": "High-load weekday facility (1,000–1,400 kW) with solar, peak hours 8–10 AM and 2–6 PM."},
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
    tick_buffer: list[dict[str, Any]] = field(default_factory=list)


_MAX_SESSIONS = 50


class SimulationService:
    """Workflow-backed simulation coordinator for the FastAPI endpoints."""

    def __init__(self) -> None:
        self._sessions: dict[str, SimulationSession] = {}
        self._workflow = create_workflow()
        self._tick_logger = TickLogger()

    def _evict_completed_sessions(self) -> None:
        if len(self._sessions) < _MAX_SESSIONS:
            return
        for sid in [s for s, v in self._sessions.items() if v.status == "completed"]:
            del self._sessions[sid]

    async def start(
        self,
        *,
        day_type: str,
        bess_capacity_kwh: float,
        battery_soc: float = 0.5,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        forecast_model: str = "gru_attention",
        md_limit_kw: float = 800.0,
        max_discharge_kw: float | None = None,
    ) -> SimulationStateResponse:
        self._evict_completed_sessions()
        loop = asyncio.get_running_loop()
        loaded = await loop.run_in_executor(None, data_loader_node, {"day_type": day_type})
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
        if not records and (start_time is not None or end_time is not None):
            import logging as _log
            _log.getLogger(__name__).warning(
                "simulation | no records in user-selected range [%s, %s] for %s — falling back to auto-window",
                start_time, end_time, day_type,
            )
            record_offset, records = self._select_simulation_window(full_records)
        if not records:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unable to derive a simulation window for {day_type}.",
            )

        session_id = str(uuid4())
        state = {
            **loaded,
            "session_id": session_id,
            "day_type": day_type,
            "md_limit_kw": md_limit_kw,
            "max_discharge_kw": max_discharge_kw if max_discharge_kw is not None else bess_capacity_kwh,
            "current_interval": 0,
            "current_record_index": record_offset,
            "forecast_window": FORECAST_WINDOW_INTERVALS,
            "forecast_model": forecast_model,
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
            "peak_ticks": 0,
            "peak_reduction_kw": 0.0,
            "total_intervals": len(records),
            "shave_percentage": 0.0,
            "total_possible_shave_kw": 0.0,
            "forecast_kw": None,
            "baseline_load": None,
            "actual_load": None,
            "tariff": None,
            "messages": [],
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

            result = await self._workflow.ainvoke(state)

            agent_trace = list(session.state.get("agent_trace", []))
            agent_trace.extend(_build_agent_trace_entries(result))
            result["agent_trace"] = agent_trace

            session.state = result
            session.current_interval += 1
            session.state["current_interval"] = session.current_interval
            session.state["current_record_index"] = absolute_index

            if session.log_path is not None:
                self._tick_logger.append_tick(
                    session.tick_buffer,
                    session.current_interval - 1,
                    result,
                    current_time,
                    float(result.get("md_limit_kw", 800.0)),
                )

            if session.current_interval >= len(session.records):
                session.status = "completed"
                if session.log_path is not None:
                    self._tick_logger.finalize(
                        session.log_path,
                        session.tick_buffer,
                        session.state,
                        session.available_start,
                        session.day_type,
                    )
                    date_str = (session.selected_start_time or session.available_start or datetime.now()).strftime("%Y-%m-%d")
                    try:
                        await run_eod_audit(session.log_path, session.day_type, date_str)
                    except Exception:
                        import logging as _log
                        _log.getLogger(__name__).exception("auditor | EOD audit failed for %s %s", date_str, session.day_type)

            return self._build_snapshot(session)

    async def run(self, session_id: str) -> SimulationStateResponse:
        while True:
            snapshot = await self.step(session_id)
            if snapshot.status == "completed":
                return snapshot

    async def run_stream(self, session_id: str):
        """Async generator yielding SSE-ready dicts for a full simulation run."""
        _SKIP_NODES = {"data_loader"}
        session = self._get_session(session_id)

        try:
            while True:
                if session.current_interval >= len(session.records):
                    session.status = "completed"
                    yield {"event": "simulation_done", "data": {"status": "completed"}}
                    return

                # Build tick state under lock (fast — no IO)
                async with session.lock:
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
                    snapshot_state_ref = session.state  # for preview merging

                # Run workflow OUTSIDE lock — LLM calls can take seconds.
                # Yield agent_token events immediately for live streaming.
                # Yield agent_update/agent_start/agent_complete during astream.
                # Only step_complete waits for the post-tick lock.
                final_state: dict | None = None
                seen_streaming_nodes: set[str] = set()
                timestamp_str = (
                    current_time.strftime("%Y-%m-%d %H:%M")
                    if current_time is not None
                    else ""
                )

                async for chunk in self._workflow.astream(
                    state,
                    stream_mode=["updates", "values", "messages"],
                    version="v2",
                ):
                    if chunk["type"] == "messages":
                        msg, metadata = chunk["data"]
                        node_name = metadata.get("langgraph_node", "unknown")
                        # Only stream AI output tokens (skip tool messages, human messages)
                        msg_type = getattr(msg, "type", "")
                        if msg_type not in ("ai", "AIMessageChunk"):
                            # Check class name as fallback
                            cls_name = type(msg).__name__
                            if "AI" not in cls_name and "Assistant" not in cls_name:
                                continue
                        raw_content = getattr(msg, "content", None)
                        # Normalize content: list of blocks → plain string
                        if isinstance(raw_content, list):
                            token_text = "".join(
                                block.get("text", "") if isinstance(block, dict) else str(block)
                                for block in raw_content
                            )
                        elif isinstance(raw_content, str):
                            token_text = raw_content
                        else:
                            token_text = ""
                        if token_text and node_name not in _SKIP_NODES:
                            if node_name not in seen_streaming_nodes:
                                seen_streaming_nodes.add(node_name)
                                yield {
                                    "event": "agent_start",
                                    "data": {
                                        "node": node_name,
                                        "timestamp": timestamp_str,
                                    },
                                }
                            yield {
                                "event": "agent_token",
                                "data": {
                                    "node": node_name,
                                    "token": token_text,
                                },
                            }

                    elif chunk["type"] == "updates":
                        for node_name, node_state in chunk["data"].items():
                            if node_name in _SKIP_NODES:
                                continue
                            preview_state = {**snapshot_state_ref, **node_state}
                            preview_snapshot = self._build_snapshot_with_state(
                                session,
                                preview_state,
                            )
                            trace_entry = _build_live_trace_entry(node_name, preview_state)
                            yield {
                                "event": "agent_update",
                                "data": {
                                    "node": node_name,
                                    "state": node_state,
                                    "snapshot": preview_snapshot.model_dump(mode="json"),
                                    "trace": trace_entry,
                                },
                            }
                            # Agents using deepagents.ainvoke() never stream tokens to the
                            # outer LangGraph astream, so synthesize start/token/complete here.
                            if node_name not in seen_streaming_nodes:
                                token_json = _extract_node_token(node_name, node_state)
                                if token_json:
                                    seen_streaming_nodes.add(node_name)
                                    yield {
                                        "event": "agent_start",
                                        "data": {
                                            "node": node_name,
                                            "timestamp": timestamp_str,
                                        },
                                    }
                                    yield {
                                        "event": "agent_token",
                                        "data": {
                                            "node": node_name,
                                            "token": token_json,
                                        },
                                    }
                            if node_name in seen_streaming_nodes:
                                yield {
                                    "event": "agent_complete",
                                    "data": {
                                        "node": node_name,
                                        "trace": trace_entry,
                                    },
                                }

                    elif chunk["type"] == "values":
                        final_state = chunk["data"]

                if final_state is None:
                    raise RuntimeError("astream ended without values chunk")

                # Update session state under lock (fast — no IO)
                async with session.lock:
                    agent_trace = list(session.state.get("agent_trace", []))
                    agent_trace.extend(_build_agent_trace_entries(final_state))
                    final_state["agent_trace"] = agent_trace

                    session.state = final_state
                    session.current_interval += 1
                    session.state["current_interval"] = session.current_interval
                    session.state["current_record_index"] = absolute_index

                    if session.log_path is not None:
                        self._tick_logger.append_tick(
                            session.tick_buffer,
                            session.current_interval - 1,
                            final_state,
                            current_time,
                            float(final_state.get("md_limit_kw", 800.0)),
                        )

                    if session.current_interval >= len(session.records):
                        session.status = "completed"
                        if session.log_path is not None:
                            self._tick_logger.finalize(
                                session.log_path,
                                session.tick_buffer,
                                session.state,
                                session.available_start,
                                session.day_type,
                            )
                            date_str = (session.selected_start_time or session.available_start or datetime.now()).strftime("%Y-%m-%d")
                            try:
                                await run_eod_audit(session.log_path, session.day_type, date_str)
                            except Exception:
                                import logging as _log
                                _log.getLogger(__name__).exception("auditor | EOD audit failed for %s %s", date_str, session.day_type)

                    snapshot = self._build_snapshot(session)

                yield {"event": "step_complete", "data": snapshot.model_dump(mode="json")}

        except Exception as exc:
            yield {"event": "error", "data": {"message": str(exc)}}

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
        return self._build_snapshot_with_state(session, session.state)

    def _build_snapshot_with_state(
        self,
        session: SimulationSession,
        state: dict[str, Any],
    ) -> SimulationStateResponse:
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
            peak_ticks=int(state.get("peak_ticks", 0) or 0),
            avg_peak_reduction_kw=round(
                float(state.get("peak_reduction_kw", 0.0) or 0.0)
                / max(int(state.get("peak_ticks", 0) or 0), 1),
                2,
            ),
            decision_log=list(state.get("decision_log", [])),
            agent_trace=agent_trace,
            last_dispatch_kw=float(state.get("last_dispatch_kw", 0.0) or 0.0),
            md_limit_kw=float(state.get("md_limit_kw", DEFAULT_MD_LIMIT_KW) or DEFAULT_MD_LIMIT_KW),
            md_rate=MD_RATE,
            dispatch_action=state.get("dispatch_action"),
            scenarios=SCENARIO_META,
        )

    async def get_scenario_metadata(self, day_type: str) -> ScenarioMetadataResponse:
        loop = asyncio.get_running_loop()
        loaded = await loop.run_in_executor(None, data_loader_node, {"day_type": day_type})
        current_facility = loaded["current_facility"]
        metadata = loaded["loaded_data"][current_facility].get("metadata") or {}
        data_quality = loaded["data_quality"].get(current_facility) or {}
        return ScenarioMetadataResponse(
            day_type=day_type,
            available_start=metadata["available_start"],
            available_end=metadata["available_end"],
            facility_name=metadata.get("facility_name", ""),
            solar_installed_kwp=float(metadata.get("solar_installed_kwp", 0.0)),
            total_rows=int(data_quality.get("rows", 0)),
        )

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


def _build_live_trace_entry(node_name: str, state: dict[str, Any]) -> dict[str, Any] | None:
    timestamp = state.get("current_time")
    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M") if isinstance(timestamp, datetime) else str(timestamp or "")

    if node_name == "forecast":
        forecast = state.get("forecast") or {}
        forecast_values = _first_forecast_values(forecast)
        forecast_conf = _first_forecast_confidence(forecast)
        forecast_kw = forecast_values[0] if forecast_values else state.get("forecast_kw")
        return {
            "timestamp": timestamp_str,
            "agent": "Forecasting Agent",
            "decision": f"Forecast next {len(forecast_values)} intervals",
            "reason": f"Rolling forecast confidence {forecast_conf:.0%}.",
            "action": (
                f"Predicted next import at {float(forecast_kw or 0.0):.0f} kW"
                if forecast_kw is not None
                else "Forecast unavailable"
            ),
        }

    if node_name == "planner":
        strategy = state.get("optimization_strategy") or {}
        reserve = float(strategy.get("reserve_soc_pct", 0.0) or 0.0)
        return {
            "timestamp": timestamp_str,
            "agent": "Planner Agent",
            "decision": str(strategy.get("strategy_name") or "Select fallback strategy"),
            "reason": str(strategy.get("rationale") or "Planner evaluated tariff and forecast."),
            "action": (
                f"Target shave {float(strategy.get('shave_kw', 0.0) or 0.0):.0f} kW with reserve {reserve:.0%}."
            ),
            "expected_reduction_kw": _optional_float(strategy.get("shave_kw")),
        }

    if node_name == "controller":
        dispatch_action = state.get("dispatch_action") or {}
        dispatch_result = state.get("dispatch_result") or {}
        battery = state.get("battery") or {}
        action_taken = dispatch_result.get("action_taken", dispatch_action.get("action", "hold"))
        actual_kw = float(dispatch_result.get("actual_discharge_kw", 0.0) or 0.0)
        soc = float(battery.get("soc", 0.0) or 0.0)
        actual_load = float(state.get("actual_load", 0.0) or 0.0)
        return {
            "timestamp": timestamp_str,
            "agent": "Controller Agent",
            "decision": f"Executed {action_taken}",
            "reason": f"Battery SoC now {soc:.0%}.",
            "action": f"Grid import adjusted to {actual_load:.0f} kW with {actual_kw:.0f} kW battery power.",
        }

    if node_name == "auditor":
        decision_log = state.get("decision_log") or []
        latest = decision_log[-1] if decision_log else {}
        delta_eval = (latest.get("evaluate") or {}).get("delta_eval") or {}
        return {
            "timestamp": str(latest.get("timestamp") or timestamp_str),
            "agent": "Auditor Agent",
            "decision": str(latest.get("perceive") or "Audit completed."),
            "reason": str(latest.get("reason") or "Auditor evaluated dispatch output."),
            "action": str(latest.get("act") or "No action recorded."),
            "expected_reduction_kw": _optional_float(delta_eval.get("shave_kw")),
            "estimated_saving_rm": _optional_float(delta_eval.get("interval_savings_rm")),
        }

    return None


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


def _extract_node_token(node_name: str, node_state: dict[str, Any]) -> str:
    """Build a JSON token string for agent stream panel cards.

    Called when a node completed via deepagents.ainvoke() (no token streaming),
    so the outer LangGraph astream never emitted message chunks for it.
    """
    import json as _json

    if node_name == "planner":
        strategy = node_state.get("optimization_strategy") or {}
        return _json.dumps(dict(strategy), default=str)

    if node_name == "controller":
        dispatch = node_state.get("dispatch_action") or {}
        return _json.dumps({
            "action": dispatch.get("action", "hold"),
            "discharge_kw": dispatch.get("discharge_kw"),
            "charge_kw": dispatch.get("charge_kw"),
            "duration_min": dispatch.get("duration_min", 30),
            "expected_soc_after": dispatch.get("expected_soc_after"),
        }, default=str)

    if node_name == "auditor":
        auditor = node_state.get("auditor_result") or {}
        llm = auditor.get("llm_eval") or {}
        delta = auditor.get("delta_eval") or {}
        raw_conf = llm.get("confidence") or (delta.get("delta_score", 75.0) / 100.0)
        return _json.dumps({
            "reasoning": llm.get("reasoning") or auditor.get("reason", ""),
            "recommendation": llm.get("recommendation") or auditor.get("act", ""),
            "confidence": float(raw_conf),
        }, default=str)

    return ""
