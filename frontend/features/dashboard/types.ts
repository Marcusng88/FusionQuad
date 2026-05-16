export type EnergyPoint = {
  timestamp: string;
  load_kw: number;
  solar_kw: number;
  original_grid_import_kw: number;
  optimized_grid_import_kw: number;
  battery_power_kw: number;
  battery_soc_percent: number;
  shifted_load_kw: number;
  demand_limit_kw: number;
  is_peak_period: boolean;
};

export type SimulationSummary = {
  original_md_kw: number;
  optimized_md_kw: number;
  peak_reduction_kw: number;
  original_md_cost_rm: number;
  optimized_md_cost_rm: number;
  md_savings_rm: number;
  battery_energy_used_kwh: number;
  final_soc_percent: number;
  shifted_load_kwh: number;
};

export type DecisionAgent =
  | "Forecasting Agent"
  | "Planner Agent"
  | "Optimization Agent"
  | "Controller Agent"
  | "Auditor Agent";

export type DecisionLog = {
  timestamp: string;
  agent: DecisionAgent;
  decision: string;
  reason: string;
  action: string;
  expected_reduction_kw?: number;
  estimated_saving_rm?: number;
};

export type ScenarioMetadata = {
  day_type: string;
  available_start: string;
  available_end: string;
  facility_name: string;
  solar_installed_kwp: number;
  total_rows: number;
};

export type ScenarioKey =
  | "baseline"
  | "solarOnly"
  | "batteryOnly"
  | "loadShiftingOnly"
  | "batteryAndShifting";

export type ScenarioAccent = "primary" | "secondary" | "tertiary";

export type ScenarioData = {
  key: ScenarioKey;
  label: string;
  blurb: string;
  accent: ScenarioAccent;
  summary: SimulationSummary;
  timeseries: EnergyPoint[];
  decisionLogs: DecisionLog[];
};

export type NavItem = {
  href: string;
  label: string;
};

export type SimulationDayType = "weekday" | "holiday" | "solar_duck_curve" | "large_weekday";

export type DateTimeRange = {
  start: string | null;
  end: string | null;
};

export type SimulationRunStatus = "idle" | "paused" | "playing" | "completed";

export type SimulationDispatchAction = {
  action?: string;
  charge_kw?: number;
  discharge_kw?: number;
  duration_min?: number;
} | null;

export type SimulationApiState = {
  session_id: string;
  status: "paused" | "playing" | "completed";
  day_type: string;
  current_interval: number;
  total_intervals: number;
  current_time: string | null;
  battery_soc: number;
  bess_capacity_kwh: number;
  baseline_load: number | null;
  actual_load: number | null;
  forecast_kw: number | null;
  tariff_window: string | null;
  total_savings_rm: number;
  shave_percentage: number;
  within_limit_ticks: number;
  decision_log: Array<Record<string, unknown>>;
  agent_trace: DecisionLog[];
  last_dispatch_kw: number;
  md_limit_kw: number;
  md_rate: number;
  dispatch_action: SimulationDispatchAction;
  scenarios: Array<{ key: SimulationDayType; label: string; blurb: string }>;
};

export type SimulationViewModel = {
  sessionId: string | null;
  status: SimulationRunStatus;
  dayType: SimulationDayType;
  history: EnergyPoint[];
  summary: SimulationSummary;
  decisionLogs: DecisionLog[];
  currentInterval: number;
  totalIntervals: number;
  currentTimeLabel: string;
  forecastKw: number | null;
  forecastConfidence: number | null;
  batterySocPercent: number;
  bessCapacityKwh: number;
  totalSavingsRm: number;
  shavePercentage: number;
  withinLimitTicks: number;
  mdLimitKw: number;
  lastDispatchKw: number;
  agentTrace: DecisionLog[];
  scenarios: Array<{ key: SimulationDayType; label: string; blurb: string }>;
};
