# Multi-Agent System Audit Review

_Verification of `BESS_SYSTEM_AUDIT.md` claims against current codebase + additional multi-agent design flaws._

---

## Part A — Verification of BESS_SYSTEM_AUDIT.md (8 issues)

| # | Claim | Status | Evidence |
|---|-------|--------|----------|
| 1 | MD override drives all PEAK dispatch | **CONFIRMED** | `controller/node.py:252-270` exact code match; dispatch log numbers match `baseline - 800 + 15` formula |
| 2 | MD override has no SOC budget awareness | **CONFIRMED** | Override only checks `battery_soc > reserve_soc + 0.05` — no remaining-PEAK-ticks math |
| 3 | Planner `target_soc_end` + MILP consistent but overridden | **CONFIRMED** | MILP applies `soc[n-1] >= target_soc_end` in `solver.py:142`, but controller MD override (`node.py:265-270`) rewrites `forced_action` regardless |
| 4 | Battery capacity insufficient (420 vs 555 kWh) | **CONFIRMED** | Math holds: `(0.62-0.20)×1000=420 kWh`, dispatch sum `(169+253+321+367)×0.5=555 kWh` |
| 5 | No PEAK-window horizon | **CONFIRMED** | `solver.py:111` uses `n_intervals = len(load_forecast)` = 6 (3 h); `planner/__init__.py:23-55` `get_forecast_context()` has no `remaining_peak_ticks` field |
| 6 | Forecast direction wrong at critical tick | **CONFIRMED (data-dependent)** | Log shows 6-step forecast from 14:00 was declining while actual spiked at 16:00 |
| 7 | `MAX_CHARGE_KW = 50` hardcoded | **CONFIRMED** | `solver.py:49` literal constant, no env/state override; `max_discharge_kw` IS state-driven (`controller/node.py:185`) — asymmetric |
| 8 | `actual_discharge_kw` field wrong during charge | **CONFIRMED** | `controller/node.py:120,126` `actual_kw = power_kw` for both branches → charge ticks log nonzero discharge |

**All 8 audit claims still exist in current code.**

---

## Part B — Additional Multi-Agent Design Flaws

### B1 — Auditor LLM call is redundant (waste)
**File:** `auditor/agent.py:236-272`
Deterministic `evaluate_rules` + `evaluate_delta` run **before** the deep agent is invoked. Agent is then asked to call those same tools and produce JSON. If parse fails, fallback `_generate_llm_reasoning` runs anyway. Net effect: deterministic eval is authoritative; the LLM call adds latency + tokens for almost nothing.
**Fix:** drop the per-tick deep-agent call; keep only the deterministic eval (LLM optional, gated on `should_run_llm`).

---

### B2 — Workflow is single-pass, no in-day feedback loop
**File:** `agents/workflow.py:29-36`
Linear edges: `data_loader → forecast/tariff → planner → controller → auditor → END`. Auditor never feeds back to planner in-day. Experience file is written at EOD only. **No tick-to-tick learning within the same day.** When tick 8 burns too much SOC, tick 9 planner has no signal that the budget is gone.
**Fix:** add `auditor → planner` edge with a "remaining_peak_ticks + soc_budget_kw" handoff, OR move budget logic into a dedicated supervisor node.

---

### B3 — MILP horizon mismatch with PEAK window
**File:** `optimization/solver.py:111`, `forecast.py` (`horizon=6`)
MILP only sees what forecast emits (6 steps = 3 h). PEAK = 8 h. MILP cannot reason about saving SOC for ticks beyond horizon. The minimax objective `peak_demand >= load[i] - power[i]` is computed over 6 ticks only — globally suboptimal.
**Fix:** extend forecast horizon to remaining PEAK ticks (max 16) for the MILP only, OR add a SOC-budget terminal constraint computed from full-PEAK aggregate.

---

### B4 — Planner output `shave_kw` is dead code during PEAK
**File:** `controller/node.py:258`
MD override uses `baseline_load - md_limit_kw + 15.0`, never `optimization_strategy["shave_kw"]`. Planner's strategy file reads, experience reads, Tavily holiday checks all influence `shave_kw` — which is then ignored.
**Fix:** override should read `shave_kw` from planner if planner already accounted for SOC budget; otherwise use a derived value.

---

### B5 — Controller agent may skip MILP entirely
**File:** `controller/node.py:213-247`
Agent is told to call `milp_optimizer` but is free not to. If `structured_response` returns directly, `_local_milp_fallback` (line 239) only runs on exception. Normal happy path can yield agent-decided dispatch with **no MILP ever invoked** — then override fires anyway. Wastes the entire optimization layer most ticks.
**Fix:** call MILP unconditionally outside the agent loop; pass result into the agent prompt as a recommendation, not a tool.

---

### B6 — Two strategy taxonomies coexist
Files:
- `strategies/Strategy of Battery Action.md` (T0-T5/S0-S3/D0-D4/B0-B5/A0-A8 code system, ~460 lines)
- `planner/prompts/system.md` (free-form `strategy_name` + `shave_kw` JSON)

Planner output schema uses `strategy_name` strings ("aggressive_peak_shaving"). The code-table file uses A-codes. No bridge. Planner reads both, picks one, agent confusion likely. Token cost of loading the 460-line code table every tick is significant.
**Fix:** pick one taxonomy. If A-codes win, add a deterministic state→A-code mapper instead of LLM lookup.

---

### B7 — Tariff window check in override has silent failure mode
**File:** `controller/node.py:181-182,253`
```python
tariff = state.get("tariff") or {}
tariff_window = tariff.get("window") or "OFF_PEAK"
```
Default `OFF_PEAK` disables the MD override silently. If tariff node fails or skipped (parallel edge), override never fires during actual PEAK.
**Fix:** raise on missing tariff, or default to `PEAK` (fail-safe direction for MD protection).

---

### B8 — `reserve_soc_pct` default mismatch (planner vs override)
**Files:** `planner/node.py:121` (fallback) → 0.30, `solver.py:48` → 0.20, `controller/node.py:252` → 0.25
Three different reserve defaults across nodes. MD override threshold `reserve_soc + 0.05 = 0.30` when strategy missing → blocks override even when planner wanted aggressive shaving. Cross-agent contract not enforced.
**Fix:** single constant in `state.py` or config.

---

### B9 — `forecast_kw` vs `baseline_load` ambiguity
**File:** `controller/node.py:188-191`
```python
forecast_kw = forecast_values[0] if forecast_values else 0.0
baseline_load = state.get("baseline_load")
if baseline_load is None:
    baseline_load = forecast_kw
```
Override uses `baseline_load` (actual CSV reading injected by simulation). In a real deployment without CSV oracle, `baseline_load` would fall back to `forecast_kw` — wrong-direction forecast (Issue 6) then becomes load-of-truth. The system has a hidden dependency on the simulation harness providing ground truth.
**Fix:** document the boundary; treat any production path with `baseline_load = forecast_kw` as unsafe.

---

### B10 — Auditor cannot warn about EOD SOC depletion before it happens
`auditor/evaluation.py` flags SOC violation **after** the tick. By then the battery is empty for the worst tick. No predictive `evaluate_budget_tool`.
**Fix:** new pre-dispatch evaluator: given remaining PEAK ticks + current SOC + forecast peaks, predict whether the current discharge will leave a future tick exposed.

---

### B11 — Forecast confidence is uninformative
**File:** `forecast.py` (logged 0.80 throughout 04-07 sim)
Confidence is static (validation MAPE), not spike-aware. Planner reads it as "high confidence" while the forecast direction was wrong. Should be derived from short-term volatility or model disagreement, not historical MAPE.

---

## Part C — Multi-Agent Architecture Anti-Patterns

Best practice references (LangGraph, deepagents, MPC literature):

1. **Single source of truth for shared constants** — `MIN_SOC`, `MAX_SOC`, `MAX_CHARGE_KW`, `reserve_soc_pct` should live in one config module, not duplicated across solver/controller/planner.
2. **Override layers must respect optimizer output** — current override is a safety bypass that supersedes the optimizer's foresight. Either the optimizer is trusted (override absent) or it's not (optimizer removed). Hybrid is worst-of-both.
3. **Receding horizon = horizon ≥ longest controlled-cost window** — MILP horizon (3 h) < PEAK billing window (8 h) violates MPC's basic assumption. Fix horizon OR add terminal cost approximation.
4. **Feedback loop required for adaptive systems** — strict DAG (`workflow.py`) makes the system reactive only. Auditor → Planner edge is missing.
5. **LLM as last resort, not default tool caller** — using deep agents to wrap deterministic MILP + evaluators wastes tokens. Use LLM where reasoning is needed (strategy selection, experience interpretation), not for arithmetic.

---

## Part D — Priority Fix Order (Aligned with Problem Statement)

Problem statement asks for: **forecast demand + shift loads + reduce MD bill + simulate savings**. Critical path:

| Priority | Fix | Audit ref | Effort |
|----------|-----|-----------|--------|
| P0 | Add SOC budget cap to MD override | Issue 2, B3 | 10 lines in `controller/node.py` |
| P0 | Extend MILP horizon to full PEAK window | Issue 5, B3 | forecast.py + solver.py |
| P1 | Single config for reserve_soc/min_soc/charge_max | Issue 7, B8 | new `config.py` |
| P1 | Add `remaining_peak_ticks` + `soc_budget_kw` to planner context | Issue 5, B2 | `planner/__init__.py:23` |
| P2 | Auditor → Planner feedback edge | B2 | workflow.py + state field |
| P2 | Bypass redundant auditor LLM call | B1 | gate on `should_run_llm` |
| P3 | Fix `actual_discharge_kw` for charge action | Issue 8 | 2 lines in `mock_inverter_dispatch` |
| P3 | Tariff window fail-safe default | B7 | 1 line |
| P3 | Holiday detection cache (Tavily) | implicit | planner |

---

## Part E — What's NOT a Flaw (Working as Designed)

- **MILP minimax formulation** — correct for peak shaving (`peak_demand >= load[i] - power[i]`).
- **Parallel forecast/tariff edges** — both independent, correct.
- **Filesystem-scoped CompositeBackend for planner/auditor** — good security pattern.
- **Deterministic `evaluate_rules` + `evaluate_delta` running first in auditor** — correct guard; the redundant LLM call (B1) is the issue, not the deterministic eval.
- **`OutputFormatGuardMiddleware` is non-blocking** — correct design (warn, don't fail).

---

## Conclusion

All 8 issues in `BESS_SYSTEM_AUDIT.md` are real and present in current code. Additionally found 11 multi-agent design flaws (B1–B11). Root cause of RM 0 MD savings is the **single-tick override with no horizon awareness** combined with **MILP horizon shorter than the cost window**. Fixing P0 items (Issue 2 + Issue 5 / B3) is the minimum path to actual MD reduction.
