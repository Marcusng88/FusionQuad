"use client";

import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import { AGENT_STYLES } from "../theme";
import type { AgentStreamEntry, DayTab, DecisionLog } from "../types";

const NODE_LABEL: Record<string, string> = {
  planner: "Planner Agent",
  controller: "Controller Agent",
  auditor: "Auditor Agent",
  forecast: "Forecasting Agent",
  tariff: "Tariff Agent",
};

function agentLabel(node: string): string {
  return NODE_LABEL[node] ?? node;
}

function agentStyle(node: string) {
  const label = agentLabel(node);
  return AGENT_STYLES[label as keyof typeof AGENT_STYLES] ?? AGENT_STYLES["Controller Agent"];
}

// ── Completed card — collapsible, markdown body ──────────────────────────────

function CompletedCard({ entry }: { entry: AgentStreamEntry }) {
  const [open, setOpen] = useState(false);
  const trace = entry.traceEntry;
  const style = agentStyle(entry.node);

  const summary = trace?.decision ?? entry.tokens?.split("\n")[0] ?? "Agent completed.";

  return (
    <div className="rounded-xl border border-outline bg-surface animate-in fade-in slide-in-from-bottom-1 duration-300">
      {/* Header row — always visible, click to toggle */}
      <button
        type="button"
        className="w-full flex items-center justify-between gap-2 px-3 py-2 text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className={`flex-shrink-0 rounded-md border px-2 py-0.5 text-[10px] font-medium ${style.badge}`}>
            {agentLabel(entry.node)}
          </span>
          <span className="text-[11px] text-foreground/80 truncate">{summary}</span>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <span className="text-[9px] text-muted font-mono">{entry.timestamp}</span>
          <span className="text-[9px] text-muted">{open ? "▲" : "▼"}</span>
        </div>
      </button>

      {/* Expanded body */}
      {open && (
        <div className="px-3 pb-3 space-y-2 border-t border-outline/60 pt-2">
          {trace ? (
            <>
              <p className="text-xs font-medium text-foreground leading-snug">{trace.decision}</p>
              <div className="text-[11px] text-muted leading-relaxed prose prose-sm prose-invert max-w-none">
                <Markdown>{trace.reason}</Markdown>
              </div>
              <div className="text-[11px] text-foreground/80 leading-relaxed prose prose-sm prose-invert max-w-none">
                <Markdown>{trace.action}</Markdown>
              </div>
              {(trace.expected_reduction_kw != null || trace.estimated_saving_rm != null) && (
                <div className="flex flex-wrap gap-1.5 pt-0.5">
                  {trace.expected_reduction_kw != null && (
                    <span className="rounded border border-primary/30 bg-primary/8 px-2 py-0.5 text-[10px] text-primary font-mono">
                      {trace.expected_reduction_kw.toFixed(1)} kW shaved
                    </span>
                  )}
                  {trace.estimated_saving_rm != null && (
                    <span className="rounded border border-tertiary/30 bg-tertiary/8 px-2 py-0.5 text-[10px] text-tertiary font-mono">
                      RM {trace.estimated_saving_rm.toFixed(4)} saved
                    </span>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="text-[11px] text-muted font-mono leading-relaxed whitespace-pre-wrap prose prose-sm prose-invert max-w-none">
              <Markdown>{entry.tokens || "Agent completed."}</Markdown>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Live streaming card ──────────────────────────────────────────────────────

function StreamingCard({ entry }: { entry: AgentStreamEntry }) {
  const style = agentStyle(entry.node);

  return (
    <div className="rounded-xl border border-outline bg-surface/60 p-3 space-y-2">
      <div className="flex items-center gap-2">
        <span className={`rounded-md border px-2 py-0.5 text-[10px] font-medium ${style.badge}`}>
          {agentLabel(entry.node)}
        </span>
        <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
        <span className="text-[10px] text-muted">thinking…</span>
      </div>
      <div className="text-[11px] text-foreground/80 font-mono leading-relaxed whitespace-pre-wrap break-words prose prose-sm prose-invert max-w-none">
        <Markdown>{entry.tokens || " "}</Markdown>
        <span className="inline-block w-0.5 h-3 bg-primary animate-pulse ml-0.5 align-middle" />
      </div>
    </div>
  );
}

// ── Tab bar ──────────────────────────────────────────────────────────────────

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
              onClick={(e) => { e.stopPropagation(); onTogglePin(tab.id); }}
            >
              {tab.pinned ? "📌" : "·"}
            </button>
            {!tab.pinned && (
              <button
                type="button"
                title="Close"
                className="opacity-40 hover:opacity-100 transition text-[9px]"
                onClick={(e) => { e.stopPropagation(); onClose(tab.id); }}
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

// ── Main stream feed ─────────────────────────────────────────────────────────

export function AgentStreamFeed({ streams }: { streams: AgentStreamEntry[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [streams.length, streams[streams.length - 1]?.tokens]);

  if (streams.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-[11px] text-muted text-center px-4">
          Run optimization to see live agent reasoning.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {streams.map((entry, i) =>
        entry.isStreaming ? (
          <StreamingCard key={`${entry.node}-${i}`} entry={entry} />
        ) : (
          <CompletedCard key={`${entry.node}-${i}`} entry={entry} />
        )
      )}
      <div ref={bottomRef} />
    </div>
  );
}
