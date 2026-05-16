import {
  DEFAULT_DEMAND_LIMIT_KW,
} from "../data/day-scenarios.ts";
import type {
  DecisionLog,
  EnergyPoint,
  SimulationApiState,
  SimulationDayType,
  SimulationDispatchAction,
  SimulationSummary,
  SimulationViewModel,
} from "../types.ts";

export function createSimulationViewModel(
  dayType: SimulationDayType = "weekday",
): SimulationViewModel {
  return {
    sessionId: null,
    status: "idle",
    dayType,
    history: [],
    summary: emptySummary(),
    decisionLogs: [],
    currentInterval: 0,
    totalIntervals: 0,
    currentTimeLabel: "Awaiting start",
    forecastKw: null,
    forecastConfidence: null,
    batterySocPercent: 50,
    bessCapacityKwh: 500,
    totalSavingsRm: 0,
    shavePercentage: 0,
    withinLimitTicks: 0,
    mdLimitKw: DEFAULT_DEMAND_LIMIT_KW,
    lastDispatchKw: 0,
    agentTrace: [],
    scenarios: [],
  };
}

export function mergeSimulationSnapshot(
  current: SimulationViewModel,
  snapshot: SimulationApiState,
): SimulationViewModel {
  const mdLimitKw = snapshot.md_limit_kw || DEFAULT_DEMAND_LIMIT_KW;
  const point = buildEnergyPoint(snapshot, mdLimitKw);
  const history = point ? upsertHistoryPoint(current.history, point) : current.history;

  return {
    sessionId: snapshot.session_id,
    status: snapshot.status,
    dayType: normalizeDayType(snapshot.day_type),
    history,
    summary: buildSummary(history, snapshot),
    decisionLogs: mapDecisionLog(snapshot.decision_log),
    agentTrace: snapshot.agent_trace ?? [],
    currentInterval: snapshot.current_interval,
    totalIntervals: snapshot.total_intervals,
    currentTimeLabel: formatCurrentTime(snapshot.current_time),
    forecastKw: snapshot.forecast_kw,
    forecastConfidence: deriveForecastConfidence(snapshot),
    batterySocPercent: Math.round(snapshot.battery_soc * 100),
    bessCapacityKwh: snapshot.bess_capacity_kwh,
    totalSavingsRm: snapshot.total_savings_rm,
    shavePercentage: snapshot.shave_percentage,
    withinLimitTicks: snapshot.within_limit_ticks,
    mdLimitKw,
    lastDispatchKw: snapshot.last_dispatch_kw,
    scenarios: snapshot.scenarios ?? [],
  };
}

function buildEnergyPoint(
  snapshot: SimulationApiState,
  mdLimitKw: number,
): EnergyPoint | null {
  if (
    snapshot.current_time == null ||
    snapshot.baseline_load == null ||
    snapshot.actual_load == null
  ) {
    return null;
  }

  const timestamp = formatChartTime(snapshot.current_time);
  const batteryPowerKw = mapDispatchPower(
    snapshot.dispatch_action,
    snapshot.last_dispatch_kw,
  );

  return {
    timestamp,
    load_kw: snapshot.baseline_load,
    solar_kw: 0,
    original_grid_import_kw: snapshot.baseline_load,
    optimized_grid_import_kw: snapshot.actual_load,
    battery_power_kw: batteryPowerKw,
    battery_soc_percent: Math.round(snapshot.battery_soc * 100),
    shifted_load_kw: Math.max(snapshot.baseline_load - snapshot.actual_load - Math.abs(Math.min(batteryPowerKw, 0)), 0),
    demand_limit_kw: mdLimitKw,
    is_peak_period: (snapshot.tariff_window || "").toUpperCase().includes("PEAK"),
  };
}

function upsertHistoryPoint(
  history: EnergyPoint[],
  nextPoint: EnergyPoint,
): EnergyPoint[] {
  const index = history.findIndex((point) => point.timestamp === nextPoint.timestamp);
  if (index === -1) {
    return [...history, nextPoint];
  }

  const updated = [...history];
  updated[index] = nextPoint;
  return updated;
}

function buildSummary(
  history: EnergyPoint[],
  snapshot: SimulationApiState,
): SimulationSummary {
  if (history.length === 0) {
    return {
      ...emptySummary(),
      final_soc_percent: Math.round(snapshot.battery_soc * 100),
    };
  }

  const originalMd = Math.max(...history.map((point) => point.original_grid_import_kw));
  const optimizedMd = Math.max(...history.map((point) => point.optimized_grid_import_kw));
  const peakReductionKw = Math.max(originalMd - optimizedMd, 0);
  const batteryEnergyUsedKwh = Math.round(
    history.reduce((sum, point) => sum + Math.abs(point.battery_power_kw) * 0.5, 0),
  );
  const shiftedLoadKwh = Math.round(
    history.reduce((sum, point) => sum + point.shifted_load_kw * 0.5, 0),
  );

  return {
    original_md_kw: originalMd,
    optimized_md_kw: optimizedMd,
    peak_reduction_kw: peakReductionKw,
    original_md_cost_rm: Math.round(originalMd * (snapshot.md_rate || 97.06)),
    optimized_md_cost_rm: Math.round(optimizedMd * (snapshot.md_rate || 97.06)),
    md_savings_rm: snapshot.total_savings_rm || Number((peakReductionKw * (snapshot.md_rate || 97.06)).toFixed(2)),
    battery_energy_used_kwh: batteryEnergyUsedKwh,
    final_soc_percent: Math.round(snapshot.battery_soc * 100),
    shifted_load_kwh: shiftedLoadKwh,
  };
}

function mapDecisionLog(entries: Array<Record<string, unknown>>): DecisionLog[] {
  return entries.map((entry) => {
    const evaluate = asRecord(entry.evaluate);
    const deltaEval = asRecord(evaluate.delta_eval);
    const timestamp = typeof entry.timestamp === "string" ? entry.timestamp : "Unknown";
    const reason = typeof entry.reason === "string" ? entry.reason : "No reasoning recorded.";
    const action = typeof entry.act === "string" ? entry.act : "No action recorded.";
    const decision = typeof entry.perceive === "string" ? entry.perceive : "Simulation decision recorded.";

    return {
      timestamp,
      agent: "Auditor Agent",
      decision,
      reason,
      action,
      expected_reduction_kw: numberOrUndefined(deltaEval.shave_kw),
      estimated_saving_rm: numberOrUndefined(deltaEval.interval_savings_rm),
    };
  });
}

function deriveForecastConfidence(snapshot: SimulationApiState): number | null {
  const forecastEntry = snapshot.agent_trace?.find(
    (entry) => entry.agent === "Forecasting Agent",
  );
  if (!forecastEntry) {
    return null;
  }

  const match = forecastEntry.reason.match(/(\d+)%/);
  if (!match) {
    return null;
  }

  return Number(match[1]) / 100;
}

function mapDispatchPower(
  dispatchAction: SimulationDispatchAction,
  lastDispatchKw: number,
) {
  const action = dispatchAction?.action || "hold";
  if (action === "discharge") {
    return -Math.abs(lastDispatchKw);
  }
  if (action === "charge") {
    return Math.abs(lastDispatchKw);
  }
  return 0;
}

function normalizeDayType(dayType: string): SimulationDayType {
  if (dayType === "holiday" || dayType === "solar_duck_curve" || dayType === "large_weekday") {
    return dayType;
  }
  return "weekday";
}

function formatCurrentTime(currentTime: string | null) {
  if (!currentTime) {
    return "Awaiting first interval";
  }

  const date = new Date(currentTime);
  if (Number.isNaN(date.getTime())) {
    return currentTime;
  }

  return date.toLocaleString("en-MY", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "short",
  });
}

function formatChartTime(currentTime: string) {
  const date = new Date(currentTime);
  if (Number.isNaN(date.getTime())) {
    return currentTime;
  }

  return date.toLocaleTimeString("en-MY", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function numberOrUndefined(value: unknown) {
  return typeof value === "number" ? value : undefined;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function emptySummary(): SimulationSummary {
  return {
    original_md_kw: 0,
    optimized_md_kw: 0,
    peak_reduction_kw: 0,
    original_md_cost_rm: 0,
    optimized_md_cost_rm: 0,
    md_savings_rm: 0,
    battery_energy_used_kwh: 0,
    final_soc_percent: 50,
    shifted_load_kwh: 0,
  };
}
