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
    label: "Weekday Peak",
    blurb: "Typical weekday load with the afternoon maximum demand breach.",
  },
  {
    key: "holiday",
    label: "Holiday Surge",
    blurb: "Higher holiday demand with broader peak exposure across the site.",
  },
  {
    key: "solar_duck_curve",
    label: "Solar Duck Curve",
    blurb: "Post-solar ramp where late-afternoon grid import rises into the tariff window.",
  },
  {
    key: "large_weekday",
    label: "Large Facility",
    blurb: "High-load weekday facility (1,000–1,400 kW) with solar, peak hours 8–10 AM and 2–6 PM.",
  },
];

export const PLAYBACK_SPEEDS = [
  { label: "1x", intervalMs: 1000 },
  { label: "10x", intervalMs: 250 },
  { label: "60x", intervalMs: 75 },
] as const;

export type PlaybackSpeedLabel = (typeof PLAYBACK_SPEEDS)[number]["label"];
