"use client";

import {
  ConfigCard,
  FlowStep,
  Panel,
} from "@/features/dashboard/components/dashboard-primitives";

export default function SetupPage() {
  return (
    <div className="grid gap-8 xl:grid-cols-[1.1fr_0.9fr]">
      <Panel
        eyebrow="Setup"
        title="Site setup"
        subtitle="Load profile, tariff, and storage settings."
      >
        <div className="grid gap-6">
          <div className="rounded-2xl border border-dashed border-outline bg-surface px-5 py-8 text-center">
            <p className="font-label text-[10px] text-secondary">Site history</p>
            <h4 className="font-display mt-3 text-xl font-semibold">
              Add load and solar history
            </h4>
            <p className="mt-3 text-sm text-muted">
              Include timestamps, site demand, and solar output.
            </p>
            <div className="mt-5 flex flex-wrap justify-center gap-3">
              <button className="rounded-full border border-outline bg-surface-3 px-4 py-2 text-sm text-foreground transition hover:border-secondary hover:bg-surface-4">
                Browse files
              </button>
              <button className="rounded-full border border-primary/35 bg-primary/10 px-4 py-2 text-sm text-primary transition hover:bg-primary/18">
                Use sample site
              </button>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <ConfigCard
              title="Tariff configuration"
              accent="tertiary"
              fields={[
                ["Demand limit", "800 kW"],
                ["MD rate", "RM97.06 / kW"],
                ["Peak start", "14:00"],
                ["Peak end", "22:00"],
              ]}
            />
            <ConfigCard
              title="Battery settings"
              accent="primary"
              fields={[
                ["Capacity", "500 kWh"],
                ["Max discharge", "100 kW"],
                ["Max charge", "100 kW"],
                ["Reserve floor", "20% SoC"],
              ]}
            />
          </div>
        </div>
      </Panel>

      <Panel
        eyebrow="Checklist"
        title="Review sequence"
        subtitle="Move from setup to action."
      >
        <div className="grid gap-4">
          <FlowStep
            index="01"
            title="Baseline"
            body="Find the intervals that cross the demand limit."
          />
          <FlowStep
            index="02"
            title="Scenarios"
            body="Compare Solar, Battery, Load Shifting, and Combined."
          />
          <FlowStep
            index="03"
            title="Decision trail"
            body="Review the final operating sequence."
          />
          <div className="rounded-2xl border border-outline bg-surface px-5 py-5">
            <p className="font-label text-[10px] text-muted">Status</p>
            <p className="mt-3 text-sm leading-7 text-muted">
              Combined strategy is holding the site at the target limit.
            </p>
          </div>
        </div>
      </Panel>
    </div>
  );
}
