"""Planner Agent - GridWise AI"""
from pathlib import Path
from typing import Any

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

    if time := state.get("current_time"):
        parts.append(f"Current Time: {time}")

    return "\n".join(parts) if parts else ""
