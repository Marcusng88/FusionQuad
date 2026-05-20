"""Tariff Agent - computes TNB tariff window and rates from simulation datetime."""
import logging
from datetime import datetime
from typing import Literal

from app.agents.state import AgentState, TariffContext
from app.agents.tariff.rates import TARIFF_RATES, get_energy_rate

logger = logging.getLogger(__name__)

DEMAND_RATES: dict[str, float] = {t: r.demand for t, r in TARIFF_RATES.items()}


def _get_tariff_window(dt: datetime, is_holiday: bool = False) -> Literal["PEAK", "OFF_PEAK", "WEEKEND"]:
    if is_holiday or dt.weekday() >= 5:
        return "WEEKEND"
    if 14 <= dt.hour < 22:
        return "PEAK"
    return "OFF_PEAK"


class TariffNode:
    def __init__(self, tariff_type: str = "C2"):
        if tariff_type not in TARIFF_RATES:
            logger.warning(f"Unknown tariff_type '%s', defaulting to C2", tariff_type)
            tariff_type = "C2"
        self.tariff_type = tariff_type

    def invoke(self, state: AgentState) -> dict:
        current_time = state.get("current_time")
        day_type = state.get("day_type", "")
        is_holiday = day_type == "holiday"
        if current_time is None:
            logger.warning("current_time is None, defaulting to PEAK window")
            window = "PEAK"
        else:
            window = _get_tariff_window(current_time, is_holiday=is_holiday)

        energy_rate = get_energy_rate(self.tariff_type, window)
        demand_charge = DEMAND_RATES[self.tariff_type] if window == "PEAK" else 0.0

        logger.info(
            "tariff | window=%s energy_rate=%.4f demand_charge=%.2f type=%s",
            window, energy_rate, demand_charge, self.tariff_type,
        )

        return {
            "tariff": TariffContext(
                window=window,
                energy_rate=energy_rate,
                demand_charge=demand_charge,
                tariff_type=self.tariff_type,
            )
        }
