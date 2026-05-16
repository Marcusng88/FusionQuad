import assert from "node:assert/strict";
import test from "node:test";

import {
  createSimulationViewModel,
  mergeSimulationSnapshot,
} from "./live-simulation.ts";
import type { SimulationApiState } from "../types.ts";

function makeSnapshot(
  overrides: Partial<SimulationApiState> = {},
): SimulationApiState {
  return {
    session_id: "session-1",
    status: "paused",
    day_type: "weekday",
    current_interval: 1,
    total_intervals: 48,
    current_time: "2025-12-31T14:00:00",
    battery_soc: 0.63,
    bess_capacity_kwh: 750,
    baseline_load: 920,
    actual_load: 800,
    forecast_kw: 930,
    tariff_window: "PEAK",
    total_savings_rm: 14559,
    shave_percentage: 100,
    within_limit_ticks: 1,
    decision_log: [
      {
        timestamp: "2025-12-31 14:00",
        perceive: "Grid import 800kW - within 800kW MD limit",
        reason: "BESS SoC at 63%, sufficient for 70kW discharge",
        act: "Dispatch 70kW -> SOC drops to 63%",
        evaluate: {
          delta_eval: {
            shave_kw: 120,
            interval_savings_rm: 9706,
          },
        },
      },
    ],
    agent_trace: [
      {
        timestamp: "2025-12-31 14:00",
        agent: "Forecasting Agent",
        decision: "Forecast next 6 intervals",
        reason: "Rolling GRU forecast generated with confidence 80%.",
        action: "Predicted next import at 930 kW",
      },
    ],
    last_dispatch_kw: 70,
    md_limit_kw: 800,
    dispatch_action: {
      action: "discharge",
      duration_min: 30,
      discharge_kw: 70,
    },
    sizing_recommendation: {
      recommended_bess_capacity_kwh: 900,
      recommended_solar_capacity_kwp: 350,
      estimated_peak_reduction_kw: 120,
      estimated_monthly_savings_rm: 11647.2,
      rationale: "Recommendation generated from historical breaches.",
    },
    ...overrides,
  };
}

test("mergeSimulationSnapshot builds live chart points and KPI summary", () => {
  const initial = createSimulationViewModel();
  const next = mergeSimulationSnapshot(initial, makeSnapshot());

  assert.equal(next.sessionId, "session-1");
  assert.equal(next.history.length, 1);
  assert.equal(next.history[0]?.optimized_grid_import_kw, 800);
  assert.equal(next.history[0]?.battery_power_kw, -70);
  assert.equal(next.summary.original_md_kw, 920);
  assert.equal(next.summary.optimized_md_kw, 800);
  assert.equal(next.summary.final_soc_percent, 63);
  assert.equal(next.summary.md_savings_rm, 14559);
  assert.equal(next.decisionLogs[0]?.agent, "Auditor Agent");
  assert.equal(next.agentTrace[0]?.agent, "Forecasting Agent");
  assert.equal(next.forecastConfidence, 0.8);
  assert.equal(next.sizingRecommendation?.recommended_bess_capacity_kwh, 900);
  assert.match(next.decisionLogs[0]?.action ?? "", /Dispatch 70kW/);
});

test("mergeSimulationSnapshot replaces duplicate interval updates during polling", () => {
  const first = mergeSimulationSnapshot(createSimulationViewModel(), makeSnapshot());
  const updated = mergeSimulationSnapshot(
    first,
    makeSnapshot({
      actual_load: 790,
      total_savings_rm: 15529.6,
      decision_log: [],
    }),
  );

  assert.equal(updated.history.length, 1);
  assert.equal(updated.history[0]?.optimized_grid_import_kw, 790);
  assert.equal(updated.summary.optimized_md_kw, 790);
  assert.equal(updated.summary.md_savings_rm, 15529.6);
});
