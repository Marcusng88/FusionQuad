# Strategy: Solar Duck Curve

## Purpose
Optimize BESS dispatch during the "solar duck curve" period when solar generation creates mid-day valley and late-afternoon surge.

## Trigger Conditions
- `tariff_window`: OFF_PEAK (solar hours) or PEAK (late afternoon surge)
- `day_type`: solar_duck_curve
- `load_forecast`: Characterized by low mid-day loads (< 30 kW) followed by sharp ramp-up after 16:00
- `battery_soc`: > 35%

## Phase 1: Solar Valley (10:00 - 15:00)
1. **Charging Strategy**: Charge during low solar-price windows if SOC < 80%
2. **Shave Target**: 0 kW (no discharge during cheapest solar hours)
3. **Max Charge Rate**: 50 kW per interval

## Phase 2: Duck Ramp (15:00 - 19:00)
1. **Discharge Strategy**: Aggressive discharge starting at 15:00 to smooth the duck curve ramp
2. **Shave Target**: Discharge 30-60 kW to blunt the evening surge
3. **Reserve SOC**: Maintain minimum 25% SOC
4. **Max Interval Discharge**: 100 kW

## Constraints
- `charge_during_solar_valley`
- `no_discharge_10AM_to_3PM`
- `aggressive_discharge_3PM_to_7PM`
- `reserve_25pct_soc`

## Rationale
The solar duck curve requires BESS to absorb mid-day excess solar generation and discharge during the evening demand surge. Timing is critical — early discharge before 15:00 wastes capacity; late discharge misses the cost-saving window.

## Priority
**HIGH** — Critical for solar-rich grid environments.
