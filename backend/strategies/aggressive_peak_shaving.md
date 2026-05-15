# Strategy: Aggressive Peak Shaving (Weekday PEAK)

## Purpose
Maximize BESS discharge during weekday PEAK tariff windows to minimize energy costs.

## Trigger Conditions
- `tariff_window`: PEAK
- `day_type`: weekday
- `load_forecast`: > 50 kW predicted interval load
- `battery_soc`: > 40%

## Discharge Rules
1. **Shave Target**: Discharge to reduce peak load by 30-50 kW below the predicted peak
2. **Reserve SOC**: Maintain minimum 20% SOC after discharge
3. **Max Interval Discharge**: 100 kW per 15-minute interval
4. **No discharge before 14:00** (preserve capacity for afternoon peak)
5. **Cycle Budget**: If `cycle_count > 3000`, reduce discharge by 50%

## Constraints
- `no_discharge_before_2PM`
- `max_100kW_interval`
- `reserve_20pct_soc`
- `respect_cycle_budget`

## Rationale
Weekday PEAK periods have the highest electricity rates. Aggressive peak shaving provides the greatest cost savings. BESS should be fully utilized during these windows.

## Priority
**HIGH** — Primary revenue-generating strategy for weekday operations.
