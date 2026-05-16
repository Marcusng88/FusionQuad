"use client";

import {
  BaselineChart,
  DispatchChart,
  SimulationChart,
  SocChart,
} from "./components/dashboard-charts";
import { KpiCard } from "./components/dashboard-primitives";
import { ACCENT_STYLES, AGENT_STYLES, type AccentStyle } from "./theme";
import {
  DEFAULT_DEMAND_LIMIT_KW,
  MD_RATE,
} from "./data/day-scenarios";
import { useSimulationController } from "./hooks/use-simulation-controller";
import { formatCurrencyValue } from "./lib/formatters";
import type { DecisionLog } from "./types";

export default function LiveDashboardPage() {
  const {
    dayOptions,
    selectedDayType,
    bessCapacityKwh,
    setBessCapacityKwh,
    simulation,
    isBusy,
    errorMessage,
    handleDayTypeChange,
    runOptimization,
    timeRange,
    setTimeRange,
    scenarioMetadata,
    metadataLoading,
    canRun,
  } = useSimulationController();

  const accent = accentForDayType(selectedDayType);
  const activeDay =
    dayOptions.find((o) => o.key === selectedDayType) ?? dayOptions[0];
  const points = simulation.history;
  const hasHistory = points.length > 0;
  const isIdle = simulation.status === "idle";
  const complianceRate =
    simulation.currentInterval > 0
      ? Math.round(
          (simulation.withinLimitTicks /
            Math.max(simulation.currentInterval, 1)) *
            100,
        )
      : 0;

  return (
    <div
      className="grid gap-0 xl:grid-cols-[300px_1fr_320px]"
      style={{ minHeight: `calc(100vh - var(--header-h))` }}
    >
      {/* ── LEFT: Control Panel ── */}
      <aside className="border-b border-outline bg-surface-2/60 xl:border-b-0 xl:border-r xl:sticky xl:overflow-y-auto"
        style={{ top: "var(--header-h)", maxHeight: `calc(100vh - var(--header-h))` }}
      >
        <div className="space-y-5 p-5">
          {/* Scenario selector */}
          <div>
            <p className="font-label text-[10px] text-muted mb-3">Scenario</p>
            <div className="space-y-2">
              {dayOptions.map((option) => {
                const isActive = option.key === selectedDayType;
                const optAccent = accentForDayType(option.key);
                return (
                  <button
                    key={option.key}
                    type="button"
                    disabled={isBusy}
                    onClick={() => void handleDayTypeChange(option.key)}
                    className={`w-full rounded-xl border px-4 py-3 text-left transition ${
                      isActive
                        ? `${optAccent.activeBorder} ${optAccent.activeBg}`
                        : "border-outline bg-surface hover:bg-surface-3"
                    }`}
                  >
                    <p className={`font-label text-[10px] ${isActive ? optAccent.activeText : "text-muted"}`}>
                      {option.label}
                    </p>
                    <p className="mt-1 text-xs leading-5 text-muted line-clamp-2">
                      {option.blurb}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* BESS slider */}
          <div className="rounded-xl border border-outline bg-surface px-4 py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-label text-[10px] text-primary">
                  BESS Capacity
                  <Tip text="Battery Energy Storage System — stored energy used to discharge during peak tariff windows to shave demand spikes." />
                </p>
                <p className="mt-2 text-2xl font-semibold text-foreground font-display">
                  {bessCapacityKwh} <span className="text-sm text-muted font-normal">kWh</span>
                </p>
              </div>
              <span className="rounded-lg border border-outline bg-surface-2 px-3 py-1.5 text-xs text-muted">
                SoC 50% start
              </span>
            </div>
            <input
              aria-label="BESS capacity"
              className="mt-4 w-full accent-[var(--primary)]"
              disabled={isBusy}
              max={2000}
              min={500}
              onChange={(e) => setBessCapacityKwh(Number(e.target.value))}
              step={100}
              type="range"
              value={bessCapacityKwh}
            />
            <div className="mt-1 flex justify-between text-[10px] text-muted">
              <span>500 kWh</span>
              <span>2000 kWh</span>
            </div>
          </div>

          {/* Time window — shown once metadata loads */}
          <div className="rounded-xl border border-outline bg-surface px-4 py-4">
            <p className="font-label text-[10px] text-primary mb-3">Time Window</p>
            {metadataLoading ? (
              <p className="text-[11px] text-muted">Loading available dates…</p>
            ) : scenarioMetadata ? (
              <div className="space-y-2">
                <div>
                  <label className="text-[10px] text-muted" htmlFor="range-start">Start <span className="text-danger">*</span></label>
                  <input
                    id="range-start"
                    className="mt-1 w-full rounded-lg border border-outline bg-surface-2 px-3 py-1.5 text-xs"
                    disabled={isBusy}
                    max={scenarioMetadata.available_end.slice(0, 16)}
                    min={scenarioMetadata.available_start.slice(0, 16)}
                    type="datetime-local"
                    value={timeRange.start ?? ""}
                    onChange={(e) => {
                      const newStart = e.target.value || null;
                      const endStillValid = newStart && timeRange.end && timeRange.end >= newStart;
                      setTimeRange({ start: newStart, end: endStillValid ? timeRange.end : null });
                    }}
                  />
                </div>
                <div>
                  <label className="text-[10px] text-muted" htmlFor="range-end">End <span className="text-danger">*</span></label>
                  <input
                    id="range-end"
                    className="mt-1 w-full rounded-lg border border-outline bg-surface-2 px-3 py-1.5 text-xs"
                    disabled={isBusy}
                    max={scenarioMetadata.available_end.slice(0, 16)}
                    min={timeRange.start ?? scenarioMetadata.available_start.slice(0, 16)}
                    type="datetime-local"
                    value={timeRange.end ?? ""}
                    onChange={(e) => setTimeRange({ start: timeRange.start, end: e.target.value || null })}
                  />
                </div>
                <p className="text-[10px] text-muted">
                  Available: {scenarioMetadata.available_start.slice(0, 10)} → {scenarioMetadata.available_end.slice(0, 10)}
                </p>
              </div>
            ) : (
              <p className="text-[11px] text-muted">Select a scenario to see available dates.</p>
            )}
          </div>

          {/* Primary CTA */}
          <button
            type="button"
            disabled={!canRun}
            onClick={() => void runOptimization()}
            className="w-full rounded-xl border border-primary/40 bg-primary/15 px-5 py-3 text-sm font-semibold text-primary transition hover:bg-primary/25 disabled:opacity-50 active:scale-95"
          >
            {isBusy ? "Working…" : "▶ Run Optimization"}
          </button>
          {!canRun && !isBusy && scenarioMetadata && (
            <p className="text-center text-[10px] text-muted">Select start and end date to run</p>
          )}

          {/* Error */}
          {errorMessage ? (
            <div className="rounded-xl border border-danger/35 bg-danger/8 px-4 py-3 text-xs text-danger">
              {errorMessage}
            </div>
          ) : null}
        </div>
      </aside>

      {/* ── CENTER: Chart Hero ── */}
      <main className="min-w-0 space-y-5 p-5 xl:p-6">
        {/* Day title + status row */}
        <div className="panel-shadow panel-noise rounded-2xl border border-outline bg-surface-2 px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="font-label text-[10px] text-muted">Live simulation</p>
              <h3 className="font-display mt-2 text-2xl font-semibold text-foreground sm:text-3xl">
                {activeDay.label}
              </h3>
              <p className="mt-2 max-w-lg text-sm leading-6 text-muted">{activeDay.blurb}</p>
            </div>

            <div className="flex flex-wrap gap-2">
              <StatusChip label="Status" value={simulation.status.toUpperCase()} tone={simulation.status === "completed" ? "primary" : "secondary"} />
              <StatusChip label="Interval" value={`${simulation.currentInterval} / ${simulation.totalIntervals || 48}`} tone="secondary" />
              <StatusChip
                label="Forecast"
                value={simulation.forecastKw != null ? `${Math.round(simulation.forecastKw)} kW` : "Pending"}
                tone="primary"
              />
              <StatusChip
                label="Rate"
                value={`RM ${MD_RATE.toFixed(2)}/kW`}
                tone="secondary"
              />
            </div>
          </div>
        </div>

        {/* Hero KPI trio */}
        <div className="grid grid-cols-3 gap-4">
          <KpiCard
            title="Original Maximum Demand"
            value={String(simulation.summary.original_md_kw || 0)}
            suffix="kW"
            detail="Observed baseline import"
            tone="secondary"
          />
          <KpiCard
            title="Optimized Maximum Demand"
            value={String(simulation.summary.optimized_md_kw || 0)}
            suffix="kW"
            detail={`${simulation.summary.peak_reduction_kw} kW shaved`}
            tone="primary"
          />
          <KpiCard
            title="Projected Monthly Savings"
            value={formatCurrencyValue(simulation.summary.md_savings_rm)}
            prefix="RM"
            detail={`${complianceRate}% ticks within limit`}
            tone="tertiary"
          />
        </div>

        {/* Main simulation chart or guided empty state */}
        <div className="panel-shadow rounded-2xl border border-outline bg-surface-2 p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="font-label text-[10px] text-primary">Simulation</p>
              <h4 className="font-display mt-1 text-lg font-semibold text-foreground">
                Baseline vs Optimized Load
              </h4>
            </div>
            {hasHistory && (
              <div className="flex gap-4 text-xs text-muted">
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-muted/50 inline-block" />
                  Baseline
                </span>
                <span className="flex items-center gap-1.5">
                  <span className={`h-2 w-2 rounded-full ${accent.legendSwatch} inline-block`} />
                  Optimized
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-danger/70 inline-block" />
                  Limit {simulation.mdLimitKw || DEFAULT_DEMAND_LIMIT_KW} kW
                </span>
              </div>
            )}
          </div>

          {hasHistory ? (
            <SimulationChart points={points} accent={accent} />
          ) : (
            <GuidedEmptyState isIdle={isIdle} isBusy={isBusy} />
          )}
        </div>

        {/* Sub charts — only shown once simulation has data */}
        {hasHistory && (
          <>
            {/* Interval stats row */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <MiniStat label="Intervals" value={String(simulation.currentInterval)} detail={`of ${simulation.totalIntervals}`} />
              <MiniStat label="Within Limit" value={String(simulation.withinLimitTicks)} detail="compliant ticks" />
              <MiniStat label="Battery Used" value={`${simulation.summary.battery_energy_used_kwh} kWh`} detail="throughput" />
              <MiniStat label="Shifted Load" value={`${simulation.summary.shifted_load_kwh} kWh`} detail="delta vs baseline" />
            </div>

            <div className="grid gap-4 xl:grid-cols-3">
              <SocChart points={points} />
              <DispatchChart points={points} />
              <BaselineChart points={points} />
            </div>
          </>
        )}
      </main>

      {/* ── RIGHT: Live Feed ── */}
      <aside
        className="border-t border-outline bg-surface-2/60 xl:border-l xl:border-t-0 xl:sticky xl:overflow-y-auto"
        style={{ top: "var(--header-h)", maxHeight: `calc(100vh - var(--header-h))` }}
      >
        <div className="space-y-5 p-5">
          {/* Live KPIs */}
          <div>
            <p className="font-label text-[10px] text-muted mb-3">Live State</p>
            <div className="space-y-3">
              <KpiCard
                title="Battery SoC"
                value={String(simulation.batterySocPercent)}
                suffix="%"
                detail={`${simulation.bessCapacityKwh} kWh installed`}
                tone="primary"
              />
              <KpiCard
                title="Last Dispatch"
                value={String(Math.round(simulation.lastDispatchKw))}
                suffix="kW"
                detail="Positive = battery discharge issued"
                tone="secondary"
              />
              <KpiCard
                title="Total Savings"
                value={formatCurrencyValue(simulation.totalSavingsRm)}
                prefix="RM"
                detail={`${simulation.shavePercentage.toFixed(1)}% shave score`}
                tone="tertiary"
              />
              
            </div>
          </div>

          {/* Agent trace */}
          <div>
            <div className="mb-3 flex items-center justify-between">
              <p className="font-label text-[10px] text-muted">Agent Trace</p>
              {simulation.agentTrace.length > 0 && (
                <span className="rounded-full border border-outline bg-surface px-2 py-0.5 text-[10px] text-muted">
                  {simulation.agentTrace.length} steps
                </span>
              )}
            </div>

            {simulation.agentTrace.length > 0 ? (
              <div className="space-y-3">
                {simulation.agentTrace.map((log, i) => (
                  <DecisionCard key={`${log.timestamp}-${i}`} log={log} index={i} />
                ))}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-outline bg-surface px-4 py-8 text-center">
                <p className="text-xs text-muted">No agent steps yet.</p>
                <p className="mt-1 text-[11px] text-muted/70">Step or play the simulation to see AI reasoning.</p>
              </div>
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}

/* ── Sub-components ── */

function StatusChip({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "primary" | "secondary" | "tertiary";
}) {
  const cls = {
    primary: "border-primary/35 bg-primary/10 text-primary",
    secondary: "border-secondary/35 bg-secondary/10 text-secondary",
    tertiary: "border-tertiary/35 bg-tertiary/10 text-tertiary",
  }[tone];
  return (
    <div className={`rounded-xl border px-3 py-2 ${cls}`}>
      <p className="font-label text-[9px] opacity-70">{label}</p>
      <p className="font-label mt-0.5 text-[11px] font-semibold">{value}</p>
    </div>
  );
}

function MiniStat({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-xl border border-outline bg-surface px-4 py-3">
      <p className="font-label text-[10px] text-muted">{label}</p>
      <p className="font-display mt-1.5 text-xl font-semibold text-foreground">{value}</p>
      <p className="mt-1 text-[11px] text-muted">{detail}</p>
    </div>
  );
}

function GuidedEmptyState({ isIdle, isBusy }: { isIdle: boolean; isBusy: boolean }) {
  const steps = [
    { n: 1, label: "Select a scenario", done: !isIdle || isBusy },
    { n: 2, label: "Set BESS capacity (optional)", done: false },
    { n: 3, label: 'Click "Run Optimization"', done: false },
  ];
  return (
    <div className="rounded-xl border border-dashed border-outline bg-surface px-6 py-14 text-center">
      <p className="text-sm font-semibold text-foreground">Start here</p>
      <p className="mt-1 text-xs text-muted">Follow these steps to run your first simulation</p>
      <div className="mt-6 flex flex-col items-center gap-3">
        {steps.map((s) => (
          <div key={s.n} className={`flex items-center gap-3 text-sm ${s.done ? "text-primary" : "text-muted"}`}>
            <span className={`flex h-6 w-6 items-center justify-center rounded-full border text-xs font-semibold ${
              s.done ? "border-primary/40 bg-primary/10 text-primary" : "border-outline bg-surface-2 text-muted"
            }`}>
              {s.done ? "✓" : s.n}
            </span>
            {s.label}
          </div>
        ))}
      </div>
    </div>
  );
}

function DecisionCard({ log, index }: { log: DecisionLog; index: number }) {
  const agentKey = log.agent as keyof typeof AGENT_STYLES;
  const styles = AGENT_STYLES[agentKey] ?? AGENT_STYLES["Controller Agent"];

  return (
    <div className="rounded-xl border border-outline bg-surface px-4 py-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full border px-2.5 py-0.5 text-[10px] ${styles.badge}`}>
          {log.agent}
        </span>
        <span className="font-label text-[9px] text-muted">{log.timestamp}</span>
      </div>
      <div className="mt-0.5 flex items-center gap-1.5">
        <span className={`h-1.5 w-1.5 rounded-full ${styles.dot}`} />
        <span className="font-label text-[9px] text-muted">Step {String(index + 1).padStart(2, "0")}</span>
      </div>
      <h4 className="font-display mt-2 text-sm font-semibold text-foreground leading-snug">
        {log.decision}
      </h4>
      <p className="mt-1 text-xs leading-5 text-muted line-clamp-3">{log.reason}</p>
      <div className="mt-2 rounded-lg border border-outline bg-surface-2 px-3 py-2 text-xs leading-5 text-foreground">
        {log.action}
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5 text-[10px]">
        {log.expected_reduction_kw ? (
          <span className="rounded-full border border-secondary/35 bg-secondary/10 px-2.5 py-0.5 text-secondary">
            Shave {log.expected_reduction_kw} kW
          </span>
        ) : null}
        {log.estimated_saving_rm ? (
          <span className="rounded-full border border-primary/35 bg-primary/10 px-2.5 py-0.5 text-primary">
            RM{formatCurrencyValue(log.estimated_saving_rm)}
          </span>
        ) : null}
      </div>
    </div>
  );
}

function Tip({ text }: { text: string }) {
  return (
    <span className="group relative inline-block ml-1 cursor-help">
      <span className="rounded-full border border-outline bg-surface-3 px-1 py-0.5 text-[9px] text-muted">?</span>
      <span className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-1.5 w-52 -translate-x-1/2 rounded-lg border border-outline bg-surface-2 px-3 py-2 text-[11px] leading-5 text-foreground opacity-0 shadow-xl transition-opacity group-hover:opacity-100">
        {text}
      </span>
    </span>
  );
}

function accentForDayType(dayType: string): AccentStyle {
  if (dayType === "holiday") return ACCENT_STYLES.tertiary;
  if (dayType === "solar_duck_curve") return ACCENT_STYLES.primary;
  if (dayType === "large_weekday") return ACCENT_STYLES.tertiary;
  return ACCENT_STYLES.secondary;
}
