import { DispatchChart, ShiftChart, SimulationChart, SocChart } from "@/features/dashboard/components/dashboard-charts";
import { KpiCard, Panel } from "@/features/dashboard/components/dashboard-primitives";
import { ACCENT_STYLES } from "@/features/dashboard/theme";
import { formatCurrencyValue } from "@/features/dashboard/lib/formatters";
import type { ScenarioData, ScenarioKey } from "@/features/dashboard/types";

export function SimulationSection({
  scenarios,
  selectedScenario,
  onScenarioChange,
}: {
  scenarios: ScenarioData[];
  selectedScenario: ScenarioKey;
  onScenarioChange: (scenario: ScenarioKey) => void;
}) {
  const scenario = scenarios.find((item) => item.key === selectedScenario) ?? scenarios[0];
  const accent = ACCENT_STYLES[scenario.accent];

  return (
    <section id="simulation" className="grid gap-6">
      <Panel
        eyebrow="Simulation"
        title="Scenario comparison"
        subtitle="Compare response options against the same demand curve."
      >
        <div className="grid gap-6">
          <div className="flex flex-wrap gap-2">
            {scenarios.map((item) => {
              const itemAccent = ACCENT_STYLES[item.accent];
              const isActive = selectedScenario === item.key;

              return (
                <button
                  key={item.key}
                  className={`rounded-full border px-4 py-2 text-sm transition ${
                    isActive
                      ? `${itemAccent.activeBorder} ${itemAccent.activeBg} ${itemAccent.activeText}`
                      : "border-outline bg-surface text-muted hover:bg-surface-3 hover:text-foreground"
                  }`}
                  onClick={() => onScenarioChange(item.key)}
                  type="button"
                >
                  {item.label}
                </button>
              );
            })}
          </div>

          <div className="rounded-2xl border border-outline bg-surface px-5 py-4">
            <p className="font-label text-[10px] text-muted">Selected scenario</p>
            <p className="mt-3 text-sm leading-7 text-foreground">{scenario.blurb}</p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard
              title="Estimated MD Savings"
              value={formatCurrencyValue(scenario.summary.md_savings_rm)}
              prefix="RM"
              detail="Estimated monthly reduction"
              tone={scenario.accent}
            />
            <KpiCard
              title="Optimized Maximum Demand"
              value={String(scenario.summary.optimized_md_kw)}
              suffix="kW"
              detail={`${scenario.summary.peak_reduction_kw} kW shaved from baseline`}
              tone="secondary"
            />
            <KpiCard
              title="Battery Energy Used"
              value={String(scenario.summary.battery_energy_used_kwh)}
              suffix="kWh"
              detail="Daily throughput"
              tone="secondary"
            />
            <KpiCard
              title="Final SoC"
              value={String(scenario.summary.final_soc_percent)}
              suffix="%"
              detail={`${scenario.summary.shifted_load_kwh} kWh shifted off-peak`}
              tone="primary"
            />
          </div>

          <SimulationChart points={scenario.timeseries} accent={accent} />

          <div className="grid gap-5 xl:grid-cols-3">
            <SocChart points={scenario.timeseries} />
            <DispatchChart points={scenario.timeseries} />
            <ShiftChart points={scenario.timeseries} />
          </div>
        </div>
      </Panel>
    </section>
  );
}
