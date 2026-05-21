import type { DecisionAgent } from "@/features/dashboard/types";

export type AccentStyle = {
  hex: string;
  text: string;
  badge: string;
  legendSwatch: string;
  activeBorder: string;
  activeBg: string;
  activeText: string;
  cardBg: string;
};

export const ACCENT_STYLES: Record<"primary" | "secondary" | "tertiary", AccentStyle> = {
  primary: {
    hex: "#4edea3",
    text: "text-primary",
    badge: "border-primary/35 bg-primary/10 text-primary",
    legendSwatch: "bg-primary",
    activeBorder: "border-primary/45",
    activeBg: "bg-primary/10",
    activeText: "text-primary",
    cardBg: "bg-primary/8",
  },
  secondary: {
    hex: "#adc6ff",
    text: "text-secondary",
    badge: "border-secondary/35 bg-secondary/10 text-secondary",
    legendSwatch: "bg-secondary",
    activeBorder: "border-secondary/45",
    activeBg: "bg-secondary/10",
    activeText: "text-secondary",
    cardBg: "bg-secondary/8",
  },
  tertiary: {
    hex: "#ffb95f",
    text: "text-tertiary",
    badge: "border-tertiary/35 bg-tertiary/10 text-tertiary",
    legendSwatch: "bg-tertiary",
    activeBorder: "border-tertiary/45",
    activeBg: "bg-tertiary/10",
    activeText: "text-tertiary",
    cardBg: "bg-tertiary/8",
  },
};

export const CARD_STYLES = {
  primary: {
    border: "border-primary/35",
    bg: "bg-primary/8",
    bar: "bg-primary",
  },
  secondary: {
    border: "border-secondary/35",
    bg: "bg-secondary/8",
    bar: "bg-secondary",
  },
  tertiary: {
    border: "border-tertiary/35",
    bg: "bg-tertiary/8",
    bar: "bg-tertiary",
  },
  danger: {
    border: "border-danger/35",
    bg: "bg-danger/8",
    bar: "bg-danger",
  },
};

export const AGENT_STYLES: Record<
  DecisionAgent,
  {
    dot: string;
    badge: string;
  }
> = {
  "Forecasting Agent": {
    dot: "border-secondary bg-secondary",
    badge: "border-secondary/35 bg-secondary/10 text-secondary",
  },
  "Planner Agent": {
    dot: "border-primary bg-primary",
    badge: "border-primary/35 bg-primary/10 text-primary",
  },
  "Optimization Agent": {
    dot: "border-tertiary bg-tertiary",
    badge: "border-tertiary/35 bg-tertiary/10 text-tertiary",
  },
  "Controller Agent": {
    dot: "border-muted bg-muted",
    badge: "border-outline bg-surface text-foreground",
  },
  "Auditor Agent": {
    dot: "border-danger bg-danger",
    badge: "border-danger/35 bg-danger/10 text-danger",
  },
};
