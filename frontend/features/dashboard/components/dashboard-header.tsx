import { Badge } from "@/features/dashboard/components/dashboard-primitives";
import type { NavItem } from "@/features/dashboard/types";

export function DashboardHeader({
  demandLimitKw,
  peakWindow,
  navItems,
}: {
  demandLimitKw: number;
  peakWindow: string;
  navItems: NavItem[];
}) {
  return (
    <header className="sticky top-0 z-30 border-b border-outline bg-background/88 backdrop-blur">
      <div className="mx-auto max-w-[1440px] px-4 py-4 sm:px-6 xl:px-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="font-label text-[10px] text-primary">Operations</p>
            <h2 className="font-display mt-1 text-xl font-semibold text-foreground sm:text-2xl">
              Peak Shaving Dashboard
            </h2>
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2">
            <Badge tone="secondary">Sample site loaded</Badge>
            <Badge tone="primary">Demand limit {demandLimitKw} kW</Badge>
            <Badge tone="tertiary">Peak {peakWindow}</Badge>
          </div>
        </div>

        <nav className="mt-4 flex gap-2 overflow-x-auto pb-1 md:hidden">
          {navItems.map((item) => (
            <a
              key={item.href}
              className="whitespace-nowrap rounded-full border border-outline bg-surface px-4 py-2 text-sm text-muted transition hover:bg-surface-3 hover:text-foreground"
              href={item.href}
            >
              {item.label}
            </a>
          ))}
        </nav>
      </div>
    </header>
  );
}
