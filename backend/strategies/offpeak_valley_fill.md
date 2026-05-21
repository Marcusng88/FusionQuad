# Strategy: Off-Peak Valley Fill

## Purpose
Charge BESS during OFF_PEAK tariff windows when electricity rates are lowest, preparing for upcoming PEAK periods.

## Trigger Conditions
- `tariff_window`: OFF_PEAK
- `day_type`: any (weekday, holiday, solar_duck_curve)
- `battery_soc`: < 85% (room for charging)
- `current_time`: Typically 22:00 - 06:00 for overnight valley fill

## Charging Rules
1. **Charge Target**: Bring SOC to 90-95% by start of next PEAK window
2. **Charge Rate**: Up to 80 kW per 30-minute interval (inverter limit — 0.08C for 1000 kWh BESS)
3. **Max Charge**: Do not exceed 95% SOC (preserve cycle life)
4. **Duration**: Charge until SOC target reached or OFF_PEAK window ends

## Constraints
- `max_charge_95pct_soc`
- `charge_rate_50_80kW`
- `overnight_charge_window`
- `grid_capacity_respect`

## Rationale
OFF_PEAK charging is the lowest-cost energy procurement strategy. BESS should maximize State of Charge during these windows to enable aggressive PEAK shaving when rates are highest.

## Priority
**HIGH** — Foundational charging strategy for cost optimization.

## Load Forecast Considerations
- If next day PEAK demand is forecast to be high (load_forecast > 80 kW), prioritize reaching 95% SOC
- If forecast confidence is low, maintain 80% SOC target to avoid over-charging on uncertain high-demand days

---

## T5 Pre-Peak Preparatory Period (12:00–14:00, weekdays)

**Objective**: Maximize SOC before PEAK window opens at 14:00. This window is still OFF_PEAK — MD charge does not apply yet.

1. **Action**: HOLD if SOC ≥ 80%. Charge at 50 kW if SOC < 75%.
2. **Shave Target**: 0 kW — do NOT discharge during T5. Discharging before 14:00 wastes capacity needed for the PEAK window.
3. **Exception**: Only discharge if SOC > 90% AND load > 110% of md_limit_kw (extreme headroom case only).
4. **Target by 14:00**: SOC ≥ 80% entering PEAK window.

**Why T5 matters**: Every percent of SOC lost before 14:00 reduces the available discharge buffer during the most expensive window of the day.
