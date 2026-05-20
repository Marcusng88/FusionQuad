# BESS System Audit — Confirmed Issues
_Verified against `backend/app/agents/controller/node.py`, `solver.py`, `simulation.py`, `2025-04-07-weekday.json`_

---

## Key Outcome: RM 0 MD Savings

Monthly MD charge bills on the **single worst 30-min PEAK reading**. Last run:
- Worst tick: **16:00 → 1231 kW** (battery empty, no dispatch)
- Without BESS: 16:00 would still be 1231 kW (same CSV baseline)
- MD record identical with or without BESS

RM 200 logged as "savings" is energy arbitrage only (PEAK rate kWh). Not MD savings. Battery cycled for zero reduction in monthly bill.

---

## Issue 1 — MD Override Drives All PEAK Dispatch (CRITICAL)

**The planner, MILP, and deep agent are bypassed for every PEAK tick.**

`controller_node` has a hardcoded safety override (lines 252–270):
```python
reserve_soc = (optimization_strategy).get("reserve_soc_pct", 0.25)
if (tariff_window == "PEAK"
    and baseline_load > md_limit_kw
    and battery_soc > reserve_soc + 0.05):
    min_discharge_kw = min(baseline_load - md_limit_kw + 15.0, max_discharge_kw)
    if action != "discharge" or current_kw < min_discharge_kw:
        forced_action = {"discharge_kw": min_discharge_kw}
```

Verification — all 4 PEAK dispatch values exactly match `baseline - 800 + 15`:

| Tick | Time  | CSV kw_import | MD override formula | Actual dispatch | Match |
|------|-------|--------------|---------------------|-----------------|-------|
| 8    | 14:00 | 954 kW       | 954 − 800 + 15 = 169 | 169 kW         | ✓     |
| 9    | 14:30 | 1038 kW      | 1038 − 800 + 15 = 253 | 253 kW        | ✓     |
| 10   | 15:00 | 1106 kW      | 1106 − 800 + 15 = 321 | 321 kW        | ✓     |
| 11   | 15:30 | 1152 kW      | 1152 − 800 + 15 = 367 | 367 kW        | ✓     |

Also confirmed: `actual_load_kw` for ticks 8–11 is uniformly **785 kW** = `md_limit - 15 = 800 - 15`. The override always brings net load to exactly 785 kW.

**MILP output and planner shave_kw are irrelevant for PEAK ticks.** The override fires because the agent/MILP returns a lower value and `current_kw < min_discharge_kw`. The planner's multi-step reasoning, strategy file reads, and experience file reads have zero effect on actual PEAK dispatch.

---

## Issue 2 — MD Override Has No SOC Budget Awareness (CRITICAL)

Override fires as long as `battery_soc > reserve_soc + 0.05`. At tick 11:
- SOC = **26.6%**, threshold = 20% + 5% = **25%**. Gap = **1.6%**.
- Override forces 367 kW × 0.5h / 1000 kWh = 18.35% SOC consumed.
- SOC after: 26.6% − 18.35% = **9.15%** → below 10% hard floor.

The override does not ask: _"if I use 367 kW now, will I have SOC for the remaining PEAK ticks?"_

At tick 11, remaining PEAK window = 13 ticks (15:30–22:00). Battery empty after one more dispatch. Ticks 12–14 (and beyond) unprotected.

**The 1.6% SOC margin above threshold is the direct cause of battery depletion and the 1231 kW MD record.**

---

## Issue 3 — Planner's `target_soc_end` and MILP Are Internally Consistent but Overridden

Planner at tick 8 sets `target_soc_end = 0.50`. MILP enforces `soc[5] >= 0.50` (SOC at end of 6-step horizon). With starting SOC 0.619 and target 0.50, MILP can only use:

```
(0.619 − 0.50) × 1000 = 119 kWh total across 6 steps
= ~39.7 kW/step if evenly spread
```

MILP returns a conservative discharge value (~40–80 kW). Override fires (value < 169). Target SOC planning is discarded.

**The planner and MILP agree with each other but are ignored.** The planner tries to conserve SOC for the full PEAK window. The override does not respect this. No coordination mechanism exists between the two.

---

## Issue 4 — Battery Capacity Insufficient for Load Profile

At PEAK start (SOC 62%, 1000 kWh, 20% reserve):
```
Available energy = (0.62 − 0.20) × 1000 = 420 kWh
Energy consumed by ticks 8–11 (dispatch × 0.5h):
  (169 + 253 + 321 + 367) × 0.5 = 555 kWh
```

555 kWh > 420 kWh available. Battery was always going to be empty before tick 12.

Even at 95% SOC (maximum):
```
Available = (0.95 − 0.20) × 1000 = 750 kWh
```

Still depleted before the end of 4 PEAK ticks if loads stay at 950–1150 kW. The system never computes or reports this impossibility. It silently drains and fails.

---

## Issue 5 — No PEAK Window Horizon in MILP or Planner

PEAK = 14:00–22:00 = **16 ticks**. MILP horizon = **6 steps (3 hours)**.

At 14:00, MILP sees 14:00–17:00 only. It optimally protects those 6 ticks. Ticks from 17:00–22:00 are invisible to it. Even if MILP worked perfectly, it would deplete SOC protecting 14:00–17:00 and leave 17:00–22:00 unprotected.

**Planner also has no remaining-PEAK-ticks context.** `get_forecast_context()` (`planner/__init__.py:23`) builds a state string with `Load Forecast`, `Battery SOC`, `MD Limit` — no field for remaining PEAK ticks, no SOC-per-tick budget.

Planner computes `shave_kw = forecast_kw − md_limit + 15` per tick in isolation. Same formula whether 16 ticks remain or 1.

---

## Issue 6 — Forecast Direction Wrong at Critical Tick

6-step forecast from 14:00: `[1021, 1031, 1010, 945, 890, 853]` — **declining**.

Actual CSV loads from 14:00: 954, 1038, 1106, 1152, **1231**, 959 — **increasing then spiking**.

MILP at 14:00 saw a declining curve and (correctly, given its input) concluded load risk reduces over time. It front-loaded SOC usage for the earlier, higher-forecast ticks. Actual worst tick (1231 kW) arrived after battery was empty.

Forecast confidence logged as **0.80** throughout. This is computed from validation MAPE on historical split, not on spike/ramp patterns. The 0.80 confidence is misleading when the model predicts the wrong direction.

---

## Issue 7 — MAX_CHARGE_KW = 50 kW Hardcoded

```python
# solver.py:49
MAX_CHARGE_KW = 50.0
```

Simulation started at 10:00. Pre-PEAK window (10:00–14:00) = 8 ticks available for charging.
```
8 ticks × 50 kW × 0.5h × 0.95 efficiency / 1000 kWh = +19% SOC
Starting SOC 50% → max 69% at PEAK start
```

MAX_CHARGE_KW = 50 kW is very conservative (5% of 1000 kWh capacity = 0.05C rate). Not user-configurable unlike `max_discharge_kw`. Higher charge rate would improve pre-PEAK SOC but cannot overcome Issue 4 at these load levels.

---

## Issue 8 — `actual_discharge_kw` Field Incorrect During Charge Ticks

`mock_inverter_dispatch` returns `actual_kw = power_kw` regardless of action type. For charge ticks, this value goes into `actual_discharge_kw` field in `dispatch_result`.

Log examples (ticks 1–6): `"action_taken": "charge", "actual_discharge_kw": 50.0`. Should be 0 for discharge field during charge actions. Does not affect SOC calculation but corrupts log analysis and any downstream metric that reads this field.

---

## What Is Working Correctly

- MD override **does** successfully bring PEAK ticks 8–11 to net 785 kW. The logic is correct for individual tick protection.
- MILP minimax objective (`minimize peak_demand = max(load[i] − power[i])`) is the right formulation.
- `baseline_load` correctly uses actual CSV `kw_import` per tick (not forecast).
- SOC hard floor (< 20% → hold) correctly prevented dispatch at tick 12.

---

## Root Cause Summary

```
1. MD override: no remaining-PEAK-ticks budget check → kills battery 1 tick before worst load
2. Planner/MILP: correctly compute conservative dispatch, correctly get overridden, but
   their outputs have no path into the override logic
3. Battery: 1000 kWh at 62% SOC cannot cover 950–1230 kW loads for 8h at 800 kW limit
4. Forecast: predicted declining load, actual increased — wrong at critical moment
```

The system optimises at the per-tick level. TNB MD billing is per-month worst-tick. These objectives are misaligned. Protecting early PEAK ticks at full shave and running out of battery costs the same MD bill as doing nothing.

---

## Suggested Fix Direction (Not Implemented)

**Minimum viable fix — controller_node MD override:**
```python
# Add before override fires:
remaining_peak_min = max(30, (22 * 60) - (current_hour * 60 + current_min))
remaining_ticks = remaining_peak_min // 30
available_kwh = max(0.0, (battery_soc - reserve_soc) * bess_capacity_kwh)
max_sustainable_kw = available_kwh / (remaining_ticks * 0.5)
min_discharge_kw = min(
    baseline_load - md_limit_kw + 15.0,
    max_discharge_kw,
    max_sustainable_kw,  # ← new: rate-limit by remaining budget
)
```

This does not fully solve the MD record problem (battery is still insufficient) but prevents the battery from being emptied on a single tick when many PEAK ticks remain.

**Planner fix — inject SOC budget into strategy prompt:**
Pass `remaining_peak_ticks` and `max_sustainable_kw` as state fields so the planner's shave_kw recommendation accounts for battery longevity across the full PEAK window.
