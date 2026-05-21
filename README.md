# FusionQuad

BESS (Battery Energy Storage System) peak-shaving simulation platform built for Recharge 2026. A multi-agent LangGraph backend orchestrates an intelligent dispatch pipeline; a Next.js frontend streams agent output in real time.

---

## What It Does

Simulates a commercial BESS optimising electricity costs under Malaysian time-of-use tariffs. The system:

- Forecasts load using GRU (trained)
- Plans a dispatch strategy (peak shaving, off-peak valley fill, solar duck curve, holiday surge)
- Executes tick-by-tick charge/discharge decisions via an LP solver
- Audits results and writes end-of-day experience logs
- Streams every agent decision to a live dashboard with power/SOC charts

---

## Architecture

```
Frontend (Next.js)
    └── SSE stream ──► FastAPI
                          └── LangGraph workflow
                                ├── Planner       — picks strategy from .md files
                                ├── DataLoader    — CSV ingestion, feature engineering
                                ├── Tariff        — time-of-use rate lookup
                                ├── Controller    — tick-by-tick dispatch decisions
                                ├── Optimization  — PuLP LP solver (MILP)
                                └── Auditor       — scores plan, writes experience log
```

**State** flows through a single `TypedDict` (`app/agents/state.py`) across all nodes.

**ML models** (`app/ml/`):
- `gru.py` / `gru_attention.py` — PyTorch GRU with attention (trained weights in `models/`)

**Tariff strategies** (`backend/strategies/*.md`) — Markdown docs injected as context into the planner LLM.

---

## Prerequisites

- Python 3.11+ with [uv](https://github.com/astral-sh/uv)
- Node.js 20+ with npm
- API keys: `ANTHROPIC_API_KEY` (required), optional `GOOGLE_API_KEY`

---

## Setup

### Backend

```bash
cd backend
cp .env.example .env          # add ANTHROPIC_API_KEY
uv sync                       # install dependencies
uv run uvicorn app.main:app --reload   # starts on :8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                   # starts on :3000
```

Open `http://localhost:3000`.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required. Claude API key |
| `PLANNER_MODEL` | `claude-sonnet-4-6` | LLM for planner agent |
| `CONTROLLER_MODEL` | `claude-sonnet-4-6` | LLM for controller agent |
| `AUDITOR_MODEL` | `claude-sonnet-4-6` | LLM for auditor agent |
| `BACKEND_CORS_ORIGINS` | `http://localhost:3000` | Frontend origin |
| `TAVILY_API_KEY` | — | Optional. Planner agent search tools |

---

## Commands

### Backend (`backend/`)

```bash
uv run uvicorn app.main:app --reload   # dev server
uv run pytest                          # all tests
uv run pytest tests/test_agents.py    # single file
uv run python compare_models.py       # benchmark GRU
uv run python train_gru.py            # retrain GRU weights
```

### Frontend (`frontend/`)

```bash
npm run dev     # dev server
npm run build   # production build
npm run lint    # ESLint
```

---

## Simulation Scenarios

| Scenario | Description |
|---|---|
| `weekday` | Standard commercial load profile |
| `large_weekday` | High-demand weekday |
| `holiday` | Reduced base load with surge risk |
| `solar_duck_curve` | Midday solar export, evening ramp |

---

## Key Metrics

- **MD (Maximum Demand)** — peak kW in billing period; drives demand charge
- **Peak compliance rate** — % of peak ticks within MD limit
- **Battery Used (kWh)** — `Σ |battery_power_kw| × 0.5h` across all ticks
- **MD Savings (RM)** — `(original_MD − optimized_MD) × tariff_rate`

---

## Project Structure

```
FusionQuad/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangGraph nodes (planner, controller, auditor…)
│   │   ├── api/v1/          # FastAPI routers
│   │   ├── ml/              # GRU
│   │   ├── schemas/         # Pydantic models
│   │   └── services/        # BatteryManager, SimulationService, TickLogger
│   ├── models/              # Trained GRU weights
│   ├── strategies/          # Tariff strategy .md files
│   └── tests/
└── frontend/
    ├── app/                 # Next.js app router
    └── features/dashboard/  # Live dashboard, charts, agent stream panel
```
