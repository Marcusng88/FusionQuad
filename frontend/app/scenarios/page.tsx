"use client";

import { useState } from "react";

import { Panel } from "@/features/dashboard/components/dashboard-primitives";
import { formatCurrencyValue } from "@/features/dashboard/lib/formatters";
import { ACCENT_STYLES } from "@/features/dashboard/theme";
import { SCENARIO_LIST } from "@/features/dashboard/data/scenarios";
import type { ScenarioKey } from "@/features/dashboard/types";

export default function ScenariosPage() {
  const [selectedScenario, setSelectedScenario] = useState<ScenarioKey>("batteryAndShifting");

  return (
    <Panel
      eyebrow="Scenarios"
      title="Scenario outcomes"
      subtitle="Final demand and monthly savings."
    >
      <div className="grid gap-4 lg:grid-cols-5">
        {SCENARIO_LIST.map((item) => {
          const itemAccent = ACCENT_STYLES[item.accent];
          const isActive = selectedScenario === item.key;

          return (
            <button
              key={item.key}
              className={`rounded-2xl border p-5 text-left transition ${
                isActive
                  ? `${itemAccent.activeBorder} ${itemAccent.cardBg}`
                  : "border-outline bg-surface hover:bg-surface-3"
              }`}
              onClick={() => setSelectedScenario(item.key)}
              type="button"
            >
              <p className={`font-label text-[10px] ${itemAccent.text}`}>{item.label}</p>
              <p className="font-display mt-4 text-3xl font-semibold text-foreground">
                {item.summary.optimized_md_kw}
                <span className="ml-2 text-base text-muted">kW</span>
              </p>
              <p className="mt-3 text-sm text-muted">
                Savings: RM{formatCurrencyValue(item.summary.md_savings_rm)}
              </p>
              <p className="mt-4 text-sm leading-6 text-muted">{item.blurb}</p>
            </button>
          );
        })}
      </div>
    </Panel>
  );
}
