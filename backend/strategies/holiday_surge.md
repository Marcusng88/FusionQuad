# Strategy: Holiday Surge

## Purpose
Handle elevated loads during holiday periods when demand patterns differ from normal weekday operations.

## Trigger Conditions
- `tariff_window`: PEAK or OFF_PEAK (holidays can extend peak periods)
- `day_type`: holiday
- `load_forecast`: > 40 kW predicted interval load
- `battery_soc`: > 30%

## Discharge Rules
1. **Shave Target**: Discharge to reduce peak load by 20-40 kW
2. **Reserve SOC**: Maintain minimum 30% SOC (holidays may have unpredictable follow-on loads)
3. **Max Interval Discharge**: 80 kW per 15-minute interval
4. **Extended Peak Handling**: Allow discharge to continue past normal 14:00 cutoff if load forecast remains elevated
5. **Anticipatory Charging**: If SOC < 50% by 18:00, plan for overnight valley-fill charging

## Constraints
- `max_80kW_interval`
- `reserve_30pct_soc`
- `extended_peak_ok`
- `plan_overnight_charge`

## Rationale
Holidays often feature atypical load patterns (higher morning loads, extended daytime activity). Conservative discharge ensures BESS availability for unexpected surge demands.

## Priority
**MEDIUM** — Important for cost management during holiday periods.
