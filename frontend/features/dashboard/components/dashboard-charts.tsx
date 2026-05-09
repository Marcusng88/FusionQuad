import type { ReactNode } from "react";

import { DEMAND_LIMIT, TIMESTAMPS } from "@/features/dashboard/data/scenarios";
import type { AccentStyle } from "@/features/dashboard/theme";
import type { EnergyPoint } from "@/features/dashboard/types";

export function BaselineChart({ points }: { points: EnergyPoint[] }) {
  return (
    <div className="rounded-2xl border border-outline bg-surface px-4 py-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-display text-lg font-semibold text-foreground">Demand profile and target limit</p>
          <p className="mt-1 text-sm text-muted">
            Original grid import, solar contribution, and weekday peak shading.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-[11px] text-muted">
          <Legend swatch="bg-secondary" label="Grid import" />
          <Legend swatch="bg-primary" label="Solar" />
          <Legend swatch="bg-danger" label="800 kW limit" />
        </div>
      </div>
      <ChartCanvas>
        {renderGrid()}
        {renderPeakWindow()}
        {renderLimitLine()}
        <path d={areaPath(points.map((point) => point.solar_kw), 0, 360)} fill="rgba(78, 222, 163, 0.18)" />
        <path d={linePath(points.map((point) => point.solar_kw), 0, 360)} fill="none" stroke="#4edea3" strokeWidth="3" />
        <path
          d={linePath(points.map((point) => point.original_grid_import_kw), 0, 1000)}
          fill="none"
          stroke="#adc6ff"
          strokeWidth="3"
          strokeDasharray="8 8"
        />
      </ChartCanvas>
      <AxisLabels />
    </div>
  );
}

export function SimulationChart({
  points,
  accent,
}: {
  points: EnergyPoint[];
  accent: AccentStyle;
}) {
  return (
    <div className="rounded-2xl border border-outline bg-surface px-4 py-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-display text-lg font-semibold text-foreground">Original vs optimized grid import</p>
          <p className="mt-1 text-sm text-muted">
            The main comparison view keeps the savings story immediate and visible.
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-[11px] text-muted">
          <Legend swatch="bg-muted" label="Original" />
          <Legend swatch={accent.legendSwatch} label="Optimized" />
          <Legend swatch="bg-danger" label="Demand limit" />
        </div>
      </div>
      <ChartCanvas>
        {renderGrid()}
        {renderPeakWindow()}
        {renderLimitLine()}
        <path
          d={linePath(points.map((point) => point.original_grid_import_kw), 0, 1000)}
          fill="none"
          stroke="#bbcabf"
          strokeWidth="3"
          strokeDasharray="8 8"
        />
        <path
          d={areaPath(points.map((point) => point.solar_kw), 0, 360)}
          fill="rgba(78, 222, 163, 0.1)"
        />
        <path
          d={linePath(points.map((point) => point.optimized_grid_import_kw), 0, 1000)}
          fill="none"
          stroke={accent.hex}
          strokeWidth="4"
        />
      </ChartCanvas>
      <AxisLabels />
    </div>
  );
}

export function SocChart({ points }: { points: EnergyPoint[] }) {
  return (
    <SmallChartCard title="Battery SoC (%)" legend="Reserve-aware state of charge">
      <ChartCanvas compact>
        {renderGrid(48)}
        <path d={areaPath(points.map((point) => point.battery_soc_percent), 0, 100)} fill="rgba(78, 222, 163, 0.12)" />
        <path
          d={linePath(points.map((point) => point.battery_soc_percent), 0, 100)}
          fill="none"
          stroke="#4edea3"
          strokeWidth="3"
        />
      </ChartCanvas>
      <AxisLabels compact yLabels={["100", "75", "50", "25", "0"]} />
    </SmallChartCard>
  );
}

export function DispatchChart({ points }: { points: EnergyPoint[] }) {
  return (
    <SmallChartCard title="Battery dispatch (kW)" legend="Positive charge, negative discharge">
      <ChartCanvas compact>
        {renderGrid(48)}
        <line x1="0" x2="1000" y1="120" y2="120" stroke="rgba(134,148,138,0.65)" strokeWidth="1.5" />
        {renderBars(points.map((point) => point.battery_power_kw), -100, 100, "#e29100", "#10b981")}
      </ChartCanvas>
      <AxisLabels compact yLabels={["100", "50", "0", "-50", "-100"]} />
    </SmallChartCard>
  );
}

export function ShiftChart({ points }: { points: EnergyPoint[] }) {
  return (
    <SmallChartCard title="Flexible load shifted (kW)" legend="Curtailment and rescheduling events">
      <ChartCanvas compact>
        {renderGrid(48)}
        {renderBars(points.map((point) => point.shifted_load_kw), 0, 100, "#ffb95f")}
      </ChartCanvas>
      <AxisLabels compact yLabels={["100", "75", "50", "25", "0"]} />
    </SmallChartCard>
  );
}

function SmallChartCard({
  title,
  legend,
  children,
}: {
  title: string;
  legend: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-outline bg-surface px-4 py-4">
      <p className="font-display text-lg font-semibold text-foreground">{title}</p>
      <p className="mt-1 text-sm text-muted">{legend}</p>
      <div className="mt-4">{children}</div>
    </div>
  );
}

function ChartCanvas({
  children,
  compact = false,
}: {
  children: ReactNode;
  compact?: boolean;
}) {
  return (
    <div
      className={`chart-grid relative overflow-hidden rounded-2xl border border-outline bg-surface-2 ${
        compact ? "h-[230px]" : "h-[360px]"
      }`}
    >
      <div className="absolute inset-y-0 left-0 w-10 border-r border-outline/70" />
      <div className="absolute bottom-0 left-10 right-0 h-10 border-t border-outline/70" />
      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 1000 280" preserveAspectRatio="none">
        {children}
      </svg>
    </div>
  );
}

function AxisLabels({
  compact = false,
  yLabels = ["1000", "800", "600", "400", "200", "0"],
}: {
  compact?: boolean;
  yLabels?: string[];
}) {
  const bottomClass = compact ? "mt-3" : "mt-4";

  return (
    <>
      <div className="mt-2 grid grid-cols-6 text-[11px] text-muted">
        {yLabels.map((label) => (
          <span key={label}>{label}</span>
        ))}
      </div>
      <div className={`${bottomClass} grid grid-cols-12 text-[11px] text-muted`}>
        {TIMESTAMPS.map((label) => (
          <span key={label}>{label}</span>
        ))}
      </div>
    </>
  );
}

function Legend({ swatch, label }: { swatch: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className={`h-2.5 w-2.5 rounded-full ${swatch}`} />
      <span>{label}</span>
    </div>
  );
}

function renderGrid(step = 56) {
  const lines: ReactNode[] = [];

  for (let y = step; y < 280; y += step) {
    lines.push(
      <line key={`y-${y}`} x1="0" x2="1000" y1={y} y2={y} stroke="rgba(60,74,66,0.35)" strokeWidth="1" />,
    );
  }

  for (let x = 84; x < 1000; x += 84) {
    lines.push(
      <line key={`x-${x}`} x1={x} x2={x} y1="0" y2="280" stroke="rgba(60,74,66,0.28)" strokeWidth="1" />,
    );
  }

  return lines;
}

function renderPeakWindow() {
  return <rect x="584" y="0" width="332" height="280" fill="rgba(255,185,95,0.1)" stroke="rgba(255,185,95,0.18)" />;
}

function renderLimitLine() {
  const y = scaleValue(DEMAND_LIMIT, 0, 1000);

  return <line x1="0" x2="1000" y1={y} y2={y} stroke="#ff8c7a" strokeWidth="2.5" strokeDasharray="10 8" />;
}

function renderBars(values: number[], min: number, max: number, positive: string, negative?: string) {
  const width = 1000;
  const height = 280;
  const gap = width / values.length;
  const barWidth = Math.min(44, gap * 0.42);
  const zero = scaleValue(0, min, max, height);

  return values.map((value, index) => {
    const x = index * gap + gap / 2 - barWidth / 2;
    const y = scaleValue(value, min, max, height);
    const fill = value < 0 && negative ? negative : positive;

    return (
      <rect
        key={`${value}-${index}`}
        x={x}
        y={Math.min(y, zero)}
        width={barWidth}
        height={Math.abs(zero - y)}
        rx="6"
        fill={fill}
        opacity="0.88"
      />
    );
  });
}

function linePath(values: number[], min: number, max: number) {
  return values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * 1000;
      const y = scaleValue(value, min, max);

      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");
}

function areaPath(values: number[], min: number, max: number) {
  const line = linePath(values, min, max);
  return `${line} L 1000 280 L 0 280 Z`;
}

function scaleValue(value: number, min: number, max: number, height = 280) {
  const safeMax = max === min ? max + 1 : max;
  return height - ((value - min) / (safeMax - min)) * height;
}
