from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _coerce_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


class TickLogger:
    def append_tick(
        self,
        log_path: Path,
        tick_index: int,
        result: dict[str, Any],
        current_time: datetime | None,
        md_limit_kw: float,
    ) -> None:
        log_path.parent.mkdir(parents=True, exist_ok=True)

        forecast = result.get("forecast") or {}
        forecast_conf = forecast.get("confidence") or {}
        first_conf = float(next(iter(forecast_conf.values()), 0.0)) if forecast_conf else 0.0

        tick_data = {
            "tick": tick_index,
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
                and _coerce_optional_float(result.get("actual_load")) <= md_limit_kw
            ),
            "savings_rm": _coerce_optional_float(
                (result.get("auditor_result") or {}).get("delta_eval", {}).get("interval_savings_rm")
            ),
        }

        if log_path.exists():
            with open(log_path) as f:
                log = json.load(f)
        else:
            log = {"ticks": [], "summary": {}}

        log["ticks"].append(tick_data)
        with open(log_path, "w") as f:
            json.dump(log, f, indent=2)

    def finalize(
        self,
        log_path: Path,
        session_state: dict[str, Any],
        available_start: datetime | None,
        day_type: str,
    ) -> None:
        if not log_path.exists():
            return

        with open(log_path) as f:
            log = json.load(f)

        battery = session_state.get("battery") or {}
        within_limit = int(session_state.get("within_limit_ticks", 0))
        total = int(session_state.get("total_intervals", 0)) or len(log["ticks"])
        decision_log = session_state.get("decision_log", [])
        last_auditor = decision_log[-1] if decision_log else {}

        log["summary"] = {
            "total_ticks": total,
            "within_limit_ticks": within_limit,
            "total_savings_rm": float(session_state.get("total_savings_rm", 0.0)),
            "compliance_rate": round(within_limit / total, 4) if total > 0 else 0.0,
            "shave_percentage": float(session_state.get("shave_percentage", 0.0)),
            "final_soc_percent": int((float(battery.get("soc", 0.5)) or 0.5) * 100),
        }

        date_str = (available_start or datetime.now()).strftime("%Y-%m-%d")
        experience_path = log_path.parent.parent / "experience" / f"{date_str}-{day_type}.md"
        if experience_path.exists():
            with open(experience_path) as f:
                log["audit_report"] = f.read()
        else:
            log["audit_report"] = last_auditor.get("reason", "") or "No experience report available."

        with open(log_path, "w") as f:
            json.dump(log, f, indent=2)
