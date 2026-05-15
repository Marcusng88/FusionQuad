"use client";

import { Panel, ReasonCard, TimelineItem } from "@/features/dashboard/components/dashboard-primitives";
import { SCENARIOS } from "@/features/dashboard/data/scenarios";

export default function DecisionsPage() {
  const scenario = SCENARIOS.batteryAndShifting;

  return (
    <div className="grid gap-8 xl:grid-cols-[0.95fr_1.05fr]">
      <Panel
        eyebrow="AI Decisions"
        title="Decision timeline"
        subtitle="Review the sequence behind the selected response."
      >
        <div className="space-y-4">
          {scenario.decisionLogs.map((log, index) => (
            <TimelineItem key={`${log.agent}-${index}`} log={log} index={index} />
          ))}
        </div>
      </Panel>

      <Panel
        eyebrow="Decision summary"
        title="Why the combined strategy leads"
        subtitle="The selected plan balances reduction, stability, and reserve."
      >
        <div className="grid gap-4">
          <ReasonCard
            label="Forecasting Agent"
            title="Flags the next breach window"
            copy="Upcoming import spikes are detected early enough for the response to land before the interval closes."
            tone="secondary"
          />
          <ReasonCard
            label="Planner Agent"
            title="Preserves storage for late peak"
            copy="Battery reserve is held back for the post-solar decline instead of discharging too early."
            tone="primary"
          />
          <ReasonCard
            label="Optimization Agent"
            title="Blends battery and load shift"
            copy="Battery discharge and flexible-load shifting share the reduction so one asset does not carry the full event."
            tone="tertiary"
          />
        </div>
      </Panel>
    </div>
  );
}
