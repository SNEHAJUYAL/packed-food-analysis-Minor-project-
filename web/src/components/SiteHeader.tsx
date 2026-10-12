"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV = [
  { href: "/", label: "Analyse" },
  { href: "/products", label: "Products" },
  { href: "/compare", label: "Compare" },
  { href: "/methodology", label: "Methodology" },
];

export function SiteHeader() {
  const pathname = usePathname() ?? "/";
  const [open, setOpen] = useState(false);
  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <Link href="/" className="flex items-center gap-2" onClick={() => setOpen(false)}>
          <span aria-hidden="true" className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-sm font-bold text-white">
            FD
          </span>
          <span className="leading-tight">
            <span className="block text-sm font-semibold text-ink">Food Decision Intelligence</span>
            <span className="hidden text-xs text-muted sm:block">Understand. Evaluate. Compare. Decide.</span>
          </span>
        </Link>
        <nav aria-label="Main" className="hidden md:block">
          <ul className="flex items-center gap-1">
            {NAV.map((n) => (
              <li key={n.href}>
                <Link
                  href={n.href}
                  aria-current={isActive(n.href) ? "page" : undefined}
                  className={`rounded-lg px-3 py-2 text-sm ${isActive(n.href) ? "bg-brand-50 font-medium text-brand-700" : "text-slate-600 hover:bg-slate-100"}`}
                >
                  {n.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <button
          type="button"
          className="rounded-lg border border-line px-3 py-1.5 text-sm text-slate-700 md:hidden"
          aria-expanded={open}
          aria-controls="mobile-nav"
          onClick={() => setOpen((o) => !o)}
        >
          Menu
        </button>
      </div>
      {open ? (
        <nav id="mobile-nav" aria-label="Main (mobile)" className="border-t border-line bg-white md:hidden">
          <ul className="mx-auto max-w-6xl px-4 py-2">
            {NAV.map((n) => (
              <li key={n.href}>
                <Link
                  href={n.href}
                  onClick={() => setOpen(false)}
                  aria-current={isActive(n.href) ? "page" : undefined}
                  className={`block rounded-lg px-3 py-2 text-sm ${isActive(n.href) ? "bg-brand-50 font-medium text-brand-700" : "text-slate-700"}`}
                >
                  {n.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}
    </header>
  );
}
