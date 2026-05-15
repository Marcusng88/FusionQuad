# FusionQuad Energy Agentic AI

## Problem Statement

Malaysian C&I facilities face RM 97.06/kW Maximum Demand charges under the July 2025 TNB tariff restructure — a 3× increase from RP3. Without intelligent, predictive energy management, a single 30-minute peak excursion can generate RM 10,677+ in MD penalties for a 900 kW facility. Traditional rule-based EMS cannot handle the stochastic, multi-objective nature of modern facilities with co-located solar PV, BESS, EV chargers, and HVAC loads. Agentic AI with autonomous reasoning is the only viable path to real-time peak shaving and load optimization.

## Evidence

- TNB MV TOU tariff: RM 97.06/kW effective July 2025 (Capacity + Network charges combined)
- A 2,550 kW facility pays RM 247,503/month in MD charges — 100 kW reduction = RM 9,706 saved/month
- ESUM X Recharge Case Study Competition Theme 1 requires: load forecasting, peak identification, automated load shifting, solar/battery sizing, cost savings simulation, and dashboard
- Malaysian facilities with 944 kWp solar installations show "post-solar duck curve" — grid import spikes after 4:30 PM when solar drops but peak tariff window (2PM–10PM) is still active
- Holiday/weekend data shows 1281 kW peaks on Dec 31 2025 vs 913 kW weekday baseline — uncoordinated high-power EV charging + HVAC + manufacturing creates costly MD excursions

## Proposed Solution

Build a multi-agentic AI energy management system using LangGraph orchestration with rolling LSTM-based load forecasting and MILP-optimized BESS dispatch. The system replays historical facility load profiles (CSV) at accelerated speed, demonstrating autonomous peak shaving decisions with full explainability. A Next.js dashboard visualizes the AI's reasoning trace, before/after load curves, and quantified RM savings for competition judges and company evaluators.

## Key Hypothesis

We believe an autonomous multi-agentic AI system with rolling load forecasts will achieve greater and more consistent peak shaving than static rule-based systems, because it dynamically weighs battery SoC, tariff windows, and predicted load to make context-aware dispatch decisions. We will know we're right when the dashboard shows the optimized load curve staying consistently below the 800 kW MD limit across all facility types (weekday, weekend, holiday), with quantified RM savings and a human-readable AI reasoning trace.

## What We're NOT Building

- Real hardware integration — no BMS, inverter, or smart meter control; simulation only
- EV charger direct control — EV coordination is shown as simulated scheduling decisions in the reasoning log, not live device commands
- Production deployment infrastructure — single-machine MVP for demo, no container orchestration or cloud deployment
- True real-time system — uses historical CSV data replay, not live sensor feeds
- Carbon/ESG reporting module — Nice-to-have deferred post-competition

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|--------------|
| MD Charge Reduction | ≥RM 9,706/month per 100 kW shaved | Dashboard: optimized peak × RM 97.06/kW × 30 days |
| Peak Shave % | ≥90% of peak events shaved below 800 kW | Auditor Agent: count of 30-min intervals exceeding limit |
| Forecast Accuracy | ≥85% MAPE on rolling 30-min ahead | Backend: compare LSTM prediction vs actual from CSV |
| Demo Completion | Full day simulation runs end-to-end without error | Manual: 10-min judge demo completes all sections |
| AI Reasonability | Every dispatch decision has ≥1 reasoning log entry | Frontend: DecisionsSection renders all logged steps |

## Open Questions

- [ ] ML model architecture (LSTM vs GRU) and training hyperparameters not yet determined
- [ ] MILP solver library (PuLP vs OR-Tools) not yet selected
- [ ] LangGraph cycle checkpointing strategy for pause/resume needs design decision
- [ ] BESS degradation modeling scope (calendar vs cycle aging) not yet defined
- [ ] Tariff data (TOU windows, energy rates) not yet extracted from plan.md into backend config

---

## Users & Context

**Primary User — Competition Judge / Company Evaluator**
- **Who**: Technical judge at ESUM X Recharge hackathon OR Recharge Malaysia company representative evaluating the solution
- **Current behavior**: Reviews 10-minute demo video + technical report, asks live questions about AI reasoning and savings methodology
- **Trigger**: Opening the dashboard URL, watching load curve animation, scrolling through AI decision logs
- **Success state**: Immediately understands what the AI did, why, and how much RM was saved — without reading documentation

**Secondary User — Facility Energy Officer (Persona)**
- **Who**: Fictional C&I facility energy manager using the dashboard to simulate their own scenario
- **Current behavior**: Reviews historical load, selects BESS size, clicks "Run Optimization", reviews savings report
- **Success state**: Confident in the AI's recommendation for their facility's BESS investment decision

**Non-Users**
- Production energy operations teams — this is a simulation/demo tool, not a production EMS replacement
- End-customers (EV drivers) — they are assets to be coordinated, not users of the system

---

## Solution Detail

### Core Capabilities (MoSCoW)

| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | CSV data loader & parser (4 facility profiles) | All downstream features depend on data ingestion |
| Must | LSTM rolling forecast model (pre-trained at build time) | Core differentiation vs rule-based competitors |
| Must | LangGraph multi-agent orchestration (Planner, Forecasting, Optimization, Controller, Auditor) | Core technical deliverable per competition brief |
| Must | MILP BESS dispatch optimizer | Generates optimal, explainable dispatch plans |
| Must | Day selector with 3 showcase scenarios (Weekday 913kW, Holiday 1281kW, Solar Duck Curve) | Enables judge interaction without training |
| Must | Dashboard with 6 hero KPIs, baseline vs optimized overlay chart, AI reasoning trace | Visual deliverable per competition brief |
| Must | Simulation playback controls (Play/Pause/Step, 1x/10x/60x speed) | Core UX per PRD decisions |
| Should | BESS size slider (500–2000 kWh) with live re-optimization | Demonstrates AI's sizing intelligence |
| Should | Interactive EV charger schedule visualization | Addresses EV coordination requirement from problem statement |
| Could | kVAR/power factor correction display | Secondary metric, defer if time-constrained |
| Won't | Real hardware integration | Explicitly out of scope per user decision |

### MVP Scope

**Hackathon MVP** must demonstrate in a 10-minute judge demo:

1. Dashboard loads with baseline load curve from CSV data
2. User selects a day scenario (3 buttons)
3. User clicks "Run Optimization" or watches auto-play
4. Simulation advances through the day with rolling forecasts
5. Every 30 simulated minutes: forecast → plan → dispatch → audit
6. Dashboard updates live with: hero KPIs, overlay chart, decision logs
7. End state: full day summary with total RM savings, peak reduction %

### User Flow

```
1. Open Dashboard (localhost:3000)
       │
       ▼
2. View Hero Overview
   (6 cards: Original Peak, MD Charge, Savings, Shave%, BESS SoC, Forecast Accuracy)
       │
       ▼
3. Select Day Scenario
   [🏢 Weekday Peak] [🎄 Holiday Surge] [☀️ Solar Duck Curve]
       │
       ▼
4. (Optional) Adjust BESS Size Slider — 500 kWh to 2000 kWh
       │
       ▼
5. Click "Run Optimization" OR Enable Auto-Play
       │
       ▼
6. Watch simulation advance through 24hr day
   - Chart updates every 30 simulated minutes
   - Decision logs populate with Perceive→Reason→Act→Evaluate entries
   - Hero KPIs refresh with live calculations
       │
       ▼
7. Pause at any point to explain a specific AI decision
       │
       ▼
8. At end of day: view final savings summary
```

---

## Technical Approach

**Feasibility**: MEDIUM — multi-agent LangGraph orchestration is well understood, but LSTM training + MILP integration within hackathon timeframe is aggressive. Rolling forecast re-computation every 30 simulated minutes may create latency on lower-end hardware.

**Architecture Notes**

- **Frontend (Next.js 16 + Tailwind CSS)**: Existing dashboard structure with sidebar, hero overview, baseline section, simulation section, decisions section. Located at `frontend/`. Currently has mock data in `scenarios.ts` — needs integration with live FastAPI endpoints.
- **Backend (FastAPI)**: Existing skeleton with API router at `backend/app/`. Needs CSV loader, ML model endpoint, LangGraph orchestration engine, MILP solver integration.
- **Data (4 CSV files)**: Located at `backend/data/`. Files: `1. Load Profile (With Solar Installed) SoL.csv` (944.88 kWp), `2. Load Profile (No Solar) E.csv` (~150 kW), `3. Load Profile (No Solar) SuN.csv` (holiday ~1281 kW peak), `4. Load Profile (With Solar) Mi2.csv`.
- **ML Model**: LSTM or GRU, pre-trained on all 4 CSVs at build time. Weights stored in `backend/models/`. Loaded at FastAPI startup. Rolling forecast runs on each simulation step.
- **LangGraph StateGraph**: 5 agents as graph nodes. State carries `current_load`, `battery_soc`, `forecast`, `tariff_window`, `dispatch_plan`, `decision_logs`. Checkpointer enables pause/resume of simulation.
- **MILP Solver**: PuLP or OR-Tools. Optimization Agent node calls solver with constraints: BESS SoC limits, inverter power limits, MD threshold, tariff windows.
- **Simulation Clock**: Backend maintains a simulated time pointer into the CSV data. On "step" advance, moves forward 1×30-min interval. Auto-play mode advances every N milliseconds (configurable speed).
- **API Endpoints needed**:
  - `POST /api/v1/simulation/start` — initialize simulation with selected day, BESS size
  - `POST /api/v1/simulation/step` — advance one 30-min interval
  - `POST /api/v1/simulation/play` — start auto-play mode
  - `POST /api/v1/simulation/pause` — pause auto-play
  - `GET /api/v1/simulation/state` — current state: time, load, SoC, forecast, dispatch plan, logs
  - `GET /api/v1/forecast/summary` — pre-computed scenario summaries for day selector

**Technical Risks**

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| LSTM training takes too long / produces poor accuracy | Medium | Use GRU (faster), limit epochs, fallback to pattern projection if needed |
| LangGraph state management complexity | Medium | Pre-built scaffold with typed State definition, use built-in checkpointing |
| MILP solve time exceeds simulation step duration | Medium | Use PuLP with warm-start from previous solution (BESS dispatch changes slowly) |
| Frontend/backend latency makes auto-play feel sluggish | Low | Batch state updates, WebSocket instead of polling if needed |
| CSV date parsing edge cases (holidays, leap years) | Low | Use pandas read_csv with infer_datetime_format, explicit date column |

---

## Implementation Phases

| # | Phase | Description | Status | Parallel | Depends | PRP Plan |
|---|-------|-------------|--------|----------|---------|----------|
| 1 | Backend CSV Data Pipeline | CSV loader, parser, pandas dataframe utilities, scenario metadata extraction | pending | with 2 | - | - |
| 2 | ML Forecasting Model Training | LSTM/GRU model, train on all 4 CSVs, validate accuracy, save weights | pending | with 1 | - | - |
| 3 | LangGraph Multi-Agent Scaffold | State definition, agent nodes (Forecasting, Planner, Optimization, Controller, Auditor), edge routing, checkpointing | pending | with 4 | 1, 2 | - |
| 4 | MILP Dispatch Optimizer | PuLP/OR-Tools integration within Optimization Agent node, constraint definition, warm-start | pending | with 3 | 1 | - |
| 5 | FastAPI Simulation Endpoints | Start/step/play/pause/state endpoints, simulation clock management, background task runner | pending | - | 3, 4 | - |
| 6 | Frontend Dashboard Integration | Replace mock data with live API calls, wire simulation controls, wire hero KPIs | pending | with 7 | 5 | - |
| 7 | Frontend Charts & AI Trace | Overlay chart (baseline vs optimized), rolling decision logs UI, BESS SoC visualization | pending | with 6 | 5 | - |
| 8 | End-to-End Demo & Testing | Full day simulation run, judge demo dry-run, bug fixes | pending | - | 6, 7 | - |

### Phase Details

**Phase 1: Backend CSV Data Pipeline**
- **Goal**: All CSV data readable and queryable by simulation engine
- **Scope**: 4 CSV files parsed to DataFrame, day-level slices extractable, tariff windows mapped, kVAR exports identified
- **Success signal**: `backend/tests/test_csv_loader.py` passes with all 4 files loaded correctly, peak times match expected values

**Phase 2: ML Forecasting Model Training**
- **Goal**: Pre-trained model that generates load forecasts at ≥85% accuracy for 30-min ahead
- **Scope**: LSTM/GRU trained in Python, weights saved to `backend/models/forecast_weights.pt`, inference tested on held-out day
- **Success signal**: `backend/tests/test_forecast.py` reports MAPE ≤15% on validation set

**Phase 3: LangGraph Multi-Agent Scaffold**
- **Goal**: Runnable LangGraph graph with 5 agents connected via edges, supports checkpointing for pause/resume
- **Scope**: `AgentState` TypedDict, 5 agent nodes with placeholder logic, conditional edges, MemorySaver checkpointer
- **Success signal**: `python -m backend.app.graph.test_run` completes a single-step simulation with state persisted

**Phase 4: MILP Dispatch Optimizer**
- **Goal**: Optimization Agent produces valid BESS dispatch plan respecting SoC, inverter, and MD constraints
- **Scope**: PuLP model in Optimization Agent, objective = minimize cost, constraints: SoC bounds, max discharge rate, MD threshold, tariff window boundaries
- **Success signal**: For a known test case (910 kW peak, 800 kW limit, 500 kWh BESS), optimizer returns a feasible dispatch plan ≤1 second

**Phase 5: FastAPI Simulation Endpoints**
- **Goal**: HTTP interface that drives the simulation, usable by frontend
- **Scope**: 5 REST endpoints in `backend/app/api/v1/endpoints/simulation.py`, background task for auto-play mode, SSE or polling for state updates
- **Success signal**: `curl` commands to start/step/pause a simulation return correct state, WebSocket reconnects cleanly on pause/resume

**Phase 6: Frontend Dashboard Integration**
- **Goal**: Dashboard uses live API instead of mock data in `scenarios.ts`
- **Scope**: Replace `SCENARIOS` constant with API calls to `/api/v1/simulation/*`, wire day selector buttons, wire BESS slider, wire Play/Pause/Step controls
- **Success signal**: Selecting a day triggers API call, optimization runs, hero KPIs and chart update within 5 seconds

**Phase 7: Frontend Charts & AI Trace**
- **Goal**: Visualize the AI's decision-making and simulation progress
- **Scope**: Recharts-based overlay chart (baseline orange vs optimized green), DecisionsSection with Perceive/Reason/Act/Evaluate steps, BESS SoC area chart, timeline scrubber
- **Success signal**: Judge can scroll through a full day's worth of AI decision logs, each entry showing timestamp + reasoning text

**Phase 8: End-to-End Demo & Testing**
- **Goal**: Complete judge-ready demo without crashes or obvious errors
- **Scope**: Full dry-run of all 3 scenarios, timing of 10-min demo flow, fix all console errors and API failures
- **Success signal**: Team runs the full demo twice without intervention

### Parallelism Notes

- Phase 1 and Phase 2 can run in parallel — CSV pipeline doesn't depend on ML model
- Phase 3 and Phase 4 are sequential — Optimization Agent needs the scaffold (Phase 3) to plug into
- Phase 6 and Phase 7 are frontend tasks that can overlap — one developer works on API integration (6), another on charts (7), both depending on Phase 5
- Phase 8 is gatekept by all preceding phases — last to start

---

## Decisions Log

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| Primary users | Competition judges + company evaluators | Facility managers, energy officers | Hackathon context: demo must impress judges in 10 min, not train real operators |
| Target facility | Large C&I (900+ kW) with comparison mode | Small facility only | Large facility = bigger savings numbers = more impressive; comparison mode shows AI adaptability |
| MD limit | 800 kW | 700 kW, 900 kW, dynamic | Matches plan.md reference, catches real peaks (913 kW), round number easy to explain |
| BESS sizing | Interactive slider (500–2000 kWh) | Fixed size, auto-sizing only | Slider demonstrates AI's sizing optimization intelligence; judges can experiment live |
| AI reasoning depth | Layered (summary + detailed trace) | Single scrolling log only | Judges want overview first; technical judges want full trace; layered UX serves both |
| Forecasting approach | True rolling forecast (LSTM, one-shot per step) | Pattern projection, pre-computed | Rolling LSTM shows real ML capability; "one-shot per step" means 48 forecasts for a day, feasible |
| Forecast re-computation | Rolling — re-runs every 30 simulated minutes | One-shot at simulation start | Rolling more realistic and dynamic; re-running with each new actual data point improves accuracy |
| Optimization algorithm | MILP (PuLP/OR-Tools) | Rule-based heuristics, RL | MILP is deterministic, explainable, constraint-transparent — best for judge explainability |
| Agentic framework | LangGraph StateGraph with 5 agents | LangChain agents, custom FSM | LangGraph handles cycles + checkpointing natively; matches plan.md architecture |
| Simulation control | Hybrid (Play/Pause/Step + 1x/10x/60x) | Real-time only, step-only | Best of both: auto-play for cinematic demo, step for deep-dive on specific decisions |
| Playback mode | Day selector with showcase defaults (3 buttons) | Full calendar date picker | 3 buttons (Weekday/Holiday/Solar) simpler to implement, clearer for judges than a calendar |
| Hardware control | Simulation only | Real BMS/inverter integration | Hackathon MVP; no access to real hardware; judges expect simulation |
| EV coordination | Simulated schedule display in decision logs | Direct device control, no EV feature | Addresses competition requirement (EV listed as existing infrastructure) without over-scoped hardware |
| ML training timing | Pre-trained at build time | Train-on-upload | Pre-trained is instant at demo time; train-on-upload risks training delay/crash mid-demo |
| ML model choice | LSTM/GRU (to be determined in Phase 2) | ARIMA, Prophet | LSTM handles sequential 30-min intervals well; plan.md references LSTM/GRU |

---

## Research Summary

**Market Context**
- TNB July 2025 tariff: RM 97.06/kW MD for MV TOU customers (C2/E2), base energy 45.40 sen/kWh (+14.2%)
- Peak window: 2:00 PM–10:00 PM weekdays; off-peak: weekends + 10PM–2PM weekdays
- MD charges do NOT apply during off-peak for MV/HV customers — critical optimization window
- GITA 100% allowance for BESS/Solar PV (own consumption, MyHIJAU listed) offsets CAPEX
- SELCO mandate (Jan 2026): >1 MWac solar must include BESS — regulatory tailwind for adoption
- UK Octopus Agile tariff example: 28% consumption shifted from peak, 47% EV peak reduction — evidence that intelligent load management works

**Technical Context**
- Existing FastAPI backend skeleton at `backend/app/` with CORS configured, router in place
- Existing Next.js frontend at `frontend/` with dashboard components: baseline-section, simulation-section, decisions-section, scenarios-section, hero-overview, setup-section
- Mock scenarios in `frontend/features/dashboard/data/scenarios.ts` — needs replacement with live API
- 4 CSV load profiles in `backend/data/`: With Solar (944 kWp), No Solar weekday (~150 kW), No Solar holiday (1281 kW peak Dec 31), With Solar Mi2
- LangGraph chosen as orchestration framework per plan.md multi-agent design
- Plan.md references LangGraph cycles, checkpoints, AgentState TypedDict — architecture well-specified

---

*Generated: 2026-05-12*
*Status: DRAFT — based on grill-me session, all decisions confirmed by user*
