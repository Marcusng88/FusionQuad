---
name: strategy-selector
description: Determines which /strategies/ file to read_file based on tariff window, day type, and facility. Use when deciding which strategy file to load for a planning interval.
---

# Strategy Selector

## When to Use
When you need to decide which strategy file to read before computing shave_kw and dispatch action.

## Decision Tree

Check conditions in order — solar facility check comes BEFORE generic weekday PEAK:

```
1. facility in {SoL, Mi2}  OR  day_type == "solar_duck_curve"
   → read_file("/strategies/solar_duck_curve.md")

2. tariff_window == "PEAK" AND day_type == "weekday"
   → read_file("/strategies/aggressive_peak_shaving.md")

3. tariff_window == "OFF_PEAK"  OR  time in 12:00–14:00 (T5 pre-peak)
   → read_file("/strategies/offpeak_valley_fill.md")

4. day_type == "holiday"  OR  day_type == "weekend"
   → read_file("/strategies/holiday_surge.md")

5. ALWAYS — SOC/cycle/temperature constraints baseline
   → read_file("/strategies/general_bess_guidelines.md")

6. Tick-level action code lookup (T/S/D/B → A0–A8)
   → read_file("/strategies/Strategy of Battery Action.md")
```

Rules 1–4 are mutually exclusive — pick the first that matches.
Rules 5 and 6 apply on top of whichever scenario file was selected.

## Action Code Quick Reference

| Code | Meaning | Trigger |
|------|---------|---------|
| A0 | Forced charge 100% | B0 (SoC < 10%), any time |
| A1 | Low charge <30% | Off-peak, SoC B2-B3, low demand |
| A2 | Medium charge 30-70% | Off-peak / T1, SoC B1-B2 |
| A3 | High charge >70% | T2 night, SoC B0-B1 (valley fill) |
| A4 | Hold / no action | SoC optimal B3, demand low-medium |
| A5 | Low discharge <30% | T0 peak, D2-D3, SoC B2-B3 |
| A6 | Medium discharge 30-70% | T0 peak, D3-D4, SoC B2-B4 |
| A7 | High discharge >70% | T0 peak, D4 critical, SoC B3-B4 |
| A8 | Forced discharge 100% | B5 (SoC > 95%), D4 emergency, grid event |

## Condition Codes

**Time (T):** T0=Peak 14-22h weekday · T1=Morning 8-14h · T2=Night 22-8h · T3=Weekend · T4=Holiday · T5=Pre-peak 12-14h  
**Solar (S):** S0=None · S1=Weak <200 W/m² · S2=Medium 200-600 · S3=Strong >600  
**Demand (D):** D0=<40% MD · D1=40-60% · D2=60-80% · D3=80-95% · D4=≥95% MD (critical)  
**Battery (B):** B0=<10% SoC · B1=10-20% · B2=20-50% · B3=50-80% · B4=80-95% · B5=>95%

## Full Action Lookup
For complete T/S/D/B → action mapping tables: `read_file("/strategies/Strategy of Battery Action.md")`
