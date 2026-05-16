# End-of-Day Audit — 2025-03-09 (solar_duck_curve)

## Summary
- Ticks: 0 / 47 (end-of-day tick submitted)
- Compliance (within MD limit): 25 / 47 ticks
- Total savings: RM 65.25
- Tariff window: WEEKEND

## Final tick state (TICK 0)
- Dispatch action: discharge
- Dispatch result:
  - New SOC: 0.380925
  - Temp increase: 0.0 °C
  - Cycle count delta: 0.0
  - Actual discharge (kW): 0.0
  - Efficiency loss: 0.05%
- Load / limits:
  - Baseline load: 865.0 kW
  - Actual load: 865.0 kW
  - MD limit: 800.0 kW
  - Forecast: 808.6790 kW

## Rule compliance evaluation (final tick)
- Result: **PASS**
- Violations: none

## Delta / shaving evaluation (final tick)
- Shave (kW): 0.0
- Shave (%): 0.0
- Forecast error (%): 0.0
- Interval savings (RM): 0.0
- Delta score: 0.0

## Observations
- Final tick indicates a discharge command with **0.0 kW actual discharge**, resulting in **no load shave** and **no incremental savings** for this interval.
- No rule violations were detected for the provided final tick inputs.

## Recommendation
- Investigate why discharge was issued while actual discharge power resolved to 0.0 kW (e.g., power limit, inverter state, or dispatch feasibility). Apply a pre-dispatch guard to avoid issuing discharge/charge actions that cannot execute.

## Confidence
- Moderate (0.5): audit constrained by being provided only the final tick inputs and aggregate totals; past-experience context files were not found during lookup.