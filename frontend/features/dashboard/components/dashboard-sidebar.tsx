import type { NavItem } from "@/features/dashboard/types";

export function DashboardSidebar({
  navItems,
  rateLabel,
}: {
  navItems: NavItem[];
  rateLabel: string;
}) {
  return (
    <aside className="panel-shadow fixed inset-y-0 left-0 hidden w-64 border-r border-outline bg-surface-2/95 px-5 py-7 backdrop-blur md:flex md:flex-col">
      <div className="border-b border-outline pb-6">
        <p className="font-label text-[11px] text-muted">GridWise</p>
        <h1 className="font-display mt-3 text-2xl font-semibold text-primary">
          Demand Control
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted">
          Weekday MV TOU site.
        </p>
      </div>

      <nav className="mt-8 flex flex-1 flex-col gap-2">
        {navItems.map((item) => (
          <a
            key={item.href}
            className="group flex items-center gap-3 rounded-lg border border-transparent px-3 py-3 text-sm text-muted transition hover:border-outline hover:bg-surface-3 hover:text-foreground"
            href={item.href}
          >
            <span className="h-2 w-2 rounded-full bg-muted transition group-hover:bg-primary" />
            <span className="font-label text-[11px]">{item.label}</span>
          </a>
        ))}
      </nav>

      <div className="space-y-3 border-t border-outline pt-5 text-xs text-muted">
        <div className="rounded-lg border border-outline bg-surface px-3 py-3">
          <p className="font-label text-[10px] text-primary">Active tariff</p>
          <p className="mt-2 text-sm text-foreground">{rateLabel}</p>
        </div>
        <div className="rounded-lg border border-outline bg-surface px-3 py-3">
          <p className="font-label text-[10px] text-secondary">Preferred strategy</p>
          <p className="mt-2 text-sm text-foreground">Battery + Load Shifting</p>
        </div>
      </div>
    </aside>
  );
}
