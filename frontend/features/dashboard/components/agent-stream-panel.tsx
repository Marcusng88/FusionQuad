"use client";

import { useEffect, useRef, useState } from "react";
import type { AgentStreamEntry, DayTab } from "../types";

function groupStreamsByTick(streams: AgentStreamEntry[]): AgentStreamEntry[][] {
  const ticks: AgentStreamEntry[][] = [];
  let current: AgentStreamEntry[] = [];

  for (const entry of streams) {
    if (entry.node === "planner" && current.some((e) => e.node === "planner")) {
      ticks.push(current);
      current = [];
    }
    current.push(entry);
  }
  if (current.length > 0) ticks.push(current);
  return ticks;
}

function extractJson(text: string): Record<string, unknown> | null {
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start < 0 || end <= start) return null;
  try {
    return JSON.parse(text.slice(start, end + 1));
  } catch {
    return null;
  }
}

function agentBadgeCls(node: string): string {
  if (node === "planner") return "border-primary/35 bg-primary/10 text-primary";
  if (node === "auditor") return "border-danger/35 bg-danger/10 text-danger";
  return "border-outline bg-surface text-foreground";
}

function agentLabel(node: string): string {
  if (node === "planner") return "Planner";
  if (node === "controller") return "Controller";
  if (node === "auditor") return "Auditor";
  return node;
}

function ActionBadge({ action }: { action?: string }) {
  if (!action) return <span className="text-[10px] text-muted">—</span>;
  const a = action.toUpperCase();
  const cls =
    a === "DISCHARGE"
      ? "border-primary/40 bg-primary/15 text-primary"
      : a === "CHARGE"
        ? "border-secondary/40 bg-secondary/15 text-secondary"
        : "border-outline bg-surface-3 text-muted";
  return (
    <span className={`rounded border px-2 py-0.5 text-[10px] font-semibold ${cls}`}>{a}</span>
  );
}

function ConfBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const bar =
    value >= 0.7 ? "bg-primary" : value >= 0.4 ? "bg-tertiary" : "bg-danger";
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-muted flex-shrink-0">Conf</span>
      <div className="flex-1 h-1 rounded-full bg-outline overflow-hidden">
        <div className={`h-full rounded-full ${bar}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-muted font-mono flex-shrink-0">{value.toFixed(2)}</span>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-[10px] text-muted">{label}</span>
      <span className="text-[10px] text-foreground font-mono truncate max-w-[150px] text-right">{value}</span>
    </div>
  );
}

function AgentCard({
  entry,
  onDetails,
}: {
  entry: AgentStreamEntry;
  onDetails: () => void;
}) {
  const data = extractJson(entry.tokens) ?? {};

  let body: React.ReactNode;
  if (entry.isStreaming) {
    body = (
      <div className="flex items-center gap-2 py-1">
        <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
        <span className="text-[10px] text-muted">thinking…</span>
      </div>
    );
  } else if (entry.node === "planner") {
    const d = data as { strategy_name?: string; shave_kw?: number; reserve_soc_pct?: number; target_soc_end?: number; confidence?: number };
    const reservePct = d.reserve_soc_pct != null ? `${(d.reserve_soc_pct * 100).toFixed(0)}%` : "—";
    const targetPct = d.target_soc_end != null ? `${(d.target_soc_end * 100).toFixed(0)}%` : "—";
    body = (
      <div className="space-y-1.5">
        <Row label="Strategy" value={String(d.strategy_name ?? "—")} />
        <Row label="Shave" value={d.shave_kw != null ? `${d.shave_kw} kW` : "—"} />
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-muted">Action</span>
          <span className="rounded border border-primary/35 bg-primary/10 text-primary px-2 py-0.5 text-[10px] font-semibold">
            Reserve {reservePct} → Target {targetPct}
          </span>
        </div>
        {d.confidence != null && <ConfBar value={Number(d.confidence)} />}
      </div>
    );
  } else if (entry.node === "controller") {
    const d = data as {
      action?: string;
      charge_kw?: number;
      discharge_kw?: number;
      previous_soc?: number;
      current_soc?: number;
      duration_min?: number;
      baseline_load?: number;
      actual_load?: number;
    };
    const kw = d.charge_kw ?? d.discharge_kw ?? 0;
    const socBefore = d.previous_soc != null ? `${(d.previous_soc * 100).toFixed(0)}%` : "—";
    const socAfter = d.current_soc != null ? `${(d.current_soc * 100).toFixed(0)}%` : "—";
    body = (
      <div className="space-y-1.5">
        <ActionBadge action={d.action} />
        <Row label="Power" value={`${kw} kW`} />
        <Row label="SoC" value={`${socBefore} → ${socAfter}`} />
        {d.duration_min != null && <Row label="Duration" value={`${d.duration_min} min`} />}
        {d.baseline_load != null && <Row label="Baseline" value={`${d.baseline_load.toFixed(1)} kW`} />}
        {d.actual_load != null && <Row label="Actual" value={`${d.actual_load.toFixed(1)} kW`} />}
      </div>
    );
  } else if (entry.node === "auditor") {
    const d = data as { confidence?: number; recommendation?: string; delta_score?: number; interval_savings_rm?: number; shave_kw?: number };
    const summary = entry.traceEntry?.decision ?? "";
    body = (
      <div className="space-y-1.5">
        {summary && <p className="text-[10px] text-foreground/80 leading-snug line-clamp-2">{summary}</p>}
        {d.delta_score != null && <Row label="Score" value={`${d.delta_score.toFixed(0)} / 100`} />}
        {d.shave_kw != null && <Row label="Shave" value={`${d.shave_kw.toFixed(1)} kW`} />}
        {d.interval_savings_rm != null && <Row label="Savings" value={`RM ${d.interval_savings_rm.toFixed(3)}`} />}
        {d.recommendation && <p className="text-[10px] text-muted leading-snug line-clamp-2 italic">{d.recommendation}</p>}
        {d.confidence != null && <ConfBar value={Number(d.confidence)} />}
      </div>
    );
  } else {
    body = (
      <p className="text-[10px] text-muted line-clamp-2">{entry.tokens.slice(0, 80) || "—"}</p>
    );
  }

  return (
    <div className="rounded-xl border border-outline bg-surface p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className={`rounded border px-2 py-0.5 text-[10px] font-medium ${agentBadgeCls(entry.node)}`}>
          {agentLabel(entry.node)}
        </span>
        <span className="text-[9px] text-muted font-mono">{entry.timestamp}</span>
      </div>
      {body}
      {!entry.isStreaming && (
        <button
          type="button"
          onClick={onDetails}
          className="w-full rounded-lg border border-outline bg-surface-2 py-1 text-[10px] text-muted hover:text-foreground hover:bg-surface-3 transition"
        >
          Details →
        </button>
      )}
    </div>
  );
}

function DetailsModal({
  entry,
  onClose,
}: {
  entry: AgentStreamEntry;
  onClose: () => void;
}) {
  const data = extractJson(entry.tokens) ?? {};

  let fields: { label: string; value: string }[] = [];
  const longText: { title: string; content: string }[] = [];

  if (entry.node === "planner") {
    const d = data as {
      strategy_name?: string;
      shave_kw?: number;
      reserve_soc_pct?: number;
      target_soc_end?: number;
      md_limit_kw?: number;
      confidence?: number;
      rationale?: string;
      constraints?: string[];
    };
    fields = [
      { label: "Strategy", value: String(d.strategy_name ?? "—") },
      { label: "Shave", value: d.shave_kw != null ? `${d.shave_kw} kW` : "—" },
      { label: "MD Limit", value: d.md_limit_kw != null ? `${d.md_limit_kw} kW` : "—" },
      {
        label: "Reserve SOC",
        value: d.reserve_soc_pct != null ? `${(d.reserve_soc_pct * 100).toFixed(0)}%` : "—",
      },
      {
        label: "Target SOC",
        value: d.target_soc_end != null ? `${(d.target_soc_end * 100).toFixed(0)}%` : "—",
      },
      { label: "Confidence", value: d.confidence != null ? d.confidence.toFixed(2) : "—" },
    ];
    if (d.rationale) longText.push({ title: "Rationale", content: d.rationale });
    if (d.constraints?.length)
      longText.push({ title: "Constraints", content: d.constraints.join("\n") });
  } else if (entry.node === "controller") {
    const d = data as {
      action?: string;
      charge_kw?: number;
      discharge_kw?: number;
      duration_min?: number;
      previous_soc?: number;
      current_soc?: number;
      baseline_load?: number;
      actual_load?: number;
    };
    fields = [
      { label: "Action", value: String(d.action ?? "—").toUpperCase() },
      { label: "Charge kW", value: d.charge_kw != null ? `${d.charge_kw} kW` : "—" },
      { label: "Discharge kW", value: d.discharge_kw != null ? `${d.discharge_kw} kW` : "—" },
      { label: "Duration", value: d.duration_min != null ? `${d.duration_min} min` : "—" },
      { label: "SoC Before", value: d.previous_soc != null ? `${(d.previous_soc * 100).toFixed(0)}%` : "—" },
      { label: "SoC After", value: d.current_soc != null ? `${(d.current_soc * 100).toFixed(0)}%` : "—" },
      { label: "Baseline Load", value: d.baseline_load != null ? `${d.baseline_load.toFixed(1)} kW` : "—" },
      { label: "Actual Load", value: d.actual_load != null ? `${d.actual_load.toFixed(1)} kW` : "—" },
    ];
  } else if (entry.node === "auditor") {
    const d = data as { reasoning?: string; recommendation?: string; confidence?: number; delta_score?: number; interval_savings_rm?: number; shave_kw?: number };
    fields = [
      { label: "Score", value: d.delta_score != null ? `${d.delta_score.toFixed(0)} / 100` : "—" },
      { label: "Shave", value: d.shave_kw != null ? `${d.shave_kw.toFixed(1)} kW` : "—" },
      { label: "Savings", value: d.interval_savings_rm != null ? `RM ${d.interval_savings_rm.toFixed(3)}` : "—" },
      { label: "Confidence", value: d.confidence != null ? d.confidence.toFixed(2) : "—" },
    ];
    const reasoning = d.reasoning ?? entry.traceEntry?.reason ?? "";
    const recommendation = d.recommendation ?? entry.traceEntry?.action ?? "";
    if (reasoning) longText.push({ title: "Reasoning", content: reasoning });
    if (recommendation) longText.push({ title: "Recommendation", content: recommendation });
  }

  const hasContent = fields.length > 0 || longText.length > 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm max-h-[80vh] flex flex-col rounded-2xl border border-outline bg-surface-2 shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-outline flex-shrink-0">
          <div className="flex items-center gap-2">
            <span className={`rounded border px-2 py-0.5 text-xs font-medium ${agentBadgeCls(entry.node)}`}>
              {agentLabel(entry.node)}
            </span>
            <span className="text-xs text-muted font-mono">{entry.timestamp}</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-muted hover:text-foreground text-sm transition"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto panel-scroll p-4 space-y-4">
          {fields.length > 0 && (
            <div className="space-y-2">
              {fields.map((f) => (
                <div key={f.label} className="flex items-start justify-between gap-3">
                  <span className="text-sm text-muted flex-shrink-0">{f.label}</span>
                  <span className="text-sm text-foreground font-mono text-right">{f.value}</span>
                </div>
              ))}
            </div>
          )}

          {longText.map((lt) => (
            <div key={lt.title}>
              <p className="font-label text-xs text-muted mb-1.5">{lt.title}</p>
              <div className="rounded-lg border border-outline bg-surface px-3 py-2.5">
                <p className="text-sm text-foreground/90 leading-relaxed whitespace-pre-wrap">
                  {lt.content}
                </p>
              </div>
            </div>
          ))}

          {!hasContent && (
            <p className="text-sm text-muted leading-relaxed whitespace-pre-wrap">
              {entry.tokens || "No data."}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export function DayTabBar({
  tabs,
  activeTabId,
  onSelect,
  onClose,
  onTogglePin,
}: {
  tabs: DayTab[];
  activeTabId: string | null;
  onSelect: (id: string) => void;
  onClose: (id: string) => void;
  onTogglePin: (id: string) => void;
}) {
  if (tabs.length === 0) return null;

  return (
    <div className="flex gap-1.5 overflow-x-auto pb-1 panel-scroll">
      {tabs.map((tab) => {
        const isActive = tab.id === activeTabId;
        return (
          <div
            key={tab.id}
            className={`flex-shrink-0 flex items-center gap-1 rounded-lg border px-2.5 py-1 text-[10px] cursor-pointer transition select-none ${
              isActive
                ? "border-primary/40 bg-primary/10 text-primary"
                : "border-outline bg-surface text-muted hover:text-foreground hover:bg-surface-3"
            }`}
            onClick={() => onSelect(tab.id)}
          >
            <span className="max-w-[110px] truncate">{tab.label}</span>
            <button
              type="button"
              title={tab.pinned ? "Unpin" : "Pin"}
              className="ml-0.5 opacity-60 hover:opacity-100 transition"
              onClick={(e) => {
                e.stopPropagation();
                onTogglePin(tab.id);
              }}
            >
              {tab.pinned ? "📌" : "·"}
            </button>
            {!tab.pinned && (
              <button
                type="button"
                title="Close"
                className="opacity-40 hover:opacity-100 transition text-[9px]"
                onClick={(e) => {
                  e.stopPropagation();
                  onClose(tab.id);
                }}
              >
                ✕
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function AgentStreamFeed({ streams }: { streams: AgentStreamEntry[] }) {
  const ticks = groupStreamsByTick(streams);
  const [tickIdx, setTickIdx] = useState(0);
  const [popup, setPopup] = useState<AgentStreamEntry | null>(null);
  const prevTickCount = useRef(0);

  useEffect(() => {
    if (ticks.length > prevTickCount.current) {
      setTickIdx(ticks.length - 1);
      prevTickCount.current = ticks.length;
    }
  }, [ticks.length]);

  if (ticks.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-[11px] text-muted text-center px-4">
          Run optimization to see live agent reasoning.
        </p>
      </div>
    );
  }

  const tick = ticks[tickIdx] ?? [];
  const planner = tick.find((e) => e.node === "planner");
  const controller = tick.find((e) => e.node === "controller");
  const auditor = tick.find((e) => e.node === "auditor");
  const tickTime = tick[0]?.timestamp ?? "";

  return (
    <>
      <div className="flex items-center justify-between mb-3 px-0.5">
        <button
          type="button"
          onClick={() => setTickIdx((i) => Math.max(0, i - 1))}
          disabled={tickIdx === 0}
          className="rounded-lg border border-outline px-2 py-1 text-[10px] text-muted hover:text-foreground disabled:opacity-30 transition"
        >
          ◀
        </button>
        <div className="text-center">
          <p className="text-[11px] text-foreground font-mono">
            Tick {tickIdx + 1} / {ticks.length}
          </p>
          {tickTime && <p className="text-[9px] text-muted">{tickTime}</p>}
        </div>
        <button
          type="button"
          onClick={() => setTickIdx((i) => Math.min(ticks.length - 1, i + 1))}
          disabled={tickIdx === ticks.length - 1}
          className="rounded-lg border border-outline px-2 py-1 text-[10px] text-muted hover:text-foreground disabled:opacity-30 transition"
        >
          ▶
        </button>
      </div>

      <div className="space-y-2">
        {planner && <AgentCard entry={planner} onDetails={() => setPopup(planner)} />}
        {controller && <AgentCard entry={controller} onDetails={() => setPopup(controller)} />}
        {auditor && <AgentCard entry={auditor} onDetails={() => setPopup(auditor)} />}
      </div>

      {popup && <DetailsModal entry={popup} onClose={() => setPopup(null)} />}
    </>
  );
}
