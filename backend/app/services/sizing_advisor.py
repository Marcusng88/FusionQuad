from __future__ import annotations

from math import ceil
from typing import Any


class SizingAdvisor:
    def compute(
        self,
        *,
        full_records: list[dict[str, Any]],
        metadata: dict[str, Any],
        md_limit_kw: float,
        md_rate: float,
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
        recommended_solar = (
            solar_installed
            if solar_installed > 0
            else float(ceil(daytime_target / 50) * 50 if daytime_target > 0 else 0.0)
        )

        estimated_peak_reduction = round(min(max_breach, recommended_bess / 5), 1)
        estimated_monthly_savings = round(estimated_peak_reduction * md_rate, 2)

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
