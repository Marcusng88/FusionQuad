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
