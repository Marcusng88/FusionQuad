import {
  KpiCard,
  QuickMetric,
} from "@/features/dashboard/components/dashboard-primitives";

export function HeroOverview({ originalMdDelta }: { originalMdDelta: number }) {
  return (
    <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
      <div className="panel-shadow panel-noise rounded-3xl border border-outline bg-surface-2 p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-2xl">
            <p className="font-label text-[11px] text-secondary">Today</p>
            <h3 className="font-display mt-3 text-3xl font-semibold leading-tight text-foreground sm:text-4xl">
              Peak demand is above target.
            </h3>
            <p className="mt-4 max-w-xl text-sm leading-7 text-muted sm:text-base">
              Review the breach, compare responses, and lock the cleanest operating plan.
            </p>
          </div>

          <div className="grid min-w-[240px] gap-3">
            <QuickMetric
              label="Original MD"
              value="950 kW"
              note={`+${originalMdDelta} kW above limit`}
              tone="danger"
            />
            <QuickMetric
              label="Preferred Strategy"
              value="Battery + Shift"
              note="Held at 800 kW"
              tone="primary"
            />
            <QuickMetric
              label="Monthly Savings"
              value="RM14,559"
              note="At RM97.06 per kW"
              tone="secondary"
            />
          </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3 xl:grid-cols-1">
        <KpiCard
          title="Original Maximum Demand"
          value="950"
          suffix="kW"
          detail="3:00 PM peak interval"
          tone="secondary"
        />
        <KpiCard
          title="Original MD Cost"
          value="92,207"
          prefix="RM"
          detail="Current billing basis"
          tone="tertiary"
        />
        <KpiCard
          title="Peak Risk Intervals"
          value="6"
          detail="Breaches above the 800 kW target"
          tone="danger"
        />
      </div>
    </section>
  );
}
