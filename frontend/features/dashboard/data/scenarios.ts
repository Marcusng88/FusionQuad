import type {
  DecisionLog,
  NavItem,
  ScenarioData,
  ScenarioKey,
  SimulationSummary,
} from "@/features/dashboard/types";

export const MD_RATE = 97.06;
export const DEMAND_LIMIT = 800;
export const PEAK_WINDOW_LABEL = "14:00 to 22:00";
export const DEFAULT_SCENARIO_KEY: ScenarioKey = "batteryAndShifting";

export const NAV_ITEMS: NavItem[] = [
  { href: "#setup", label: "Setup" },
  { href: "#baseline", label: "Baseline" },
  { href: "#simulation", label: "Simulation" },
  { href: "#ai-decisions", label: "AI Decisions" },
  { href: "#scenarios", label: "Scenarios" },
];

export const TIMESTAMPS = [
  "00:00",
  "02:00",
  "04:00",
  "06:00",
  "08:00",
  "10:00",
  "12:00",
  "14:00",
  "16:00",
  "18:00",
  "20:00",
  "22:00",
];

const ORIGINAL_GRID = [540, 520, 505, 560, 650, 720, 790, 920, 950, 880, 760, 640];
const SOLAR = [0, 0, 0, 35, 120, 240, 320, 250, 120, 40, 0, 0];
const LOAD = ORIGINAL_GRID.map((value, index) => value + SOLAR[index]);

export const SCENARIOS: Record<ScenarioKey, ScenarioData> = {
  baseline: makeScenario({
    key: "baseline",
    label: "Baseline",
    blurb: "Historical demand profile before any intervention.",
    accent: "secondary",
    optimized: ORIGINAL_GRID,
    batteryPower: Array(TIMESTAMPS.length).fill(0),
    soc: Array(TIMESTAMPS.length).fill(90),
    shiftedLoad: Array(TIMESTAMPS.length).fill(0),
    decisionLogs: [
      {
        timestamp: "15:00",
        agent: "Auditor Agent",
        decision: "Flag maximum demand exposure",
        reason: "Observed a 950 kW import during the weekday peak window.",
        action: "Marked six high-risk intervals for comparison.",
        estimated_saving_rm: 0,
      },
    ],
  }),
  solarOnly: makeScenario({
    key: "solarOnly",
    label: "Solar Only",
    blurb: "Solar relieves the afternoon shoulder, but the late peak still lands above target.",
    accent: "primary",
    optimized: [540, 520, 505, 560, 650, 700, 760, 880, 900, 850, 760, 640],
    batteryPower: Array(TIMESTAMPS.length).fill(0),
    soc: Array(TIMESTAMPS.length).fill(90),
    shiftedLoad: Array(TIMESTAMPS.length).fill(0),
    decisionLogs: [
      {
        timestamp: "14:00",
        agent: "Forecasting Agent",
        decision: "Project solar-led reduction only",
        reason: "Midday solar output delays the strongest grid pull by one interval.",
        action: "Trimmed the simulated peak to 900 kW without storage support.",
        expected_reduction_kw: 50,
        estimated_saving_rm: 4853,
      },
    ],
  }),
  batteryOnly: makeScenario({
    key: "batteryOnly",
    label: "Battery Only",
    blurb: "Storage trims the spike, but the reserve floor limits a deeper late-window cut.",
    accent: "secondary",
    optimized: [540, 520, 505, 560, 650, 720, 790, 860, 850, 820, 760, 640],
    batteryPower: [0, 0, 0, 0, 0, 35, 45, -60, -70, -60, 0, 0],
    soc: [90, 90, 90, 90, 90, 94, 98, 76, 63, 51, 51, 51],
    shiftedLoad: Array(TIMESTAMPS.length).fill(0),
    decisionLogs: [
      {
        timestamp: "14:00",
        agent: "Planner Agent",
        decision: "Use storage as the primary response",
        reason: "No flexible load window is available in this scenario.",
        action: "Charged before the peak and discharged through the highest-risk intervals.",
        expected_reduction_kw: 100,
        estimated_saving_rm: 9706,
      },
    ],
  }),
  loadShiftingOnly: makeScenario({
    key: "loadShiftingOnly",
    label: "Load Shifting Only",
    blurb: "EV and HVAC flexibility help, but the site still finishes above the demand target.",
    accent: "tertiary",
    optimized: [540, 520, 505, 560, 650, 720, 790, 870, 860, 830, 760, 640],
    batteryPower: Array(TIMESTAMPS.length).fill(0),
    soc: Array(TIMESTAMPS.length).fill(90),
    shiftedLoad: [0, 0, 0, 0, 0, 0, 0, 50, 90, 50, 0, 0],
    decisionLogs: [
      {
        timestamp: "15:00",
        agent: "Optimization Agent",
        decision: "Reschedule EV charging and pre-cool HVAC blocks",
        reason: "A 150 kW breach was projected with storage unavailable.",
        action: "Moved 190 kW of flexible activity into lower-cost hours.",
        expected_reduction_kw: 90,
        estimated_saving_rm: 8735.4,
      },
    ],
  }),
  batteryAndShifting: makeScenario({
    key: "batteryAndShifting",
    label: "Battery + Load Shifting",
    blurb: "Storage and flexible demand work together to hold the site at the 800 kW target.",
    accent: "primary",
    optimized: [540, 520, 505, 560, 650, 720, 790, 800, 800, 780, 760, 640],
    batteryPower: [0, 0, 0, 0, 0, 25, 35, -60, -70, -20, 0, 0],
    soc: [90, 90, 90, 90, 90, 93, 97, 80, 63, 57, 57, 57],
    shiftedLoad: [0, 0, 0, 0, 0, 0, 0, 60, 80, 80, 0, 0],
    decisionLogs: [
      {
        timestamp: "14:00",
        agent: "Forecasting Agent",
        decision: "Detect a 920 kW import risk",
        reason: "The peak window opens as solar support starts to roll off.",
        action: "Raised a 120 kW shave requirement for the next interval.",
        expected_reduction_kw: 120,
      },
      {
        timestamp: "14:30",
        agent: "Planner Agent",
        decision: "Hold enough storage for the later 16:00 spike",
        reason: "The highest breach is still ahead of the current interval.",
        action: "Split the response between storage and flexible demand instead of overspending the battery early.",
      },
      {
        timestamp: "15:00",
        agent: "Optimization Agent",
        decision: "Cap import at the demand target",
        reason: "The projected breach reached 150 kW versus the 800 kW operating limit.",
        action: "Discharged 70 kW and shifted 80 kW of EV charging.",
        expected_reduction_kw: 150,
        estimated_saving_rm: 14559,
      },
      {
        timestamp: "15:00",
        agent: "Controller Agent",
        decision: "Apply the staged response",
        reason: "The combined action stays above the 20% reserve floor.",
        action: "Updated the optimized import curve and the storage trajectory.",
      },
      {
        timestamp: "15:30",
        agent: "Auditor Agent",
        decision: "Validate the outcome",
        reason: "Import must stay at or below the threshold through the late peak.",
        action: "Confirmed an optimized MD of 800 kW with projected monthly savings of RM14,559.",
        estimated_saving_rm: 14559,
      },
    ],
  }),
};

export const SCENARIO_LIST = Object.values(SCENARIOS);

function makeScenario({
  key,
  label,
  blurb,
  accent,
  optimized,
  batteryPower,
  soc,
  shiftedLoad,
  decisionLogs,
}: {
  key: ScenarioKey;
  label: string;
  blurb: string;
  accent: ScenarioData["accent"];
  optimized: number[];
  batteryPower: number[];
  soc: number[];
  shiftedLoad: number[];
  decisionLogs: DecisionLog[];
}): ScenarioData {
  const optimizedMd = Math.max(...optimized);
  const summary: SimulationSummary = {
    original_md_kw: 950,
    optimized_md_kw: optimizedMd,
    peak_reduction_kw: 950 - optimizedMd,
    original_md_cost_rm: 92207,
    optimized_md_cost_rm: Math.round(optimizedMd * MD_RATE),
    md_savings_rm: Number(((950 - optimizedMd) * MD_RATE).toFixed(2)),
    battery_energy_used_kwh: Math.round(
      batteryPower
        .filter((value) => value < 0)
        .reduce((sum, value) => sum + Math.abs(value), 0) / 4,
    ),
    final_soc_percent: soc.at(-1) ?? 0,
    shifted_load_kwh: Math.round(shiftedLoad.reduce((sum, value) => sum + value, 0) / 2),
  };

  const timeseries = TIMESTAMPS.map((timestamp, index) => ({
    timestamp,
    load_kw: LOAD[index],
    solar_kw: SOLAR[index],
    original_grid_import_kw: ORIGINAL_GRID[index],
    optimized_grid_import_kw: optimized[index],
    battery_power_kw: batteryPower[index],
    battery_soc_percent: soc[index],
    shifted_load_kw: shiftedLoad[index],
    demand_limit_kw: DEMAND_LIMIT,
    is_peak_period: index >= 7 && index <= 11,
  }));

  if (key === "batteryAndShifting") {
    summary.battery_energy_used_kwh = 35;
    summary.final_soc_percent = 63;
    summary.shifted_load_kwh = 110;
  }

  return {
    key,
    label,
    blurb,
    accent,
    summary,
    timeseries,
    decisionLogs,
  };
}
