"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const navItems = [
  { href: "/", label: "Overview" },
  { href: "/baseline", label: "Baseline" },
  { href: "/simulation", label: "Simulation" },
  { href: "/decisions", label: "AI Decisions" },
  { href: "/scenarios", label: "Scenarios" },
  { href: "/setup", label: "Setup" },
];

export function HeaderNav() {
  const pathname = usePathname();

  return (
    <nav className="flex items-center gap-0.5 overflow-x-auto">
      {navItems.map((item) => {
        const isActive =
          item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`whitespace-nowrap rounded-lg px-3 py-1.5 font-label text-[11px] transition-colors ${
              isActive
                ? "bg-primary/10 text-primary ring-1 ring-primary/20"
                : "text-muted hover:bg-surface-3 hover:text-foreground"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    const saved = localStorage.getItem("fusionquad-theme") as
      | "dark"
      | "light"
      | null;
    const initial = saved ?? "dark";
    setTheme(initial);
    document.documentElement.setAttribute("data-theme", initial);
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("fusionquad-theme", next);
  }

  return (
    <button
      onClick={toggle}
      type="button"
      title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
      className="flex h-8 w-8 items-center justify-center rounded-lg border border-outline bg-surface text-muted transition hover:border-primary/40 hover:bg-surface-3 hover:text-primary"
    >
      <span className="text-sm leading-none">{theme === "dark" ? "☀" : "☾"}</span>
    </button>
  );
}
