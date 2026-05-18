"use client";

import { useEffect, useState } from "react";
import {
  BaselineChart,
  DispatchChart,
  SimulationChart,
  SocChart,
} from "./components/dashboard-charts";
import { KpiCard } from "./components/dashboard-primitives";
import { ACCENT_STYLES, type AccentStyle } from "./theme";
import {
  DEFAULT_DEMAND_LIMIT_KW,
  MD_RATE,
} from "./data/day-scenarios";
import { AgentStreamFeed, DayTabBar } from "./components/agent-stream-panel";
import { useSimulationController } from "./hooks/use-simulation-controller";
import { formatCurrencyValue } from "./lib/formatters";


export default function LiveDashboardPage() {
  const {
    dayOptions,
    selectedDayType,
    forecastModel,
    setForecastModel,
    bessCapacityKwh,
    setBessCapacityKwh,
    batterySoc,
    setBatterySoc,
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
    tabs,
    activeTabId,
    selectTab,
    closeTab,
    togglePinTab,
  } = useSimulationController();

  const activeTabStreams = tabs.find((t) => t.id === activeTabId)?.streams ?? [];

  const [leftOpen, setLeftOpenState] = useState(true);
  const [rightOpen, setRightOpenState] = useState(true);

  useEffect(() => {
    try {
      const l = localStorage.getItem("fusionquad-left-open");
      if (l !== null) setLeftOpenState(JSON.parse(l));
      const r = localStorage.getItem("fusionquad-right-open");
      if (r !== null) setRightOpenState(JSON.parse(r));
    } catch {}
  }, []);

  function setLeftOpen(v: boolean) {
    setLeftOpenState(v);
    try { localStorage.setItem("fusionquad-left-open", JSON.stringify(v)); } catch {}
  }
  function setRightOpen(v: boolean) {
    setRightOpenState(v);
    try { localStorage.setItem("fusionquad-right-open", JSON.stringify(v)); } catch {}
  }
  const [mobileLeft, setMobileLeft] = useState(false);
  const [mobileRight, setMobileRight] = useState(false);

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
      className="flex flex-col gap-4 overflow-hidden px-4 py-4 sm:px-6 xl:px-8"
      style={{ height: "calc(100vh - var(--header-h))" }}
    >
      {/* ── TOP ROW: Left + Center + Right ── */}
      <div className="flex flex-1 min-h-0 gap-4 overflow-hidden">

        {/* ── LEFT PANEL ── */}
        <div
          className={`relative flex-shrink-0 hidden xl:block transition-[width] duration-300 ease-in-out ${leftOpen ? "xl:w-[280px]" : "xl:w-14"}`}
        >
          {/* Inner clip — separates overflow from chevron button */}
          <div className="h-full overflow-hidden rounded-3xl border border-outline bg-surface-2/80 panel-shadow">
            <div className={`h-full ${leftOpen ? "w-[280px]" : "w-14"}`}>
              <div className="sticky top-0 z-10 border-b border-outline bg-surface-2/90 px-4 py-3 backdrop-blur">
                <p className="font-label text-[10px] text-muted">Controls</p>
                <p className="font-display text-sm font-semibold text-foreground">
                  Scenario Setup
                </p>
              </div>
              <div className="h-[calc(100%-52px)] overflow-y-auto panel-scroll">
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
                  <div className="rounded-xl border border-outline bg-surface px-4 py-4 space-y-4">
                    <div>
                      <div className="flex items-center justify-between">
                        <p className="font-label text-[10px] text-primary">
                          BESS Capacity
                          <Tip text="Battery Energy Storage System — stored energy used to discharge during peak tariff windows to shave demand spikes." />
                        </p>
                        <p className="text-lg font-semibold text-foreground font-display">
                          {bessCapacityKwh}{" "}
                          <span className="text-xs text-muted font-normal">kWh</span>
                        </p>
                      </div>
                      <input
                        aria-label="BESS capacity"
                        className="mt-3 w-full accent-[var(--primary)]"
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
                    <div>
                      <div className="flex items-center justify-between">
                        <p className="font-label text-[10px] text-primary">
                          Initial SoC
                          <Tip text="Starting state-of-charge for the battery at simulation start. Higher SoC = more energy available for peak shaving." />
                        </p>
                        <p className="text-lg font-semibold text-foreground font-display">
                          {Math.round(batterySoc * 100)}{" "}
                          <span className="text-xs text-muted font-normal">%</span>
                        </p>
                      </div>
                      <input
                        aria-label="Initial battery SoC"
                        className="mt-3 w-full accent-[var(--primary)]"
                        disabled={isBusy}
                        max={90}
                        min={10}
                        onChange={(e) => setBatterySoc(Number(e.target.value) / 100)}
                        step={5}
                        type="range"
                        value={Math.round(batterySoc * 100)}
                      />
                      <div className="mt-1 flex justify-between text-[10px] text-muted">
                        <span>10%</span>
                        <span>90%</span>
                      </div>
                    </div>
                  </div>

                  {/* Forecast model selector */}
                  <div className="rounded-xl border border-outline bg-surface px-4 py-4">
                    <p className="font-label text-[10px] text-primary mb-3">
                      Forecast Model
                      <Tip text="GRU Attention uses time covariates (hour, day, peak flag) for direct multi-step forecasting. Pure GRU uses autoregressive single-feature prediction." />
                    </p>
                    <div className="flex gap-2">
                      {(["gru_attention", "gru"] as const).map((m) => (
                        <button
                          key={m}
                          disabled={isBusy}
                          onClick={() => setForecastModel(m)}
                          className={`flex-1 rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
                            forecastModel === m
                              ? "border-primary bg-primary/10 text-primary"
                              : "border-outline bg-surface-2 text-muted hover:border-primary/50 hover:text-foreground"
                          } disabled:cursor-not-allowed disabled:opacity-50`}
                        >
                          {m === "gru_attention" ? "GRU + Attention" : "GRU Pure"}
                        </button>
                      ))}
                    </div>
                    <p className="mt-2 text-[10px] text-muted">
                      {forecastModel === "gru_attention"
                        ? "6-feature · direct multi-step · default"
                        : "1-feature · autoregressive · baseline"}
                    </p>
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
                  <IconStrip icon="⚡" tooltip={`${bessCapacityKwh} kWh · SoC ${Math.round(batterySoc * 100)}%`} />
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
        <main className="flex-1 min-w-0 flex flex-col overflow-hidden rounded-3xl border border-outline bg-surface-2/70 panel-shadow">
          <div className="flex items-center gap-3 px-5 py-3 border-b border-outline bg-surface-2/90 backdrop-blur">
            <p className="font-label text-[10px] text-muted">Overview</p>
            <p className="font-display text-sm font-semibold text-foreground">Live Simulation</p>
            <div className="ml-auto flex items-center gap-2">
              <span className="rounded-full border border-outline bg-surface px-2.5 py-1 text-[10px] text-muted">
                {activeDay.label}
              </span>
            </div>
          </div>

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

          <div className="flex-1 overflow-y-auto panel-scroll">
            <div className="space-y-5 p-5 xl:p-6">
              {/* Day title + status row */}
              <div className="panel-shadow panel-noise rounded-3xl border border-outline bg-surface-2 px-6 py-5">
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
              <div className="panel-shadow rounded-3xl border border-outline bg-surface-2 p-5">
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
          <div className="h-full overflow-hidden rounded-3xl border border-outline bg-surface-2/80 panel-shadow">
            <div className="w-[320px] h-full flex flex-col">
              <div className="flex-shrink-0 border-b border-outline bg-surface-2/90 px-4 py-3 backdrop-blur">
                <p className="font-label text-[10px] text-muted">Live State</p>
                <p className="font-display text-sm font-semibold text-foreground">
                  Battery + Dispatch
                </p>
              </div>

              {/* KPI strip — compact 3-column row */}
              <div className="flex-shrink-0 grid grid-cols-3 divide-x divide-outline border-b border-outline">
                <div className="px-3 py-2.5">
                  <p className="font-label text-[9px] text-muted uppercase tracking-wide">Batt SoC</p>
                  <p className="font-display text-lg font-semibold text-foreground mt-0.5">
                    {simulation.batterySocPercent}<span className="text-xs text-muted font-normal ml-0.5">%</span>
                  </p>
                  <p className="text-[9px] text-muted truncate">{simulation.bessCapacityKwh} kWh</p>
                </div>
                <div className="px-3 py-2.5">
                  <p className="font-label text-[9px] text-muted uppercase tracking-wide">Dispatch</p>
                  <p className="font-display text-lg font-semibold text-foreground mt-0.5">
                    {Math.round(simulation.lastDispatchKw)}<span className="text-xs text-muted font-normal ml-0.5">kW</span>
                  </p>
                  <p className="text-[9px] text-muted truncate">last issued</p>
                </div>
                <div className="px-3 py-2.5">
                  <p className="font-label text-[9px] text-muted uppercase tracking-wide">Savings</p>
                  <p className="font-display text-lg font-semibold text-foreground mt-0.5">
                    <span className="text-xs text-muted font-normal mr-0.5">RM</span>{formatCurrencyValue(simulation.totalSavingsRm)}
                  </p>
                  <p className="text-[9px] text-muted truncate">{simulation.shavePercentage.toFixed(1)}% shave</p>
                </div>
              </div>

              {/* Agent stream section */}
              <div className="flex-shrink-0 px-3 pt-3 pb-2">
                <div className="flex items-center gap-2 mb-2">
                  <p className="font-label text-[10px] text-muted">Agent Stream</p>
                  {isBusy && (
                    <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
                  )}
                  {tabs.length > 0 && (
                    <span className="ml-auto rounded-full border border-outline bg-surface px-2 py-0.5 text-[10px] text-muted">
                      {tabs.length} {tabs.length === 1 ? "run" : "runs"}
                    </span>
                  )}
                </div>
                <DayTabBar
                  tabs={tabs}
                  activeTabId={activeTabId}
                  onSelect={selectTab}
                  onClose={closeTab}
                  onTogglePin={togglePinTab}
                />
              </div>

              {/* Stream feed — fills remaining space, scrollable */}
              <div className="flex-1 min-h-0 overflow-y-auto panel-scroll px-3 pb-3">
                <AgentStreamFeed streams={activeTabStreams} />
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
          <div className="w-80 max-w-[85vw] bg-surface-2 border-l border-outline flex flex-col">
            <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-outline flex-shrink-0">
              <p className="font-label text-[11px] text-muted">Live State</p>
              <button
                type="button"
                onClick={() => setMobileRight(false)}
                className="text-muted hover:text-foreground text-sm"
              >
                ✕
              </button>
            </div>
            <div className="flex-shrink-0 grid grid-cols-3 divide-x divide-outline border-b border-outline">
              <div className="px-3 py-2.5">
                <p className="font-label text-[9px] text-muted uppercase tracking-wide">Batt SoC</p>
                <p className="font-display text-lg font-semibold text-foreground mt-0.5">
                  {simulation.batterySocPercent}<span className="text-xs text-muted font-normal ml-0.5">%</span>
                </p>
                <p className="text-[9px] text-muted truncate">{simulation.bessCapacityKwh} kWh</p>
              </div>
              <div className="px-3 py-2.5">
                <p className="font-label text-[9px] text-muted uppercase tracking-wide">Dispatch</p>
                <p className="font-display text-lg font-semibold text-foreground mt-0.5">
                  {Math.round(simulation.lastDispatchKw)}<span className="text-xs text-muted font-normal ml-0.5">kW</span>
                </p>
                <p className="text-[9px] text-muted truncate">last issued</p>
              </div>
              <div className="px-3 py-2.5">
                <p className="font-label text-[9px] text-muted uppercase tracking-wide">Savings</p>
                <p className="font-display text-lg font-semibold text-foreground mt-0.5">
                  <span className="text-xs text-muted font-normal mr-0.5">RM</span>{formatCurrencyValue(simulation.totalSavingsRm)}
                </p>
                <p className="text-[9px] text-muted truncate">{simulation.shavePercentage.toFixed(1)}% shave</p>
              </div>
            </div>
            <div className="flex-shrink-0 px-4 pt-3 pb-2">
              <p className="font-label text-[10px] text-muted mb-2">Agent Stream</p>
              <DayTabBar
                tabs={tabs}
                activeTabId={activeTabId}
                onSelect={selectTab}
                onClose={closeTab}
                onTogglePin={togglePinTab}
              />
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto panel-scroll px-4 pb-4">
              <AgentStreamFeed streams={activeTabStreams} />
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
