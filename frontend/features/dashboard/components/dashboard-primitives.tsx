import type { ReactNode } from "react";

import { formatCurrencyValue } from "@/features/dashboard/lib/formatters";
import { AGENT_STYLES, CARD_STYLES } from "@/features/dashboard/theme";
import type { DecisionLog } from "@/features/dashboard/types";

type CardTone = "primary" | "secondary" | "tertiary" | "danger";
type AccentTone = "primary" | "secondary" | "tertiary";

export function Panel({
  eyebrow,
  title,
  subtitle,
  children,
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  return (
    <div className="panel-shadow rounded-3xl border border-outline bg-surface-2 p-6 sm:p-7">
      <div className="mb-6">
        <p className="font-label text-[10px] text-primary">{eyebrow}</p>
        <h3 className="font-display mt-3 text-2xl font-semibold text-foreground">{title}</h3>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">{subtitle}</p>
      </div>
      {children}
    </div>
  );
}

export function KpiCard({
  title,
  value,
  detail,
  tone,
  prefix,
  suffix,
}: {
  title: string;
  value: string;
  detail: string;
  tone: CardTone;
  prefix?: string;
  suffix?: string;
}) {
  const styles = CARD_STYLES[tone];

  return (
    <div className={`panel-noise rounded-2xl border ${styles.border} ${styles.bg} px-5 py-5`}>
      <div className={`h-1 w-16 rounded-full ${styles.bar}`} />
      <p className="font-label mt-4 text-[10px] text-muted">{title}</p>
      <div className="mt-4 flex items-end gap-2">
        {prefix ? <span className="text-sm text-muted">{prefix}</span> : null}
        <p className="font-display text-4xl font-semibold text-foreground">{value}</p>
        {suffix ? <span className="pb-1 text-sm text-muted">{suffix}</span> : null}
      </div>
      <p className="mt-3 text-sm leading-6 text-muted">{detail}</p>
    </div>
  );
}

export function QuickMetric({
  label,
  value,
  note,
  tone,
}: {
  label: string;
  value: string;
  note: string;
  tone: "primary" | "secondary" | "danger";
}) {
  const styles = CARD_STYLES[tone];

  return (
    <div className={`rounded-2xl border ${styles.border} ${styles.bg} px-4 py-4`}>
      <p className="font-label text-[10px] text-muted">{label}</p>
      <p className="font-display mt-3 text-lg font-semibold text-foreground">{value}</p>
      <p className="mt-2 text-sm text-muted">{note}</p>
    </div>
  );
}

export function MiniStat({
  title,
  value,
  accent,
}: {
  title: string;
  value: string;
  accent: AccentTone;
}) {
  const colorClass =
    accent === "primary"
      ? "text-primary"
      : accent === "secondary"
        ? "text-secondary"
        : "text-tertiary";

  return (
    <div className="rounded-2xl border border-outline bg-surface px-4 py-4">
      <p className="font-label text-[10px] text-muted">{title}</p>
      <p className={`font-display mt-3 text-2xl font-semibold ${colorClass}`}>{value}</p>
    </div>
  );
}

export function RiskCard({
  title,
  value,
  note,
  tone,
}: {
  title: string;
  value: string;
  note: string;
  tone: "secondary" | "tertiary" | "danger";
}) {
  const styles = CARD_STYLES[tone];

  return (
    <div className={`rounded-2xl border ${styles.border} ${styles.bg} px-5 py-4`}>
      <p className="font-label text-[10px] text-muted">{title}</p>
      <p className="font-display mt-3 text-3xl font-semibold text-foreground">{value}</p>
      <p className="mt-3 text-sm leading-6 text-muted">{note}</p>
    </div>
  );
}

export function ConfigCard({
  title,
  accent,
  fields,
}: {
  title: string;
  accent: "primary" | "tertiary";
  fields: [string, string][];
}) {
  const colorClass = accent === "primary" ? "text-primary" : "text-tertiary";

  return (
    <div className="rounded-2xl border border-outline bg-surface px-5 py-5">
      <p className={`font-label text-[10px] ${colorClass}`}>{title}</p>
      <div className="mt-5 grid gap-3">
        {fields.map(([label, value]) => (
          <div key={label} className="rounded-xl border border-outline bg-surface-2 px-4 py-3">
            <p className="font-label text-[10px] text-muted">{label}</p>
            <p className="mt-2 text-sm text-foreground">{value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function FlowStep({
  index,
  title,
  body,
}: {
  index: string;
  title: string;
  body: string;
}) {
  return (
    <div className="rounded-2xl border border-outline bg-surface px-5 py-4">
      <div className="flex items-start gap-4">
        <div className="font-display flex h-12 w-12 items-center justify-center rounded-full border border-primary/35 bg-primary/10 text-sm font-semibold text-primary">
          {index}
        </div>
        <div>
          <h4 className="font-display text-lg font-semibold text-foreground">{title}</h4>
          <p className="mt-2 text-sm leading-7 text-muted">{body}</p>
        </div>
      </div>
    </div>
  );
}

export function TimelineItem({ log, index }: { log: DecisionLog; index: number }) {
  const tone = AGENT_STYLES[log.agent];

  return (
    <div className="relative rounded-2xl border border-outline bg-surface px-5 py-5">
      <div className="absolute left-6 top-6 h-[calc(100%-2.5rem)] w-px bg-outline" />
      <div className="relative flex gap-4">
        <div className={`mt-1 h-4 w-4 rounded-full border-4 ${tone.dot}`} />
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-3">
            <span className={`rounded-full border px-3 py-1 text-[11px] ${tone.badge}`}>
              {log.agent}
            </span>
            <span className="font-label text-[10px] text-muted">{log.timestamp}</span>
            <span className="font-label text-[10px] text-muted">
              Step {String(index + 1).padStart(2, "0")}
            </span>
          </div>
          <h4 className="font-display mt-3 text-lg font-semibold text-foreground">{log.decision}</h4>
          <p className="mt-2 text-sm leading-7 text-muted">{log.reason}</p>
          <div className="mt-4 rounded-xl border border-outline bg-surface-2 px-4 py-3 text-sm leading-7 text-foreground">
            {log.action}
          </div>
          {(log.expected_reduction_kw || log.estimated_saving_rm) && (
            <div className="mt-4 flex flex-wrap gap-2">
              {log.expected_reduction_kw ? (
                <Badge tone="secondary">Target shave {log.expected_reduction_kw} kW</Badge>
              ) : null}
              {log.estimated_saving_rm ? (
                <Badge tone="primary">
                  Savings RM{formatCurrencyValue(log.estimated_saving_rm)}
                </Badge>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function ReasonCard({
  label,
  title,
  copy,
  tone,
}: {
  label: string;
  title: string;
  copy: string;
  tone: AccentTone;
}) {
  const colorClass =
    tone === "primary" ? "text-primary" : tone === "secondary" ? "text-secondary" : "text-tertiary";

  return (
    <div className="rounded-2xl border border-outline bg-surface px-5 py-5">
      <p className={`font-label text-[10px] ${colorClass}`}>{label}</p>
      <h4 className="font-display mt-3 text-xl font-semibold text-foreground">{title}</h4>
      <p className="mt-3 text-sm leading-7 text-muted">{copy}</p>
    </div>
  );
}

export function Badge({
  children,
  tone,
}: {
  children: ReactNode;
  tone: AccentTone;
}) {
  const badgeClass =
    tone === "primary"
      ? "border-primary/35 bg-primary/10 text-primary"
      : tone === "secondary"
        ? "border-secondary/35 bg-secondary/10 text-secondary"
        : "border-tertiary/35 bg-tertiary/10 text-tertiary";

  return <span className={`rounded-full border px-3 py-1 text-[11px] ${badgeClass}`}>{children}</span>;
}
