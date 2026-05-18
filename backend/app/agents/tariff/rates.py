"""Single source of truth for TNB tariff energy rates (RM/kWh)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TariffRates:
    peak: float      # RM/kWh
    off_peak: float  # RM/kWh
    weekend: float   # RM/kWh
    demand: float    # RM/kW/month


# Rates effective 1 July 2025 (TNB TOU tariff revision)
# MD charge = RM 30.19 Capacity + RM 66.87 Network = RM 97.06/kW/month (peak period only)
# Energy: peak 23.4 sen/kWh, off-peak 14.4 sen/kWh
TARIFF_RATES: dict[str, TariffRates] = {
    "C2": TariffRates(peak=0.234, off_peak=0.144, weekend=0.234, demand=97.06),
    "E2": TariffRates(peak=0.234, off_peak=0.144, weekend=0.234, demand=97.06),
    "C1": TariffRates(peak=0.234, off_peak=0.144, weekend=0.234, demand=89.27),
    "E1": TariffRates(peak=0.234, off_peak=0.144, weekend=0.234, demand=89.27),
}


def get_energy_rate(tariff_type: str, window: str) -> float:
    rates = TARIFF_RATES.get(tariff_type, TARIFF_RATES["C2"])
    if window == "PEAK":
        return rates.peak
    if window == "WEEKEND":
        return rates.weekend
    return rates.off_peak
