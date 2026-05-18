# End-of-Day Audit — 2025-09-02 (solar_duck_curve)

## Overall Performance
- Total ticks: **8**
- Ticks within MD limit: **2/8** → **25% compliance**
- Total savings: **RM 113.09**
- Average shave per tick: **-** (log fields provide no single per-tick shave_kw; discharge_kw values exist but shave_kw is not reliably present for all ticks)
- BESS SOC: start **0.9000** → end **0.7000** (net delta **-0.2000**)
- Cycle count delta: **0.0** (tick-level cycle_count_delta values exist, but no total delta field is provided in summary; net from log is not aggregated in this file)

## What Worked
- Tick 2 (14:00, PEAK): Discharged **100 kW**; within MD limit (**actual_load_kw 762.0**) and achieved savings **RM 26.68**.
- Tick 7 (16:30, PEAK): Discharged **73.7 kW**; within MD limit (**actual_load_kw 748.3**) and savings **RM 18.07**.
- Late-day duck-ramp actions (ticks 5–7) generally reduced load, and the last interval (tick 7) successfully restored compliance.

## What Failed or Was Suboptimal
- Demand limit breaches despite PEAK windows:
  - Tick 0 (13:00, OFF_PEAK): Within_limit **false** (**actual_load_kw 868.0**), savings **RM 0.00** (action hold).
  - Tick 1 (13:30, OFF_PEAK): Within_limit **false** (**actual_load_kw 857.0**), savings **RM 0.00** (action hold).
  - Tick 3 (14:30, PEAK): Discharge forbidden by strategy window; action **hold** and still **within_limit false** (**actual_load_kw 902.0**, savings RM 0.00). Root cause: conflict between MD risk and solar_duck_curve “no discharge 10:00–15:00” constraint.
  - Tick 4 (15:00, PEAK): Discharged **72.0 kW** but still **within_limit false** (**actual_load_kw 818.0**, savings **RM 21.05**). Indicates under-shaving vs MD margin.
  - Tick 5 (15:30, PEAK): Discharged **81.23 kW** but still **within_limit false** (**actual_load_kw 809.77**, savings **RM 23.75**). Slight under-shave (~9.77 kW above MD).
  - Tick 6 (16:00, PEAK): Discharged **80.5 kW** but still **within_limit false** (**actual_load_kw 805.5**, savings **RM 23.54**). Slight under-shave (~5.5 kW above MD).
- Ineffective discharge events where discharge occurred but savings were zero: none observed (all discharge ticks with savings reported as > 0).
- Dispatch direction mismatch (charge during PEAK): none observed; charge_kw is null throughout the log.
- Forecast error signal (per tick, using forecast_kw vs actual_load_kw from the log):
  - Tick 0: forecast 893.98 vs actual 868.0 (error **-25.98 kW**)
  - Tick 1: forecast 901.05 vs actual 857.0 (error **-44.05 kW**)
  - Tick 2: forecast 899.52 vs actual 762.0 (error **-137.52 kW**; implies strategy over-allocated discharge vs realized load)
  - Tick 3: forecast 905.96 vs actual 902.0 (error **-3.96 kW**; MD miss due to forced hold)
  - Tick 4: forecast 871.97 vs actual 818.0 (error **-53.97 kW**; suggests discharge did bring load down but still not enough)
  - Tick 5: forecast 881.23 vs actual 809.77 (error **-71.46 kW**)
  - Tick 6: forecast 880.48 vs actual 805.5 (error **-74.98 kW**)
  - Tick 7: forecast 873.65 vs actual 748.3 (error **-125.35 kW**)
  Net: forecasts are consistently higher than actuals (negative errors), yet MD compliance is still low—pointing to strategy constraint/quantization issues (e.g., max interval cap / reserve rules) and timing windows more than forecast underestimation.

## Recommendations for Next Similar Day
1. Add an MD-safety override during solar_duck_curve “no discharge 10:00–15:00” window: if **actual_load_kw > MD limit by more than X** (start with X=25–50 kW) in OFF/PEAK pre-ramp ticks, allow limited discharge despite the valley constraint.
2. Adjust PEAK under-shaving at ticks 4–6: because these intervals remained above MD by ~**5.5 to 9.8 kW**, increase shave target by a small buffer when discharging under caps (e.g., target **MD limit − 10 kW** or apply buffer **+10 kW** shaving beyond forecast margin), subject to SOC reserve.
3. Forecast-to-discharge mapping check: forecasts are ~**4–14% above actuals** on most ticks while MD breaches still occur; review whether discharge_kw calculations use forecast horizon/units consistent with actual_load_kw and whether tariff/strategy phase selection is aligned to datetime boundaries.

## Pattern Comparison (vs Past Experience)
- No prior `/experience/*-solar_duck_curve.md` files exist (only `/experience/.gitkeep` found), so pattern comparison is not available.
