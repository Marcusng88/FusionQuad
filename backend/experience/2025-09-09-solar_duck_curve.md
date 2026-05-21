# End-of-Day Audit — 2025-09-09 (solar_duck_curve)

## Overall Performance
- Total ticks: **11**
- Ticks within MD limit: **(not fully derivable from log field) /11** → **(compliance_rate not directly given)**
- Total savings: **RM 53.16**
- Average shave per tick: **9.09 kW**
- BESS SOC: start **0.5000** → end **0.4700** (net delta **-0.0300**)
- Cycle count delta: **0.0**

## What Worked
- PEAK window discharge actions reduced grid import with positive interval savings:
  - tick 4 (14:00, PEAK): baseline 830.0 kW → actual 776.17 kW; discharge_kw 53.83 kW; savings RM 8.32; within_limit true.
  - tick 5 (14:30, PEAK): actual 785.0 kW; discharge 30.0 kW; savings RM 4.52; within_limit true.
  - tick 6 (15:00, PEAK): actual 764.78 kW; discharge 55.23 kW; savings RM 7.81; within_limit true.
  - tick 10 (17:00, PEAK): actual 696.0 kW; discharge 100.0 kW; savings RM 11.70; within_limit true.

## What Failed or Was Suboptimal
- Ineffective/zero-savings actions during OFF_PEAK:
  - tick 0 (12:00, OFF_PEAK): action_taken=charge, actual_discharge_kw=0.0; savings_rm=0.0.
  - tick 1 (12:30, OFF_PEAK): action_taken=charge; actual_discharge_kw=0.0; savings_rm=0.0.
  - tick 2 (13:00, OFF_PEAK): action_taken=charge; actual_discharge_kw=0.0; savings_rm=0.0.
  - tick 3 (13:30, OFF_PEAK): action_taken=charge; actual_discharge_kw=0.0; savings_rm=0.0.
- Forecast error signal (units/scale likely mismatched):
  - The log’s forecast_kw is ~788–844 kW while the reported metric from evaluate_delta_tool indicates only ~12.56% forecast_error_pct at the final tick (forecast_kw=796 vs actual_load=696, which matches a % error of 100*(796-696)/796≈12.56%).
  - However, shave_percentage in summary is **219.63%**, which is inconsistent with the per-tick discharge values (suggesting the summary “shave_percentage” is computed relative to an internal baseline different from md_limit_kw or total peak reduction).
- Data quality limitations:
  - `within_limit` is null for many ticks (ticks 0–3 and 7–9), so full-day compliance_rate cannot be recomputed from tick fields.
  - `cycle_count_delta` appears as 0.0 for early ticks and small nonzero values later, but the log does not provide an end-of-day cumulative cycle count; therefore “Cycle count delta” is not reliably aggregable from the visible fields.

## Recommendations for Next Similar Day
1. Add a hard rule: when tariff_window=OFF_PEAK, suppress/avoid charging actions that do not produce grid-import shaving economics (e.g., if projected md-limit breach is unlikely and savings_rm will be ~0). Instead, charge only when a measurable PEAK risk threshold is reached.
2. Fix or document metric computation for `shave_percentage` (summary shows 219.63%), and ensure Planner uses consistent baselines (md_limit_kw vs baseline_load_kw vs internal expected load) when evaluating performance.
3. Calibrate forecast handling: verify that `forecast_kw` is truly the site import forecast (not solar-only or already netted), because the strategy decisions repeatedly treated forecast_kw relative to md_limit_kw but the end-of-day metric suggests internal discrepancies.

## Pattern Comparison (vs Past Experience)
- No matching past experience files were found for day_type `solar_duck_curve` under /experience/ at audit time.
- Therefore, forecast error trend and savings trend comparisons vs prior runs are not available.
