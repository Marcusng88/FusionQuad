import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "GridWise",
  description: "Peak shaving dashboard.",
};

const navItems = [
  { href: "/", label: "Overview" },
  { href: "/baseline", label: "Baseline" },
  { href: "/simulation", label: "Simulation" },
  { href: "/decisions", label: "AI Decisions" },
  { href: "/scenarios", label: "Scenarios" },
  { href: "/setup", label: "Setup" },
];

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full">
        <div className="flex min-h-screen">
          <aside className="panel-shadow fixed inset-y-0 left-0 hidden w-64 border-r border-outline bg-surface-2/95 px-5 py-7 backdrop-blur md:flex md:flex-col lg:w-72">
            <div className="border-b border-outline pb-6">
              <p className="font-label text-[11px] text-muted">GridWise</p>
              <h1 className="font-display mt-3 text-2xl font-semibold text-primary lg:text-3xl">
                Demand Control
              </h1>
              <p className="mt-2 text-sm leading-6 text-muted">
                Weekday MV TOU site.
              </p>
            </div>

            <nav className="mt-8 flex flex-1 flex-col gap-2">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="group flex items-center gap-3 rounded-lg border border-transparent px-3 py-3 text-sm text-muted transition hover:border-outline hover:bg-surface-3 hover:text-foreground"
                >
                  <span className="h-2 w-2 rounded-full bg-muted transition group-hover:bg-primary" />
                  <span className="font-label text-[11px]">{item.label}</span>
                </Link>
              ))}
            </nav>

            <div className="space-y-3 border-t border-outline pt-5 text-xs text-muted">
              <div className="rounded-lg border border-outline bg-surface px-3 py-3">
                <p className="font-label text-[10px] text-primary">Active tariff</p>
                <p className="mt-2 text-sm text-foreground">MV TOU / RM97.06 per kW</p>
              </div>
              <div className="rounded-lg border border-outline bg-surface px-3 py-3">
                <p className="font-label text-[10px] text-secondary">Preferred strategy</p>
                <p className="mt-2 text-sm text-foreground">Battery + Load Shifting</p>
              </div>
            </div>
          </aside>

          <div className="flex-1 md:ml-64 lg:ml-72">
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
                    <span className="rounded-full border border-secondary/35 bg-secondary/10 px-3 py-1 text-[11px] text-secondary">
                      Sample site loaded
                    </span>
                    <span className="rounded-full border border-primary/35 bg-primary/10 px-3 py-1 text-[11px] text-primary">
                      Demand limit 800 kW
                    </span>
                    <span className="rounded-full border border-tertiary/35 bg-tertiary/10 px-3 py-1 text-[11px] text-tertiary">
                      Peak 14:00 to 22:00
                    </span>
                  </div>
                </div>

                <nav className="mt-4 flex gap-2 overflow-x-auto pb-1 md:hidden">
                  {navItems.map((item) => (
                    <Link
                      key={item.href}
                      href={item.href}
                      className="whitespace-nowrap rounded-full border border-outline bg-surface px-4 py-2 text-sm text-muted transition hover:bg-surface-3 hover:text-foreground"
                    >
                      {item.label}
                    </Link>
                  ))}
                </nav>
              </div>
            </header>

            <main className="mx-auto max-w-[1440px] px-4 py-6 sm:px-6 xl:px-8">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
