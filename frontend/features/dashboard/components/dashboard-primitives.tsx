import { CARD_STYLES } from "@/features/dashboard/theme";

type CardTone = "primary" | "secondary" | "tertiary" | "danger";

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
