"use client";

import { useEffect, useRef, useState, useCallback } from "react";
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

function useLocalStorage<T>(key: string, initial: T): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(() => {
    if (typeof window === "undefined") return initial;
    try {
      const stored = localStorage.getItem(key);
      return stored !== null ? (JSON.parse(stored) as T) : initial;
    } catch {
      return initial;
    }
  });
  const set = useCallback(
    (v: T) => {
      setValue(v);
      try {
        localStorage.setItem(key, JSON.stringify(v));
      } catch {}
    },
    [key],
  );
  return [value, set];
}

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

  const [leftOpen, setLeftOpen] = useLocalStorage("fusionquad-left-open", true);
  const [rightOpen, setRightOpen] = useLocalStorage("fusionquad-right-open", true);
  const [drawerOpen, setDrawerOpen] = useLocalStorage("fusionquad-drawer-open", false);
  const [mobileLeft, setMobileLeft] = useState(false);
  const [mobileRight, setMobileRight] = useState(false);

  const traceRef = useRef<HTMLDivElement>(null);
  const userScrolledRef = useRef(false);
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  useEffect(() => {
    if (!userScrolledRef.current && traceRef.current) {
      traceRef.current.scrollLeft = traceRef.current.scrollWidth;
    }
  }, [simulation.agentTrace.length]);

  const handleTraceScroll = useCallback(() => {
    const el = traceRef.current;
    if (!el) return;
    const atRight = el.scrollWidth - el.scrollLeft - el.clientWidth < 40;
    userScrolledRef.current = !atRight;
    setShowScrollBtn(!atRight);
  }, []);

  const scrollToLatest = useCallback(() => {
    if (traceRef.current) {
      traceRef.current.scrollLeft = traceRef.current.scrollWidth;
      userScrolledRef.current = false;
      setShowScrollBtn(false);
    }
  }, []);

  const accent = accentForDayType(selectedDayType);
  const activeDay = dayOptions.find((o) => o.key === selectedDayType) ?? dayOptions[0];
  const points = simulation.history;
  const hasHistory = points.length > 0;
  const isIdle = simulation.status === "idle";
  const complianceRate =
    simulation.currentInterval > 0
      ? Math.round(
          (simulation.withinLimitTicks / Math.max(simulation.currentInterval, 1)) * 100,
        )
      : 0;

  return (
    <div
      className="flex flex-col -mx-4 sm:-mx-6 xl:-mx-8 -my-6 overflow-hidden"
      style={{ height: "calc(100vh - var(--header-h))" }}
    >
      {/* ── TOP ROW: Left + Center + Right ── */}
      <div className="flex flex-1 min-h-0 overflow-hidden">

        {/* ── LEFT PANEL ── */}
        <div
          className={`relative flex-shrink-0 hidden xl:block transition-[width] duration-300 ease-in-out ${leftOpen ? "xl:w-[300px]" : "xl:w-12"}`}
        >
          {/* Inner clip — separates overflow from chevron button */}
          <div className="h-full overflow-hidden border-r border-outline bg-surface-2/60">
            <div className={`h-full overflow-y-auto ${leftOpen ? "w-[300px]" : "w-12"}`}>
              {leftOpen ? (
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
                          {bessCapacityKwh}{" "}
                          <span className="text-sm text-muted font-normal">kWh</span>
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

                  {/* Time window */}
                  <div className="rounded-xl border border-outline bg-surface px-4 py-4">
                    <p className="font-label text-[10px] text-primary mb-3">Time Window</p>
                    {metadataLoading ? (
                      <p className="text-[11px] text-muted">Loading available dates…</p>
                    ) : scenarioMetadata ? (
                      <div className="space-y-2">
                        <div>
                          <label className="text-[10px] text-muted" htmlFor="range-start">
                            Start <span className="text-danger">*</span>
                          </label>
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
                              const endStillValid =
                                newStart && timeRange.end && timeRange.end >= newStart;
                              setTimeRange({
                                start: newStart,
                                end: endStillValid ? timeRange.end : null,
                              });
                            }}
                          />
                        </div>
                        <div>
                          <label className="text-[10px] text-muted" htmlFor="range-end">
                            End <span className="text-danger">*</span>
                          </label>
                          <input
                            id="range-end"
                            className="mt-1 w-full rounded-lg border border-outline bg-surface-2 px-3 py-1.5 text-xs"
                            disabled={isBusy}
                            max={scenarioMetadata.available_end.slice(0, 16)}
                            min={
                              timeRange.start ??
                              scenarioMetadata.available_start.slice(0, 16)
                            }
                            type="datetime-local"
                            value={timeRange.end ?? ""}
                            onChange={(e) =>
                              setTimeRange({
                                start: timeRange.start,
                                end: e.target.value || null,
                              })
                            }
                          />
                        </div>
                        <p className="text-[10px] text-muted">
                          Available: {scenarioMetadata.available_start.slice(0, 10)} →{" "}
                          {scenarioMetadata.available_end.slice(0, 10)}
                        </p>
                      </div>
                    ) : (
                      <p className="text-[11px] text-muted">
                        Select a scenario to see available dates.
                      </p>
                    )}
                  </div>

                  {/* CTA */}
                  <button
                    type="button"
                    disabled={!canRun}
                    onClick={() => void runOptimization()}
                    className="w-full rounded-xl border border-primary/40 bg-primary/15 px-5 py-3 text-sm font-semibold text-primary transition hover:bg-primary/25 disabled:opacity-50 active:scale-95"
                  >
                    {isBusy ? "Working…" : "▶ Run Optimization"}
                  </button>
                  {!canRun && !isBusy && scenarioMetadata && (
                    <p className="text-center text-[10px] text-muted">
                      Select start and end date to run
                    </p>
                  )}
                  {errorMessage && (
                    <div className="rounded-xl border border-danger/35 bg-danger/8 px-4 py-3 text-xs text-danger">
                      {errorMessage}
                    </div>
                  )}
                </div>
              ) : (
                /* Icon strip (collapsed) */
                <div className="flex flex-col items-center gap-4 py-5">
                  <IconStrip icon="◈" tooltip={activeDay?.label ?? "Scenario"} />
                  <IconStrip icon="⚡" tooltip={`${bessCapacityKwh} kWh`} />
                  <IconStrip
                    icon="⏱"
                    tooltip={timeRange.start ? timeRange.start.slice(0, 10) : "No date set"}
                  />
                  <IconStrip
                    icon="▶"
                    tooltip={isBusy ? "Working…" : "Run Optimization"}
                    onClick={canRun ? () => void runOptimization() : undefined}
                    disabled={!canRun || isBusy}
                    active={isBusy}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Left chevron — sits on the right border, pokes into center */}
          <button
            type="button"
            aria-label={leftOpen ? "Collapse panel" : "Expand panel"}
            onClick={() => setLeftOpen(!leftOpen)}
            className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 z-20 flex h-6 w-6 items-center justify-center rounded-full border border-outline bg-surface text-[9px] text-muted shadow-md hover:text-foreground transition"
          >
            {leftOpen ? "◀" : "▶"}
          </button>
        </div>

        {/* ── CENTER ── */}
        <main className="flex-1 min-w-0 flex flex-col overflow-hidden">
          {/* Mobile toolbar */}
          <div className="xl:hidden flex items-center gap-3 px-4 py-2.5 border-b border-outline bg-surface-2/60 flex-shrink-0">
            <button
              type="button"
              onClick={() => setMobileLeft(true)}
              className="text-xs text-muted hover:text-foreground transition"
            >
              ☰ Controls
            </button>
            <div className="ml-auto">
              <button
                type="button"
                onClick={() => setMobileRight(true)}
                className="text-xs text-muted hover:text-foreground transition"
              >
                Stats ▸
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            <div className="space-y-5 p-5 xl:p-6">
              {/* Day title + status row */}
              <div className="panel-shadow panel-noise rounded-2xl border border-outline bg-surface-2 px-6 py-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="font-label text-[10px] text-muted">Live simulation</p>
                    <h3 className="font-display mt-2 text-2xl font-semibold text-foreground sm:text-3xl">
                      {activeDay.label}
                    </h3>
                    <p className="mt-2 max-w-lg text-sm leading-6 text-muted">
                      {activeDay.blurb}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <StatusChip
                      label="Status"
                      value={simulation.status.toUpperCase()}
                      tone={simulation.status === "completed" ? "primary" : "secondary"}
                    />
                    <StatusChip
                      label="Interval"
                      value={`${simulation.currentInterval} / ${simulation.totalIntervals || 48}`}
                      tone="secondary"
                    />
                    <StatusChip
                      label="Forecast"
                      value={
                        simulation.forecastKw != null
                          ? `${Math.round(simulation.forecastKw)} kW`
                          : "Pending"
                      }
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

              {/* Main simulation chart */}
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
                        <span
                          className={`h-2 w-2 rounded-full ${accent.legendSwatch} inline-block`}
                        />
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

              {/* Sub charts — only after simulation has data */}
              {hasHistory && (
                <>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <MiniStat
                      label="Intervals"
                      value={String(simulation.currentInterval)}
                      detail={`of ${simulation.totalIntervals}`}
                    />
                    <MiniStat
                      label="Within Limit"
                      value={String(simulation.withinLimitTicks)}
                      detail="compliant ticks"
                    />
                    <MiniStat
                      label="Battery Used"
                      value={`${simulation.summary.battery_energy_used_kwh} kWh`}
                      detail="throughput"
                    />
                    <MiniStat
                      label="Shifted Load"
                      value={`${simulation.summary.shifted_load_kwh} kWh`}
                      detail="delta vs baseline"
                    />
                  </div>
                  <div className="grid gap-4 xl:grid-cols-3">
                    <SocChart points={points} />
                    <DispatchChart points={points} />
                    <BaselineChart points={points} />
                  </div>
                </>
              )}
            </div>
          </div>
        </main>

        {/* ── RIGHT PANEL ── */}
        <div
          className={`relative flex-shrink-0 hidden xl:block transition-[width] duration-300 ease-in-out ${rightOpen ? "xl:w-[320px]" : "xl:w-0"}`}
        >
          <div className="h-full overflow-hidden border-l border-outline bg-surface-2/60">
            <div className="w-[320px] h-full overflow-y-auto">
              <div className="space-y-5 p-5">
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
            </div>
          </div>

          {/* Right chevron — sits on the left border, pokes into center */}
          <button
            type="button"
            aria-label={rightOpen ? "Collapse panel" : "Expand panel"}
            onClick={() => setRightOpen(!rightOpen)}
            className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1/2 z-20 flex h-6 w-6 items-center justify-center rounded-full border border-outline bg-surface text-[9px] text-muted shadow-md hover:text-foreground transition"
          >
            {rightOpen ? "▶" : "◀"}
          </button>
        </div>
      </div>

      {/* ── BOTTOM DRAWER: Agent Trace ── */}
      <div
        className="flex-shrink-0 border-t border-outline bg-surface-2/80 backdrop-blur overflow-hidden transition-[height] duration-300 ease-in-out"
        style={{ height: drawerOpen ? 260 : 40 }}
      >
        {/* Tab / header */}
        <button
          type="button"
          onClick={() => setDrawerOpen(!drawerOpen)}
          className="flex w-full h-10 items-center gap-3 px-5 text-left hover:bg-surface-3/40 transition flex-shrink-0"
        >
          <span className="font-label text-[10px] text-muted">Agent Trace</span>
          {simulation.agentTrace.length > 0 && (
            <span className="rounded-full border border-outline bg-surface px-2 py-0.5 text-[10px] text-muted">
              {simulation.agentTrace.length} steps
            </span>
          )}
          {isBusy && (
            <span className="ml-1 h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
          )}
          <span className="ml-auto text-[10px] text-muted">{drawerOpen ? "▼" : "▲"}</span>
        </button>

        {/* Horizontal card timeline */}
        <div className="relative" style={{ height: 220 }}>
          <div
            ref={traceRef}
            onScroll={handleTraceScroll}
            className="h-full overflow-x-auto overflow-y-hidden px-5 pt-2 pb-4 flex items-start gap-3"
          >
            {simulation.agentTrace.length > 0 ? (
              simulation.agentTrace.map((log, i) => (
                <DecisionCard key={`${log.timestamp}-${i}`} log={log} index={i} compact />
              ))
            ) : (
              <div className="flex h-full w-full items-center justify-center">
                <p className="text-xs text-muted">
                  No agent steps yet. Run optimization to see trace.
                </p>
              </div>
            )}
          </div>
          {showScrollBtn && (
            <button
              type="button"
              onClick={scrollToLatest}
              className="absolute right-5 bottom-4 rounded-full border border-outline bg-surface px-3 py-1 text-[10px] text-muted shadow-md hover:text-foreground transition"
            >
              → Latest
            </button>
          )}
        </div>
      </div>

      {/* ── MOBILE: Left overlay ── */}
      {mobileLeft && (
        <div className="xl:hidden fixed inset-0 z-40 flex">
          <div className="w-80 max-w-[85vw] bg-surface-2 border-r border-outline overflow-y-auto">
            <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-outline">
              <p className="font-label text-[11px] text-muted">Controls</p>
              <button
                type="button"
                onClick={() => setMobileLeft(false)}
                className="text-muted hover:text-foreground text-sm"
              >
                ✕
              </button>
            </div>
            <div className="space-y-4 p-5">
              <div className="space-y-2">
                {dayOptions.map((option) => {
                  const isActive = option.key === selectedDayType;
                  const optAccent = accentForDayType(option.key);
                  return (
                    <button
                      key={option.key}
                      type="button"
                      disabled={isBusy}
                      onClick={() => {
                        void handleDayTypeChange(option.key);
                        setMobileLeft(false);
                      }}
                      className={`w-full rounded-xl border px-4 py-3 text-left transition ${
                        isActive
                          ? `${optAccent.activeBorder} ${optAccent.activeBg}`
                          : "border-outline bg-surface hover:bg-surface-3"
                      }`}
                    >
                      <p className={`font-label text-[10px] ${isActive ? optAccent.activeText : "text-muted"}`}>
                        {option.label}
                      </p>
                    </button>
                  );
                })}
              </div>
              <button
                type="button"
                disabled={!canRun}
                onClick={() => {
                  void runOptimization();
                  setMobileLeft(false);
                }}
                className="w-full rounded-xl border border-primary/40 bg-primary/15 px-5 py-3 text-sm font-semibold text-primary transition hover:bg-primary/25 disabled:opacity-50"
              >
                {isBusy ? "Working…" : "▶ Run Optimization"}
              </button>
            </div>
          </div>
          <div className="flex-1 bg-black/40" onClick={() => setMobileLeft(false)} />
        </div>
      )}

      {/* ── MOBILE: Right overlay ── */}
      {mobileRight && (
        <div className="xl:hidden fixed inset-0 z-40 flex justify-end">
          <div className="flex-1 bg-black/40" onClick={() => setMobileRight(false)} />
          <div className="w-80 max-w-[85vw] bg-surface-2 border-l border-outline overflow-y-auto">
            <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-outline">
              <p className="font-label text-[11px] text-muted">Live State</p>
              <button
                type="button"
                onClick={() => setMobileRight(false)}
                className="text-muted hover:text-foreground text-sm"
              >
                ✕
              </button>
            </div>
            <div className="space-y-3 p-5">
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
        </div>
      )}
    </div>
  );
}

/* ── Sub-components ── */

function IconStrip({
  icon,
  tooltip,
  onClick,
  disabled,
  active,
}: {
  icon: string;
  tooltip: string;
  onClick?: () => void;
  disabled?: boolean;
  active?: boolean;
}) {
  return (
    <div className="group relative flex flex-col items-center">
      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        className={`flex h-8 w-8 items-center justify-center rounded-lg border text-sm transition ${
          active
            ? "border-primary/40 bg-primary/15 text-primary"
            : "border-outline bg-surface text-muted hover:text-foreground hover:bg-surface-3"
        } disabled:opacity-40`}
      >
        {icon}
      </button>
      <span className="pointer-events-none absolute left-full ml-2 top-1/2 -translate-y-1/2 z-50 whitespace-nowrap rounded-lg border border-outline bg-surface-2 px-2.5 py-1 text-[11px] text-foreground opacity-0 shadow-xl transition-opacity group-hover:opacity-100">
        {tooltip}
      </span>
    </div>
  );
}

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
          <div
            key={s.n}
            className={`flex items-center gap-3 text-sm ${s.done ? "text-primary" : "text-muted"}`}
          >
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full border text-xs font-semibold ${
                s.done
                  ? "border-primary/40 bg-primary/10 text-primary"
                  : "border-outline bg-surface-2 text-muted"
              }`}
            >
              {s.done ? "✓" : s.n}
            </span>
            {s.label}
          </div>
        ))}
      </div>
    </div>
  );
}

function DecisionCard({
  log,
  index,
  compact = false,
}: {
  log: DecisionLog;
  index: number;
  compact?: boolean;
}) {
  const agentKey = log.agent as keyof typeof AGENT_STYLES;
  const styles = AGENT_STYLES[agentKey] ?? AGENT_STYLES["Controller Agent"];

  return (
    <div
      className={`rounded-xl border border-outline bg-surface px-4 py-4 flex-shrink-0 ${compact ? "w-64" : "w-full"}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full border px-2.5 py-0.5 text-[10px] ${styles.badge}`}>
          {log.agent}
        </span>
        <span className="font-label text-[9px] text-muted">{log.timestamp}</span>
      </div>
      <div className="mt-0.5 flex items-center gap-1.5">
        <span className={`h-1.5 w-1.5 rounded-full ${styles.dot}`} />
        <span className="font-label text-[9px] text-muted">
          Step {String(index + 1).padStart(2, "0")}
        </span>
      </div>
      <h4 className="font-display mt-2 text-sm font-semibold text-foreground leading-snug">
        {log.decision}
      </h4>
      <p className="mt-1 text-xs leading-5 text-muted line-clamp-3">{log.reason}</p>
      {!compact && (
        <div className="mt-2 rounded-lg border border-outline bg-surface-2 px-3 py-2 text-xs leading-5 text-foreground">
          {log.action}
        </div>
      )}
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
      <span className="rounded-full border border-outline bg-surface-3 px-1 py-0.5 text-[9px] text-muted">
        ?
      </span>
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
