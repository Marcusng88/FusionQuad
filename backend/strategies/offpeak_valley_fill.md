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
2. **Charge Rate**: 50-80 kW per 15-minute interval (respect inverter limits)
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
