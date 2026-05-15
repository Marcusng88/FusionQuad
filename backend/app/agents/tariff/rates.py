"""Single source of truth for TNB tariff energy rates (RM/kWh)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TariffRates:
    peak: float      # RM/kWh
    off_peak: float  # RM/kWh
    weekend: float   # RM/kWh
    demand: float    # RM/kW/month


TARIFF_RATES: dict[str, TariffRates] = {
    "C2": TariffRates(peak=0.45, off_peak=0.22, weekend=0.30, demand=97.06),
    "E2": TariffRates(peak=0.45, off_peak=0.22, weekend=0.30, demand=97.06),
    "C1": TariffRates(peak=0.45, off_peak=0.22, weekend=0.30, demand=89.27),
    "E1": TariffRates(peak=0.45, off_peak=0.22, weekend=0.30, demand=89.27),
}


def get_energy_rate(tariff_type: str, window: str) -> float:
    rates = TARIFF_RATES.get(tariff_type, TARIFF_RATES["C2"])
    if window == "PEAK":
        return rates.peak
    if window == "WEEKEND":
        return rates.weekend
    return rates.off_peak
