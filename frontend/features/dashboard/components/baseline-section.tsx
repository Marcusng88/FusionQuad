import { BaselineChart } from "@/features/dashboard/components/dashboard-charts";
import {
  MiniStat,
  Panel,
  RiskCard,
} from "@/features/dashboard/components/dashboard-primitives";
import type { EnergyPoint } from "@/features/dashboard/types";

export function BaselineSection({ points }: { points: EnergyPoint[] }) {
  return (
    <section id="baseline" className="grid gap-6 xl:grid-cols-[1.35fr_0.65fr]">
      <Panel
        eyebrow="Baseline"
        title="Historical maximum demand"
        subtitle="Review the demand profile against the target limit."
      >
        <div className="grid gap-5">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MiniStat title="Original MD" value="950 kW" accent="secondary" />
            <MiniStat title="Peak Time" value="15:00" accent="tertiary" />
            <MiniStat title="Average Load" value="728 kW" accent="secondary" />
            <MiniStat title="Solar Offset" value="320 kW" accent="primary" />
          </div>

          <BaselineChart points={points} />
        </div>
      </Panel>

      <Panel
        eyebrow="Risk panel"
        title="Peak risk summary"
        subtitle="Key breach indicators for the current profile."
      >
        <div className="grid gap-4">
          <RiskCard
            title="Risk intervals detected"
            value="6"
            note="All inside the weekday peak tariff window"
            tone="tertiary"
          />
          <RiskCard
            title="Peak import during TOU"
            value="4,250 kWh"
            note="High import coincides with the most expensive period"
            tone="secondary"
          />
          <RiskCard
            title="Potential MD penalty"
            value="RM12,400"
            note="Avoidable exposure if the largest spikes are clipped"
            tone="danger"
          />
          <div className="rounded-2xl border border-primary/35 bg-primary/10 px-5 py-4">
            <p className="font-label text-[10px] text-primary">Best result</p>
            <p className="mt-3 text-sm leading-7 text-foreground">
              Battery plus flexible load keeps the site at the 800 kW target.
            </p>
          </div>
        </div>
      </Panel>
    </section>
  );
}
