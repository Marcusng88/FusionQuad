# End-of-Day Audit — 2025-09-02 (solar_duck_curve)

## Overall Performance
- Total ticks: **8**
- Ticks within MD limit: **2/8** → **25% compliance**
- Total savings: **RM 0.00**
- Average shave per tick: **0.00 kW**
- BESS SOC: start **0.5000** → end **0.5000** (net delta **+0.0000**)
- Cycle count delta: **0.0**

## What Worked
- The simulation satisfied MD compliance in **2 ticks** (per `within_limit_ticks=2` in the log summary).
- Deterministic safety evaluation (`evaluate_rules_tool`) on the final tick state: **passed** with **0 violations**.

## What Failed or Was Suboptimal
- MD demand limit breaches: **6/8 ticks** with `within_limit=false`.
- Ineffective dispatch moments:
  - Tick **0**: planner `dispatch_action.action="discharge"` but `actual_discharge_kw=0.0` and `savings_rm=0.0`.
- Dispatch direction mismatch (charge during PEAK): none observed in the extracted log (`charge_kw` is null).
- Forecast error signal (forecast_kw vs actual_load_kw):
  - At the last extracted tick (**tick 7**), forecast was **847.38 kW** vs actual **895.0 kW** → **+47.62 kW** error (forecast underestimates actual).
  - Full per-tick forecast error distribution was not recomputed in this audit run due to partial in-tool extraction.

## Recommendations for Next Similar Day
1. Prevent no-op discharge: if `action="discharge"` then require `actual_discharge_kw>0`; otherwise convert to `hold`.
2. Add an MD-limit override during solar_duck_curve phases where strategy suppresses discharge: allow limited discharge when `actual_load_kw - md_limit_kw > 25 kW`.
3. Verify payoff calculation wiring: ensure `within_limit` and `savings_rm` are derived from the same operational quantity. Here, `total_savings_rm=0.0`.

## Pattern Comparison (vs Past Experience)
- No prior `/experience/*-solar_duck_curve.md` files were available for comparison before this audit.
