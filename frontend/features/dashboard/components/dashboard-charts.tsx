"use client";

import type { ReactNode } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  AreaChart,
  BarChart,
  Area,
  Line,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ReferenceArea,
  Cell,
} from "recharts";

import type { AccentStyle } from "@/features/dashboard/theme";
import type { EnergyPoint } from "@/features/dashboard/types";

const C = {
  grid: "rgba(46,58,82,0.6)",
  primary: "#4edea3",
  secondary: "#adc6ff",
  tertiary: "#ffb95f",
  danger: "#ff8c7a",
  muted: "#8a99b8",
  surface: "#131b2e",
  outline: "#2e3a52",
} as const;

const TOOLTIP_STYLE = {
  backgroundColor: C.surface,
  border: `1px solid ${C.outline}`,
  borderRadius: "8px",
  color: "#dae2fd",
  fontSize: "12px",
  padding: "8px 12px",
};

const TICK = { fill: C.muted, fontSize: 11 };
const AXIS = { axisLine: { stroke: C.outline }, tickLine: false } as const;

function fmtTs(ts: string) {
  if (ts.includes(" ")) return ts.split(" ")[1].slice(0, 5);
  return ts.slice(0, 5);
}

function peakBounds(points: EnergyPoint[]) {
  const peaks = points.filter((p) => p.is_peak_period);
  if (!peaks.length) return null;
  return { x1: peaks[0].timestamp, x2: peaks[peaks.length - 1].timestamp };
}

function xInterval(count: number) {
  if (count <= 12) return 0;
  if (count <= 24) return 1;
  return Math.floor(count / 12) - 1;
}

function yMax(max: number) {
  return Math.ceil((max + 50) / 100) * 100;
}

export function BaselineChart({ points }: { points: EnergyPoint[] }) {
  const peak = peakBounds(points);
  const hasPrediction = points.some((p) => p.predicted_kw != null);

  return (
    <Card
      title="ML Model Forecast vs Actual Load"
      subtitle="GRU model's next-interval prediction compared to actual grid import."
      legend={
        <>
          <Dot color={C.secondary} label="Actual load" />
          {hasPrediction && <Dot color={C.tertiary} label="GRU forecast (T+1)" />}
        </>
      }
    >
      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart data={points} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={C.grid} strokeDasharray="4 4" vertical={false} />
          {peak && (
            <ReferenceArea
              x1={peak.x1}
              x2={peak.x2}
              fill="rgba(255,185,95,0.08)"
              stroke="rgba(255,185,95,0.18)"
            />
          )}
          <XAxis
            dataKey="timestamp"
            tickFormatter={fmtTs}
            tick={TICK}
            {...AXIS}
            interval={xInterval(points.length)}
          />
          <YAxis
            tick={TICK}
            {...AXIS}
            width={52}
            domain={[0, (max: number) => yMax(max)]}
            tickFormatter={(v) => String(v)}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(v: any, n: any) => [`${Math.round(Number(v ?? 0))} kW`, n]}
            labelFormatter={(l) => fmtTs(String(l))}
          />
          <Line
            dataKey="original_grid_import_kw"
            name="Actual load"
            stroke={C.secondary}
            strokeWidth={2.5}
            dot={false}
          />
          {hasPrediction && (
            <Line
              dataKey="predicted_kw"
              name="GRU forecast (T+1)"
              stroke={C.tertiary}
              strokeWidth={2}
              strokeDasharray="6 4"
              dot={false}
              connectNulls={false}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function SimulationChart({
  points,
  accent,
}: {
  points: EnergyPoint[];
  accent: AccentStyle;
}) {
  const peak = peakBounds(points);
  const limit = points[0]?.demand_limit_kw ?? 800;

  return (
    <Card
      title="Original vs optimized grid import"
      subtitle="The main comparison view keeps the savings story immediate and visible."
      legend={
        <>
          <Dot color={C.muted} label="Original" />
          <Dot color={accent.hex} label="Optimized" />
          <Dot color={C.danger} label="Demand limit" />
        </>
      }
    >
      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart data={points} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={C.grid} strokeDasharray="4 4" vertical={false} />
          {peak && (
            <ReferenceArea
              x1={peak.x1}
              x2={peak.x2}
              fill="rgba(255,185,95,0.08)"
              stroke="rgba(255,185,95,0.18)"
            />
          )}
          <ReferenceLine y={limit} stroke={C.danger} strokeDasharray="10 6" strokeWidth={2} />
          <XAxis
            dataKey="timestamp"
            tickFormatter={fmtTs}
            tick={TICK}
            {...AXIS}
            interval={xInterval(points.length)}
          />
          <YAxis
            tick={TICK}
            {...AXIS}
            width={52}
            domain={[0, (max: number) => yMax(max)]}
            tickFormatter={(v) => String(v)}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(v: any, n: any) => [`${Math.round(Number(v ?? 0))} kW`, n]}
            labelFormatter={(l) => fmtTs(String(l))}
          />
          <Line
            dataKey="original_grid_import_kw"
            name="Original"
            stroke={C.muted}
            strokeWidth={2}
            strokeDasharray="8 6"
            dot={false}
          />
          <Line
            dataKey="optimized_grid_import_kw"
            name="Optimized"
            stroke={accent.hex}
            strokeWidth={3}
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function SocChart({ points }: { points: EnergyPoint[] }) {
  return (
    <SmallCard title="Battery SoC (%)" subtitle="Reserve-aware state of charge">
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={points} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={C.grid} strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="timestamp"
            tickFormatter={fmtTs}
            tick={TICK}
            {...AXIS}
            interval={xInterval(points.length)}
          />
          <YAxis tick={TICK} {...AXIS} width={40} domain={[0, 100]} tickCount={5} />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(v: any) => [`${Math.round(Number(v ?? 0))}%`, "SoC"]}
            labelFormatter={(l) => fmtTs(String(l))}
          />
          <Area
            dataKey="battery_soc_percent"
            name="SoC"
            fill="rgba(78,222,163,0.15)"
            stroke={C.primary}
            strokeWidth={2.5}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </SmallCard>
  );
}

export function DispatchChart({ points }: { points: EnergyPoint[] }) {
  return (
    <SmallCard title="Battery dispatch (kW)" subtitle="Positive charge, negative discharge">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={points} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={C.grid} strokeDasharray="4 4" vertical={false} />
          <ReferenceLine y={0} stroke={C.muted} strokeWidth={1.5} opacity={0.65} />
          <XAxis
            dataKey="timestamp"
            tickFormatter={fmtTs}
            tick={TICK}
            {...AXIS}
            interval={xInterval(points.length)}
          />
          <YAxis tick={TICK} {...AXIS} width={40} />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
             
            labelStyle={{ color: "#dae2fd" }}
            itemStyle={{ color: "#dae2fd" }}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(v: any) => [`${Math.round(Number(v ?? 0))} kW`, "Dispatch"]}
            labelFormatter={(l) => fmtTs(String(l))}
          />
          <Bar dataKey="battery_power_kw" name="Dispatch" radius={[4, 4, 0, 0]}>
            {points.map((p, i) => (
              <Cell key={i} fill={p.battery_power_kw >= 0 ? C.tertiary : C.primary} opacity={0.88} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </SmallCard>
  );
}

export function ShiftChart({ points }: { points: EnergyPoint[] }) {
  return (
    <SmallCard title="Flexible load shifted (kW)" subtitle="Curtailment and rescheduling events">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={points} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={C.grid} strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="timestamp"
            tickFormatter={fmtTs}
            tick={TICK}
            {...AXIS}
            interval={xInterval(points.length)}
          />
          <YAxis tick={TICK} {...AXIS} width={40} />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter={(v: any) => [`${Math.round(Number(v ?? 0))} kW`, "Shifted load"]}
            labelFormatter={(l) => fmtTs(String(l))}
          />
          <Bar dataKey="shifted_load_kw" name="Shifted" fill={C.tertiary} opacity={0.88} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </SmallCard>
  );
}

function Card({
  title,
  subtitle,
  legend,
  children,
}: {
  title: string;
  subtitle: string;
  legend: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-outline bg-surface px-4 py-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-display text-lg font-semibold text-foreground">{title}</p>
          <p className="mt-1 text-sm text-muted">{subtitle}</p>
        </div>
        <div className="flex flex-wrap gap-3 text-[11px] text-muted">{legend}</div>
      </div>
      {children}
    </div>
  );
}

function SmallCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-outline bg-surface px-4 py-4">
      <p className="font-display text-lg font-semibold text-foreground">{title}</p>
      <p className="mt-1 text-sm text-muted">{subtitle}</p>
      <div className="mt-4">{children}</div>
    </div>
  );
}

function Dot({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
      <span>{label}</span>
    </div>
  );
}
