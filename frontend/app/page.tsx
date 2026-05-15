"use client";

import { useState } from "react";

import { HeroOverview } from "@/features/dashboard/components/hero-overview";
import {
  KpiCard,
  Panel,
  QuickMetric,
} from "@/features/dashboard/components/dashboard-primitives";
import { DEMAND_LIMIT, MD_RATE, SCENARIOS } from "@/features/dashboard/data/scenarios";
import { formatCurrencyValue } from "@/features/dashboard/lib/formatters";

const TIMESTAMPS = [
  "00:00", "02:00", "04:00", "06:00", "08:00", "10:00",
  "12:00", "14:00", "16:00", "18:00", "20:00", "22:00",
];

const DEMAND_DATA = [540, 520, 505, 560, 650, 720, 790, 920, 950, 880, 760, 640];
const PEAK_DATA = [790, 920, 950, 880, 760, 640];

export default function OverviewPage() {
  const scenario = SCENARIOS.batteryAndShifting;
  const originalMdDelta = scenario.summary.original_md_kw - DEMAND_LIMIT;

  return (
    <div className="grid gap-8">
      <HeroOverview originalMdDelta={originalMdDelta} />

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel
          eyebrow="Demand profile"
          title="Mini demand overview"
          subtitle="Today's grid import pattern against the 800 kW target limit."
        >
          <div className="space-y-6">
            <div className="rounded-2xl border border-outline bg-surface p-5">
              <p className="font-label text-[10px] text-muted">Hourly grid import (kW)</p>
              <div className="mt-4 flex items-end gap-1.5">
                {DEMAND_DATA.map((value, index) => {
                  const heightPercent = (value / 1000) * 100;
                  const isPeak = index >= 7 && index <= 11;
                  const exceedsLimit = value > DEMAND_LIMIT;

                  return (
                    <div key={TIMESTAMPS[index]} className="flex flex-1 flex-col items-center gap-2">
                      <div
                        className={`w-full rounded-t-lg transition-all ${
                          exceedsLimit
                            ? "bg-danger/70"
                            : isPeak
                              ? "bg-tertiary/50"
                              : "bg-secondary/50"
                        }`}
                        style={{ height: `${heightPercent}%`, minHeight: "8px" }}
                      />
                      <span className="text-[9px] text-muted">{TIMESTAMPS[index]}</span>
                    </div>
                  );
                })}
              </div>
              <div className="mt-3 flex items-center justify-center gap-6 text-[10px] text-muted">
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-secondary/50" /> Grid import
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-tertiary/50" /> Peak window
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-danger/70" /> Above limit
                </span>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <KpiCard
                title="Current SoC"
                value="63"
                suffix="%"
                detail="Battery reserve after peak"
                tone="primary"
              />
              <KpiCard
                title="Peak Interval"
                value="16:00"
                detail="Highest grid import at 950 kW"
                tone="danger"
              />
              <KpiCard
                title="Savings Ready"
                value={formatCurrencyValue(scenario.summary.md_savings_rm)}
                prefix="RM"
                detail="Monthly projected savings"
                tone="secondary"
              />
            </div>
          </div>
        </Panel>

        <div className="grid gap-4">
          <Panel
            eyebrow="Strategy status"
            title="Agent coordination"
            subtitle="Active agents managing the demand response."
          >
            <div className="space-y-3">
              <AgentStatus
                name="Forecasting Agent"
                status="Active"
                detail="Monitoring 14:00 peak window"
                tone="secondary"
              />
              <AgentStatus
                name="Planner Agent"
                status="Active"
                detail="Battery reserve at 63% held"
                tone="primary"
              />
              <AgentStatus
                name="Optimization Agent"
                status="Active"
                detail="Combined response running"
                tone="tertiary"
              />
              <AgentStatus
                name="Controller Agent"
                status="Active"
                detail="Dispatching 70 kW discharge"
                tone="secondary"
              />
              <AgentStatus
                name="Auditor Agent"
                status="Standby"
                detail="Validating final outcome"
                tone="secondary"
              />
            </div>
          </Panel>

          <div className="rounded-2xl border border-primary/35 bg-primary/10 p-5">
            <p className="font-label text-[10px] text-primary">Battery SoC</p>
            <div className="mt-4 flex items-center gap-4">
              <div className="relative h-16 w-16 flex-shrink-0 rounded-full border-4 border-primary/40 bg-surface-2">
                <svg className="absolute inset-0 h-full w-full -rotate-90" viewBox="0 0 36 36">
                  <circle
                    cx="18"
                    cy="18"
                    r="14"
                    fill="none"
                    stroke="rgba(78, 222, 163, 0.2)"
                    strokeWidth="4"
                  />
                  <circle
                    cx="18"
                    cy="18"
                    r="14"
                    fill="none"
                    stroke="#4edea3"
                    strokeWidth="4"
                    strokeDasharray={`${63 * 0.88} 88`}
                    strokeLinecap="round"
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center font-display text-sm font-semibold text-primary">
                  63%
                </span>
              </div>
              <div className="flex-1">
                <p className="text-sm text-foreground">500 kWh capacity</p>
                <p className="mt-1 text-sm text-muted">195 kWh available</p>
                <p className="mt-1 text-sm text-muted">315 kWh reserved (63%)</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function AgentStatus({
  name,
  status,
  detail,
  tone,
}: {
  name: string;
  status: string;
  detail: string;
  tone: "primary" | "secondary" | "tertiary";
}) {
  const statusColor =
    tone === "primary"
      ? "text-primary"
      : tone === "secondary"
        ? "text-secondary"
        : "text-tertiary";

  const dotColor =
    tone === "primary"
      ? "bg-primary"
      : tone === "secondary"
        ? "bg-secondary"
        : "bg-tertiary";

  return (
    <div className="flex items-center gap-3 rounded-xl border border-outline bg-surface px-4 py-3">
      <div className={`h-2 w-2 rounded-full ${dotColor}`} />
      <div className="flex-1">
        <p className="text-sm font-medium text-foreground">{name}</p>
        <p className="text-xs text-muted">{detail}</p>
      </div>
      <span className={`rounded-full border px-2 py-1 text-[10px] font-label ${statusColor} border-current/20 bg-current/10`}>
        {status}
      </span>
    </div>
  );
}
