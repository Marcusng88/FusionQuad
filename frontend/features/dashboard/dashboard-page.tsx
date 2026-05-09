"use client";

import { useState } from "react";

import { BaselineSection } from "@/features/dashboard/components/baseline-section";
import { DashboardHeader } from "@/features/dashboard/components/dashboard-header";
import { DecisionsSection } from "@/features/dashboard/components/decisions-section";
import { HeroOverview } from "@/features/dashboard/components/hero-overview";
import { ScenariosSection } from "@/features/dashboard/components/scenarios-section";
import { DashboardSidebar } from "@/features/dashboard/components/dashboard-sidebar";
import { SetupSection } from "@/features/dashboard/components/setup-section";
import { SimulationSection } from "@/features/dashboard/components/simulation-section";
import {
  DEFAULT_SCENARIO_KEY,
  DEMAND_LIMIT,
  MD_RATE,
  NAV_ITEMS,
  PEAK_WINDOW_LABEL,
  SCENARIO_LIST,
  SCENARIOS,
} from "@/features/dashboard/data/scenarios";
import type { ScenarioKey } from "@/features/dashboard/types";

export default function DashboardPage() {
  const [selectedScenario, setSelectedScenario] =
    useState<ScenarioKey>(DEFAULT_SCENARIO_KEY);

  const scenario = SCENARIOS[selectedScenario];
  const originalMdDelta = scenario.summary.original_md_kw - DEMAND_LIMIT;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <DashboardSidebar
        navItems={NAV_ITEMS}
        rateLabel={`MV TOU / RM${MD_RATE.toFixed(2)} per kW`}
      />

      <div className="md:ml-64">
        <DashboardHeader
          demandLimitKw={DEMAND_LIMIT}
          peakWindow={PEAK_WINDOW_LABEL}
          navItems={NAV_ITEMS}
        />

        <main className="mx-auto flex max-w-[1440px] flex-col gap-8 px-4 py-6 sm:px-6 xl:px-8">
          <HeroOverview originalMdDelta={originalMdDelta} />
          <SetupSection />
          <BaselineSection points={SCENARIOS.baseline.timeseries} />
          <SimulationSection
            scenarios={SCENARIO_LIST}
            selectedScenario={selectedScenario}
            onScenarioChange={setSelectedScenario}
          />
          <DecisionsSection logs={scenario.decisionLogs} />
          <ScenariosSection
            scenarios={SCENARIO_LIST}
            selectedScenario={selectedScenario}
            onScenarioChange={setSelectedScenario}
          />
        </main>
      </div>
    </div>
  );
}
