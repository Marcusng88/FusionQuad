import type { SimulationDayType } from "../types";

export const MD_RATE = 97.06;
export const DEFAULT_DEMAND_LIMIT_KW = 800;

export const DAY_SCENARIOS: Array<{
  key: SimulationDayType;
  label: string;
  blurb: string;
}> = [
  {
    key: "weekday",
    label: "Load Profile (No Solar) E",
    blurb: "Typical weekday load with the afternoon maximum demand breach.",
  },
  {
    key: "holiday",
    label: "Load Profile (No Solar) SuN",
    blurb: "Higher holiday demand with broader peak exposure across the site.",
  },
  {
    key: "solar_duck_curve",
    label: "Load Profile (With Solar Installed) SoL",
    blurb: "Post-solar ramp where late-afternoon grid import rises into the tariff window.",
  },
  {
    key: "large_weekday",
    label: "Load Profile (With Solar) Mi2",
    blurb: "High-load weekday facility (1,000–1,400 kW) with solar, peak hours 8–10 AM and 2–6 PM.",
  },
];

