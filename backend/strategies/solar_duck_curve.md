# Strategy: Solar Duck Curve (Industrial Scale)

## Purpose
Optimize BESS dispatch for commercial/industrial facilities (800–1200 kW) with on-site solar PV where afternoon load surges into the TNB C2 peak tariff window (14:00–22:00 weekdays).

## TNB C2 Critical Fact
**MD charge (RM 97.06/kW/month) is billed on the highest 30-min reading during PEAK hours only.**
- PEAK window: **14:00–22:00 weekdays**
- OFF_PEAK: 22:00–14:00 weekdays — MD charge does NOT apply in this window
- Every single tick at 14:00–22:00 where load > md_limit_kw is a potential MD record setter
- The monthly bill is determined by the WORST single tick in the billing period

## Trigger Conditions
- `day_type`: solar_duck_curve OR large_weekday
- `facility`: SoL, Mi2
- `tariff_window`: PEAK or OFF_PEAK
- `load_forecast`: 800–1400 kW range
- `battery_soc`: > 20%

---

## Phase 1: Pre-Peak Preservation (OFF_PEAK, before 14:00)
**Objective**: Maximize SOC before PEAK window opens. Do NOT waste battery on OFF_PEAK ticks.

1. **Action**: HOLD. If SOC < 75%, charge at 50 kW.
2. **Shave Target**: 0 kW — MD charge does not apply before 14:00. Discharging now wastes capacity needed for the PEAK window.
3. **Exception**: Only discharge if SOC > 90% and load > 110% of md_limit_kw (extreme headroom case).

---

## Phase 2: PEAK Discharge (PEAK window, 14:00–22:00)
**Objective**: Keep every PEAK tick below md_limit_kw. Act on the CURRENT tick — never defer.

1. **Action**: Discharge as soon as tariff_window == "PEAK"
2. **Shave Target formula**: `shave_kw = max(0, forecast_kw - md_limit_kw + 15)`
   - The +15 kW buffer accounts for forecast error (GRU model ~3–5% MAPE at this scale)
3. **Reserve SOC**: 20% minimum
4. **Max Interval Discharge**: 100 kW per 30-minute interval

### MANDATORY RULE (non-negotiable during PEAK)
```
IF tariff_window == "PEAK" AND forecast_kw > md_limit_kw:
    shave_kw = forecast_kw - md_limit_kw + 15   ← minimum, go higher if SOC allows
    DO NOT output shave_kw = 0 in PEAK window when load exceeds MD limit
```

### DO NOT defer discharge
- `"14:30 is early, wait until 15:00"` → WRONG. 14:30 is already PEAK. Every breach sets the monthly record.
- `"Apply conservatively"` → WRONG during PEAK. Conservative = expensive. Discharge now.
- `"Phase 2 starts at 15:00"` → WRONG. Phase 2 starts at 14:00 when PEAK starts.

---

## SOC Management
| Situation | Action |
|-----------|--------|
| SOC > 80%, entering PEAK with load > MD limit | Discharge full shave target |
| SOC 40–80%, PEAK, load > MD limit | Discharge shave target, reserve 20% |
| SOC 20–40%, PEAK, load > MD limit | Partial discharge, preserve reserve |
| SOC < 20% | HOLD — hard safety floor |

---

## Constraints
- `discharge_only_during_peak_window`
- `peak_starts_at_14h00_not_15h00`
- `reserve_20pct_soc`
- `max_100kW_per_interval`
- `forecast_buffer_15kw_for_error`

---

## Rationale
Solar reduces mid-day loads but the duck-ramp into peak tariff (14:00) is the cost driver at industrial scale. BESS must be at high SOC by 14:00, then discharge consistently from 14:00 onwards. At RM 97.06/kW, every 10 kW over the MD limit costs approximately RM 970/month. Missing one high-demand tick (e.g. 14:30 at 902 kW) and holding costs more than discharging sub-optimally across 3 ticks.

## Priority
**CRITICAL**
