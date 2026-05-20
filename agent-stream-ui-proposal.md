# Agent Stream UI Proposal

---

## Layout: Tick Navigator + 3 Agent Cards

One tick shown at a time. Arrow buttons to navigate between ticks.
Each tick has 3 cards side by side. Each card has a Details button → popup.

```
┌─ Agent Stream ──────────────────────────────────────────────────┐
│                                                                  │
│   ◀   Tick 3 / 7  ·  15:30  ·  WEEKEND  ·  within limit ✅  ▶  │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  🧠 PLANNER  │  │ ⚡CONTROLLER │  │  🔍 AUDITOR  │          │
│  │              │  │              │  │              │          │
│  │ Holiday Surge│  │   [ HOLD ]   │  │ Safety  ✅   │          │
│  │              │  │              │  │              │          │
│  │ Shave  0 kW  │  │   0 kW       │  │ Shave   ⚠️   │          │
│  │ MD   800 kW  │  │   SoC: 50%   │  │ 0 kW shaved  │          │
│  │ Conf   0.46  │  │              │  │ Conf   0.86  │          │
│  │              │  │              │  │              │          │
│  │ [  Details  ]│  │ [  Details  ]│  │ [  Details  ]│          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Popup — when user clicks Details on Planner card

```
┌─ Planner · Tick 3 · 15:30 ──────────────────────────────────┐
│                                                               │
│  Strategy     Holiday Surge                                  │
│  Shave        0.0 kW                                         │
│  MD Limit     800 kW                                         │
│  Reserve SOC  30%                                            │
│  Target SOC   52%                                            │
│  Confidence   ████████░░  0.46                               │
│                                                               │
│  Rationale                                                    │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ Simulation time is 16:00 on 2025-05-31 (Saturday).   │   │
│  │ Tariff Window=WEEKEND. Load forecast 679–743 kW is   │   │
│  │ below the 800 kW MD limit so no shaving is needed.   │   │
│  │ Holding SOC ≥ 30% reserve to avoid degradation.      │   │
│  │ ...                                                   │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  Constraints                                                  │
│  • reserve_30pct_soc                                         │
│  • never_discharge_below_10pct_soc                           │
│  • thermal_hold_above_45C                                    │
│                                                               │
│  [  Show Raw JSON  ]                           [ Close ✕ ]   │
└───────────────────────────────────────────────────────────────┘
```

---

## Popup — Controller Details

```
┌─ Controller · Tick 3 · 15:30 ────────────────────────────────┐
│                                                               │
│  Action        [ HOLD ]                                      │
│  Charge kW     —                                             │
│  Discharge kW  —                                             │
│  Duration      30 min                                        │
│  SoC After     50.0%                                         │
│                                                               │
│                                              [ Close ✕ ]    │
└───────────────────────────────────────────────────────────────┘
```

---

## Popup — Auditor Details

```
┌─ Auditor · Tick 3 · 15:30 ───────────────────────────────────┐
│                                                               │
│  Safety     ✅  Passed                                       │
│  Shave      ⚠️  0 kW — load below MD limit                  │
│  Confidence ████████████████░░░░  0.86                       │
│                                                               │
│  Reasoning                                                    │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ Safety passed: no SOC/temperature/cycle violations.  │   │
│  │ Battery SOC=0.5, temp_increase=0.1°C. Performance   │   │
│  │ was ineffective: baseline=590 kW, actual=590 kW,    │   │
│  │ shave=0 kW. WEEKEND tariff gives no MD incentive.   │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  Recommendation                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ Keep HOLD on WEEKEND when load < md_limit_kw.        │   │
│  │ Switch to discharge only when forecast shows MD risk.│   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│                                              [ Close ✕ ]    │
└───────────────────────────────────────────────────────────────┘
```

---

## Summary

- `◀ ▶` arrows navigate ticks (1 through N)
- 3 cards always visible side by side per tick
- Cards show only key metrics (compact)
- `Details` button on each card opens popup with full rationale/reasoning text
- `Show Raw JSON` inside popup for debug — not visible by default
