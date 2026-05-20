# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FusionQuad — BESS (Battery Energy Storage System) peak-shaving simulation platform. Multi-agent LangGraph backend orchestrates planner → data_loader → tariff → controller → optimization → auditor pipeline. Next.js frontend streams agent output in real time.

## Commands

### Backend (run from `backend/`)
```bash
uv run uvicorn app.main:app --reload      # dev server (port 8000)
uv run pytest                              # all tests
uv run pytest tests/test_agents.py        # single test file
uv run python compare_models.py           # benchmark GRU vs Chronos
uv run python train_gru.py                # retrain GRU weights
```

### Frontend (run from `frontend/`)
```bash
npm run dev     # dev server (port 3000)
npm run build   # production build
npm run lint    # ESLint
```

## Architecture

### Backend — `backend/`

**Entry:** `app/main.py` → FastAPI with CORS, lifespan, routers at `/api/v1/`.

**Simulation flow** (`app/services/simulation.py`, 34 KB):
1. API receives request → `SimulationService` kicks off LangGraph workflow
2. Workflow (`app/agents/workflow.py`) runs agents in sequence
3. Planner → DataLoader → Tariff → Controller → Optimization → Auditor
4. Results streamed back to frontend via SSE

**Agents** (`app/agents/`):
- `planner/node.py` — Reads load profile, picks strategy
- `data_loader/node.py` — CSV ingestion, feature engineering
- `tariff/node.py` + `tariff/rates.py` — Time-of-use rate lookup
- `controller/node.py` (15.6 KB) — LangGraph node; decides charge/discharge per tick
- `optimization/solver.py` (9.3 KB) — PuLP LP solver for optimal dispatch
- `auditor/agent.py` + `auditor/evaluation.py` — Scores the plan, writes audit report
- `state.py` — Shared `TypedDict` passed through entire graph

**Agent LLM models** (`app/agents/config.py`):
```python
PLANNER_MODEL    # env var, defaults to claude-sonnet-4-6
CONTROLLER_MODEL # env var, defaults to claude-sonnet-4-6
AUDITOR_MODEL    # env var, defaults to claude-sonnet-4-6
```

**ML models** (`app/ml/`):
- `gru.py` / `gru_attention.py` — Trained PyTorch models (weights in `models/`)
- `chronos_model.py` — Zero-shot Amazon Chronos forecasting (no training needed)

**Tariff strategies** (`strategies/*.md`) — Markdown docs fed as context to planner agent. Current: aggressive_peak_shaving, offpeak_valley_fill, solar_duck_curve, holiday_surge, general_bess_guidelines.

### Frontend — `frontend/`

**Entry:** `app/page.tsx` → `features/dashboard/live-dashboard-page.tsx` (36 KB, main component).

**Key components** (`features/dashboard/components/`):
- `agent-stream-panel.tsx` — Renders agent thought stream from SSE
- `dashboard-charts.tsx` — Recharts power/SOC time-series
- `date-time-picker.tsx` — Simulation time range picker
- Other sections: baseline, decisions, scenarios, setup, simulation

**Theme:** CSS-variable dark/light toggle, persisted in `localStorage`. Init script in `app/layout.tsx` prevents flash.

**API calls:** All go to `http://localhost:8000/api/v1/` (configured via `BACKEND_CORS_ORIGINS` env var).

## Key Conventions

- Backend uses **uv** for package management (not pip/poetry). Add deps with `uv add <pkg>`.
- Frontend uses **npm** (has both `package-lock.json` and `pnpm-lock.yaml` — prefer npm).
- Agent state flows through a single `TypedDict` in `app/agents/state.py`. Add new fields there, not as ad-hoc dicts.
- New agent nodes go in `app/agents/<name>/node.py`, wired into `workflow.py`.
- When building multi-agent logic use **LangGraph** + **deepagents**. If unsure how, load the `langgraph-fundamentals` or `deep-agents-core` skills via Skill tool.
- Tariff strategies live as `.md` files in `backend/strategies/` — edit there, not hardcoded in Python.

## Communication Style

Use caveman mode in all responses: drop articles/filler/pleasantries/hedging. Fragments OK. Technical terms exact. Code blocks unchanged. Load the `caveman` skill if needed.

# Behavioral Guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.