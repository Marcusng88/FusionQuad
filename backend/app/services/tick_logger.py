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
        tick_buffer: list[dict[str, Any]],
        tick_index: int,
        result: dict[str, Any],
        current_time: datetime | None,
        md_limit_kw: float,
    ) -> None:
        forecast = result.get("forecast") or {}
        forecast_conf = forecast.get("confidence") or {}
        first_conf = float(next(iter(forecast_conf.values()), 0.0)) if forecast_conf else 0.0

        tariff_window = (result.get("tariff") or {}).get("window")
        actual_load = _coerce_optional_float(result.get("actual_load"))
        baseline_load = _coerce_optional_float(result.get("baseline_load"))
        is_peak = tariff_window == "PEAK"

        # within_limit is only meaningful during PEAK (MD charges only apply then)
        if is_peak and actual_load is not None:
            within_limit: bool | None = actual_load <= md_limit_kw
        else:
            within_limit = None

        peak_reduction_kw = (
            max(0.0, (baseline_load or 0.0) - (actual_load or 0.0))
            if is_peak else 0.0
        )

        tick_data = {
            "tick": tick_index,
            "datetime": (current_time or datetime.now()).strftime("%Y-%m-%dT%H:%M:%S") if current_time else None,
            "forecast_kw": _coerce_optional_float(result.get("forecast_kw")),
            "forecast_confidence": first_conf,
            "tariff_window": tariff_window,
            "optimization_strategy": result.get("optimization_strategy"),
            "dispatch_action": result.get("dispatch_action"),
            "dispatch_result": result.get("dispatch_result"),
            "baseline_load_kw": baseline_load,
            "actual_load_kw": actual_load,
            "peak_reduction_kw": peak_reduction_kw,
            "within_limit": within_limit,
            "savings_rm": _coerce_optional_float(
                (result.get("auditor_result") or {}).get("delta_eval", {}).get("interval_savings_rm")
            ),
        }

        tick_buffer.append(tick_data)

    def finalize(
        self,
        log_path: Path,
        tick_buffer: list[dict[str, Any]],
        session_state: dict[str, Any],
        available_start: datetime | None = None,
        day_type: str = "",
    ) -> None:
        log_path.parent.mkdir(parents=True, exist_ok=True)

        battery = session_state.get("battery") or {}
        total = len(tick_buffer)

        peak_ticks_data = [t for t in tick_buffer if t.get("tariff_window") == "PEAK"]
        peak_ticks_count = len(peak_ticks_data)
        within_limit_peak = int(session_state.get("within_limit_ticks", 0))

        # MD-relevant metrics: reduction vs baseline during PEAK
        peak_reductions = [t.get("peak_reduction_kw") or 0.0 for t in peak_ticks_data]
        avg_peak_reduction_kw = (sum(peak_reductions) / peak_ticks_count) if peak_ticks_count > 0 else 0.0

        peak_baselines = [t.get("baseline_load_kw") or 0.0 for t in peak_ticks_data]
        peak_actuals = [t.get("actual_load_kw") or 0.0 for t in peak_ticks_data]
        max_baseline_kw = max(peak_baselines) if peak_baselines else 0.0
        max_actual_kw = max(peak_actuals) if peak_actuals else 0.0

        summary = {
            "total_ticks": total,
            "peak_ticks": peak_ticks_count,
            # PEAK-only compliance (MD charges only apply in PEAK)
            "peak_within_limit_ticks": within_limit_peak,
            "peak_compliance_rate": round(within_limit_peak / peak_ticks_count, 4) if peak_ticks_count > 0 else 0.0,
            # How much the BESS flattened the peak (key MD metric)
            "avg_peak_reduction_kw": round(avg_peak_reduction_kw, 2),
            "max_baseline_kw": round(max_baseline_kw, 2),
            "max_actual_kw": round(max_actual_kw, 2),
            "total_savings_rm": float(session_state.get("total_savings_rm", 0.0)),
            "shave_percentage": float(session_state.get("shave_percentage", 0.0)),
            "final_soc_percent": int((float(battery.get("soc", 0.5)) or 0.5) * 100),
        }

        log = {
            "ticks": tick_buffer,
            "summary": summary,
        }

        with open(log_path, "w") as f:
            json.dump(log, f, indent=2)
