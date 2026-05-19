"""Planner Agent - GridWise AI"""
from pathlib import Path
from typing import Any

from app.agents.config import PEAK_END_HOUR, RESERVE_SOC

STRATEGIES_DIR = Path(__file__).parent.parent.parent.parent / "strategies"
EXPERIENCE_DIR = Path(__file__).parent.parent.parent.parent / "experience"


def read_guideline_file(path: str) -> str:
    """Read a specific guideline file by name or path."""
    if not path:
        return ""

    filepath = Path(path)
    if not filepath.is_absolute() and not filepath.exists():
        filepath = STRATEGIES_DIR / path

    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return ""


def get_forecast_context(state: dict[str, Any]) -> str:
    """Build context string from AgentState value objects."""
    if not state:
        return ""

    parts = []

    tariff = state.get("tariff") or {}
    if window := tariff.get("window"):
        parts.append(f"Tariff Window: {window}")

    if day_type := state.get("day_type"):
        parts.append(f"Day Type: {day_type}")

    battery = state.get("battery") or {}
    raw_soc = battery.get("soc")
    if raw_soc is not None:
        parts.append(f"Battery SOC: {float(raw_soc) * 100:.1f}% (fraction: {raw_soc})")
    if cycles := battery.get("cycle_count"):
        parts.append(f"Cycle Count: {cycles}")
    if md_limit := state.get("md_limit_kw"):
        parts.append(f"MD Limit: {md_limit} kW")

    forecast = state.get("forecast") or {}
    if load := forecast.get("load_forecast"):
        parts.append(f"Load Forecast: {load} kW")
    if confidence := forecast.get("confidence"):
        parts.append(f"Forecast Confidence: {confidence}")

    current_time = state.get("current_time")
    if current_time:
        parts.append(f"Current Time: {current_time}")

        tariff_window = tariff.get("window") or ""
        if tariff_window == "PEAK" and hasattr(current_time, "hour"):
            peak_end_min = PEAK_END_HOUR * 60
            current_min = current_time.hour * 60 + current_time.minute
            remaining_ticks = max(1, (peak_end_min - current_min) // 30)
            parts.append(f"Remaining PEAK Ticks: {remaining_ticks}")

            bess_capacity_kwh = float(battery.get("capacity_kwh") or 1000.0)
            if raw_soc is not None and bess_capacity_kwh > 0:
                available_kwh = max(0.0, (float(raw_soc) - RESERVE_SOC) * bess_capacity_kwh)
                soc_budget_kw = available_kwh / (remaining_ticks * 0.5)
                parts.append(
                    f"SOC Budget: {soc_budget_kw:.1f} kW max sustainable discharge "
                    f"({available_kwh:.0f} kWh available above reserve / {remaining_ticks} ticks)"
                )

    return "\n".join(parts) if parts else ""
