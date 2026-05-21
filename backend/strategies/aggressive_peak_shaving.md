# Strategy: Aggressive Peak Shaving (Weekday PEAK, Non-Solar Facility)

## Purpose
Maximize BESS discharge during weekday PEAK tariff windows to keep grid import below the MD limit and minimize the monthly Maximum Demand charge.

## Trigger Conditions
- `tariff_window`: PEAK
- `day_type`: weekday
- `facility`: non-solar (E, SuN) — solar facilities use solar_duck_curve.md instead
- `battery_soc`: > 20% (hard floor)

## Shave Target Formula
```
shave_kw = max(0, forecast_kw - md_limit_kw + 15)
```
The +15 kW buffer accounts for forecast error. Never cap shave_kw at an arbitrary fixed value — industrial facilities (800–1200 kW range) routinely need 100–400 kW shave.

## Discharge Rules
1. **Act immediately at 14:00** — do not defer. Every PEAK tick above md_limit_kw sets a potential monthly MD record.
2. **Reserve SOC**: Maintain minimum 20% SOC after discharge.
3. **Max Interval Discharge**: 100 kW per 30-minute interval (inverter limit).
4. **Cycle Budget**: If `cycle_count > 3000`, limit DoD to 50% of remaining usable capacity.
5. **SOC triage during PEAK**:
   - SOC > 80%: discharge full shave target
   - SOC 40–80%: discharge shave target, hold 20% reserve
   - SOC 20–40%: partial discharge, preserve reserve
   - SOC < 20%: HOLD — hard safety floor

## Constraints
- `peak_starts_at_14h00`
- `max_100kW_interval`
- `reserve_20pct_soc`
- `respect_cycle_budget`

## Rationale
Weekday PEAK carries both the highest energy rate (RM 0.234/kWh) and the Maximum Demand charge (RM 97.06/kW/month billed on the single worst 30-min reading). At industrial scale, one unshaved tick at 902 kW with an 800 kW MD limit costs RM 9,900 in MD alone that month.

## Priority
**HIGH** — Primary revenue-generating strategy for weekday non-solar operations.
