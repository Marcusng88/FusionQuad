# Strategy: Holiday / Weekend Surge

## Purpose
Manage BESS dispatch during holidays and weekends where TNB C2 **Maximum Demand charge does NOT apply** — focus is purely on energy cost arbitrage, not MD shaving.

## TNB C2 Important Clarification
**MD charge (RM 97.06/kW/month) only applies during weekday PEAK hours (14:00–22:00 Mon–Fri).**
- Holidays and weekends: weekend energy rate (RM 0.234/kWh) applies all day, but no MD charge.
- Do NOT discharge for MD-shaving reasons on holidays — there is no MD penalty to avoid.
- Discharge only when energy arbitrage (buy cheap OFF_PEAK, sell dear PEAK-rate hours) makes sense.

## Trigger Conditions
- `day_type`: holiday or weekend
- `battery_soc`: > 30%

## Discharge Rules
1. **Shave Target**: Only discharge to reduce energy cost, not MD. `shave_kw` should be modest (20–40 kW) unless load is extreme.
2. **Reserve SOC**: Maintain minimum 30% SOC (unpredictable follow-on loads on holidays).
3. **Max Interval Discharge**: 80 kW per 15-minute interval.
4. **Anticipatory Charging**: If SOC < 50% by 18:00, charge overnight for the next weekday PEAK.

## Charging Rules
1. Prioritize reaching 90% SOC overnight if next day is a weekday (PEAK MD risk returns).
2. Charge rate: 50–80 kW per interval during OFF_PEAK hours.

## Constraints
- `no_md_shaving_on_holidays`
- `max_80kW_interval`
- `reserve_30pct_soc`
- `plan_overnight_charge_if_next_day_weekday`

## Rationale
Holiday load patterns are atypical (higher morning loads, extended activity) but carry no MD charge risk. Conservative discharge preserves battery life and ensures BESS is fully charged entering the next weekday PEAK window.

## Priority
**MEDIUM** — Energy cost management only; no MD penalty exposure.
