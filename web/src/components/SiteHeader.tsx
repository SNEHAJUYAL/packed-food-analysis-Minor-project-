"use client";

import Link from "next/link";
import { useState } from "react";
import { BrandMark } from "./Brand";
import { IconClose, IconMenu } from "./icons";
import { buttonClass } from "./ui";

const NAV = [
  { href: "/#how-it-works", label: "How it works" },
  { href: "/products", label: "Explore products" },
  { href: "/compare", label: "Compare" },
  { href: "/methodology", label: "Methodology" },
];

/** Top bar for the public landing page; app pages use the sidebar in AppShell. */
export function SiteHeader() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 border-b border-line/70 bg-ivory/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-10">
        <Link href="/" aria-label="Food Intelligence home" onClick={() => setOpen(false)}>
          <BrandMark />
        </Link>
        <nav aria-label="Main" className="hidden md:block">
          <ul className="flex items-center gap-1">
            {NAV.map((n) => (
              <li key={n.href}>
                <Link href={n.href} className="rounded-lg px-3 py-2 text-sm text-slate-700 transition hover:bg-white hover:text-ink">
                  {n.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <div className="hidden items-center gap-2 md:flex">
          <Link href="/dashboard" className={buttonClass.ghost}>Dashboard</Link>
          <Link href="/analyze" className={`${buttonClass.primary} !py-2.5`}>Analyze a product</Link>
        </div>
        <button
          type="button"
          className="flex h-11 w-11 items-center justify-center rounded-xl border border-line bg-white text-ink md:hidden"
          aria-expanded={open}
          aria-controls="mobile-nav"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((o) => !o)}
        >
          {open ? <IconClose /> : <IconMenu />}
        </button>
      </div>
      {open ? (
        <nav id="mobile-nav" aria-label="Main (mobile)" className="border-t border-line bg-white md:hidden">
          <ul className="mx-auto max-w-7xl space-y-1 px-4 py-3">
            {[...NAV, { href: "/dashboard", label: "Dashboard" }, { href: "/analyze", label: "Analyze a product" }].map((n) => (
              <li key={n.href}>
                <Link href={n.href} onClick={() => setOpen(false)} className="block rounded-xl px-3 py-3 text-sm text-slate-700 hover:bg-brand-50">
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
