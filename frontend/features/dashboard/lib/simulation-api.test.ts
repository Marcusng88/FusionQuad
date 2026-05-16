import assert from "node:assert/strict";
import test from "node:test";

import { startSimulation } from "./simulation-api.ts";

test("startSimulation posts the selected day and battery settings", async () => {
  const calls: Array<{ input: RequestInfo | URL; init?: RequestInit }> = [];
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async (input, init) => {
    calls.push({ input, init });

    return new Response(
      JSON.stringify({
        session_id: "session-1",
        status: "paused",
        day_type: "holiday",
        current_interval: 0,
        total_intervals: 48,
        current_time: null,
        battery_soc: 0.5,
        bess_capacity_kwh: 1000,
        baseline_load: null,
        actual_load: null,
        forecast_kw: null,
        tariff_window: null,
        total_savings_rm: 0,
        shave_percentage: 0,
        within_limit_ticks: 0,
        decision_log: [],
        agent_trace: [],
        last_dispatch_kw: 0,
        md_limit_kw: 800,
        dispatch_action: null,
        sizing_recommendation: null,
      }),
      {
        status: 200,
        headers: { "content-type": "application/json" },
      },
    );
  };

  try {
    await startSimulation(
      {
        dayType: "holiday",
        bessCapacityKwh: 1000,
        batterySoc: 0.5,
      },
      "http://localhost:8000",
    );
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.input, "http://localhost:8000/api/v1/simulation/start");
  assert.equal(calls[0]?.init?.method, "POST");
  assert.deepEqual(JSON.parse(String(calls[0]?.init?.body)), {
    day_type: "holiday",
    bess_capacity_kwh: 1000,
    battery_soc: 0.5,
    use_deep_agent: true,
  });
});
