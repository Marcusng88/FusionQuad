import type { Metadata } from "next";
import Script from "next/script";
import { HeaderNav, ThemeToggle } from "./components/nav-client";
import "./globals.css";

export const metadata: Metadata = {
  title: "FusionQuad — Peak Shaving",
  description: "Agentic AI energy management dashboard.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased" suppressHydrationWarning>
      <head>
        <Script
          id="theme-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('fusionquad-theme');document.documentElement.setAttribute('data-theme',t||'dark');}catch(e){}})();`,
          }}
        />
      </head>
      <body className="min-h-full">
        <header
          className="sticky top-0 z-30 border-b border-outline bg-background/90 backdrop-blur"
          style={{ height: "var(--header-h)" }}
        >
          <div className="mx-auto flex h-full max-w-[1440px] items-center gap-4 px-4 sm:px-6 xl:px-8">
            {/* Brand */}
            <div className="shrink-0 border-r border-outline pr-4">
              <p className="font-label text-[9px] text-muted">FusionQuad</p>
              <p className="font-display text-base font-semibold text-primary leading-tight">
                Demand Control
              </p>
            </div>

            {/* Page nav */}
            <HeaderNav />

            {/* Right: status chips + theme toggle */}
            <div className="ml-auto flex shrink-0 items-center gap-2">
              <div className="hidden items-center gap-2 sm:flex">
                <span className="rounded-full border border-primary/35 bg-primary/10 px-2.5 py-1 text-[10px] text-primary">
                  800 kW limit
                </span>
                <span className="rounded-full border border-tertiary/35 bg-tertiary/10 px-2.5 py-1 text-[10px] text-tertiary">
                  14:00–22:00 peak
                </span>
                <span className="rounded-full border border-secondary/35 bg-secondary/10 px-2.5 py-1 text-[10px] text-secondary">
                  RM 97.06/kW
                </span>
              </div>
              <ThemeToggle />
            </div>
          </div>
        </header>

        <main>
          {children}
        </main>
      </body>
    </html>
  );
}
