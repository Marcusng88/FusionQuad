"""Tariff Agent - computes TNB tariff window and rates from simulation datetime."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Literal

from app.agents.state import AgentState

logger = logging.getLogger(__name__)

TARIFF_RATES: dict[str, dict[str, float]] = {
    "C2": {"peak_energy": 28.52, "off_peak_energy": 24.43, "capacity": 30.19, "network": 66.87},
    "E2": {"peak_energy": 28.52, "off_peak_energy": 22.40, "capacity": 30.19, "network": 66.87},
    "C1": {"peak_energy": 28.52, "off_peak_energy": 24.43, "capacity": 29.43, "network": 59.84},
    "E1": {"peak_energy": 28.52, "off_peak_energy": 22.40, "capacity": 29.43, "network": 59.84},
}

DEMAND_RATES: dict[str, float] = {"C2": 97.06, "E2": 97.06, "C1": 89.27, "E1": 89.27}

_HOLIDAYS: set[str] | None = None


def _load_holidays() -> set[str]:
    global _HOLIDAYS
    if _HOLIDAYS is None:
        holidays_path = Path(__file__).parent.parent.parent / "data" / "holidays.json"
        try:
            with open(holidays_path) as f:
                holidays = json.load(f)
            _HOLIDAYS = {h["date"] for h in holidays}
        except Exception as e:
            logger.warning(f"Failed to load holidays: {e}, using empty set")
            _HOLIDAYS = set()
    return _HOLIDAYS


def _is_holiday(dt: datetime) -> bool:
    return dt.strftime("%Y-%m-%d") in _load_holidays()


def _get_tariff_window(dt: datetime) -> Literal["PEAK", "OFF_PEAK", "WEEKEND"]:
    if _is_holiday(dt):
        return "WEEKEND"
    if dt.weekday() >= 5:
        return "WEEKEND"
    if 14 <= dt.hour < 22:
        return "PEAK"
    return "OFF_PEAK"


class TariffNode:
    def __init__(self, tariff_type: str = "C2"):
        if tariff_type not in TARIFF_RATES:
            logger.warning(f"Unknown tariff_type '{tariff_type}', defaulting to C2")
            tariff_type = "C2"
        self.tariff_type = tariff_type

    def invoke(self, state: AgentState) -> AgentState:
        current_time = state.get("current_time")
        if current_time is None:
            logger.warning("current_time is None, defaulting to PEAK window")
            window = "PEAK"
        else:
            window = _get_tariff_window(current_time)

        rates = TARIFF_RATES[self.tariff_type]
        energy_rate = rates["peak_energy"] if window == "PEAK" else rates["off_peak_energy"]
        demand_charge = DEMAND_RATES[self.tariff_type] if window == "PEAK" else 0.0

        return {
            "tariff_window": window,
            "energy_rate": energy_rate,
            "demand_charge": demand_charge,
            "tariff_type": self.tariff_type,
        }
