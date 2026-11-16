"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, useSyncExternalStore, type ReactNode } from "react";
import {
  IconBook, IconChart, IconChevronLeft, IconChevronRight, IconClose, IconColumns, IconDashboard, IconGrid,
  IconLeaf, IconMenu, IconScan,
} from "./icons";
import { BrandMark } from "./Brand";
import { SiteFooter } from "./SiteFooter";
import { SiteHeader } from "./SiteHeader";
import { api } from "@/lib/api";

export const APP_NAV = [
  { href: "/dashboard", label: "Dashboard", icon: IconDashboard },
  { href: "/analyze", label: "Analyze Product", icon: IconScan },
  { href: "/products", label: "Product Explorer", icon: IconGrid },
  { href: "/compare", label: "Compare Products", icon: IconColumns },
  { href: "/alternatives", label: "Alternatives", icon: IconLeaf },
  { href: "/insights", label: "Insights & Analytics", icon: IconChart },
  { href: "/methodology", label: "Methodology", icon: IconBook },
] as const;

/** Which nav item a path belongs to. Alternatives pages live under /products/{id}/alternatives. */
export function activeNav(pathname: string): string | null {
  if (/^\/products\/[^/]+\/alternatives/.test(pathname)) return "/alternatives";
  const hit = APP_NAV.find((n) => pathname === n.href || pathname.startsWith(`${n.href}/`));
  return hit?.href ?? null;
}

/** Live API/database state from /api/health; says nothing it has not measured. */
function ServicePill({ compact }: { compact: boolean }) {
  const [state, setState] = useState<"checking" | "ok" | "db" | "down">("checking");
  useEffect(() => {
    const ctrl = new AbortController();
    api.health(ctrl.signal)
      .then((h) => setState(h.database === "ok" ? "ok" : "db"))
      .catch(() => { if (!ctrl.signal.aborted) setState("down"); });
    return () => ctrl.abort();
  }, []);
  const text = { checking: "Checking service…", ok: "API and database online", db: "Database unavailable", down: "API not reachable" }[state];
  const dot = { checking: "bg-slate-300", ok: "bg-[#6fbf8b]", db: "bg-warn", down: "bg-danger" }[state];
  return (
    <p className={`flex items-center gap-2 text-xs text-sage/80 ${compact ? "justify-center" : ""}`} title={text}>
      <span aria-hidden="true" className={`h-2 w-2 shrink-0 rounded-full ${dot}`} />
      <span className={compact ? "sr-only" : ""}>{text}</span>
    </p>
  );
}

function NavList({ pathname, compact, onNavigate }: { pathname: string; compact: boolean; onNavigate?: () => void }) {
  const active = activeNav(pathname);
  return (
    <ul className="space-y-1">
      {APP_NAV.map(({ href, label, icon: Icon }) => {
        const on = active === href;
        return (
          <li key={href}>
            <Link
              href={href}
              onClick={onNavigate}
              aria-current={on ? "page" : undefined}
              title={compact ? label : undefined}
              className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                compact ? "justify-center" : ""
              } ${on ? "bg-white/10 font-semibold text-white" : "text-sage/80 hover:bg-white/5 hover:text-white"}`}
            >
              <Icon className={`h-5 w-5 shrink-0 ${on ? "text-sage" : "text-sage/70 group-hover:text-sage"}`} />
              <span className={compact ? "sr-only" : ""}>{label}</span>
              {on && !compact ? <span aria-hidden="true" className="ml-auto h-1.5 w-1.5 rounded-full bg-sage" /> : null}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

const COLLAPSE_KEY = "fdi.sidebar.collapsed";

/** Sidebar collapse preference, per viewer, in localStorage (falls back to expanded). */
const collapseListeners = new Set<() => void>();
const collapseStore = {
  subscribe(cb: () => void) {
    collapseListeners.add(cb);
    window.addEventListener("storage", cb);
    return () => {
      collapseListeners.delete(cb);
      window.removeEventListener("storage", cb);
    };
  },
  get(): boolean {
    try {
      return window.localStorage.getItem(COLLAPSE_KEY) === "1";
    } catch {
      return false;
    }
  },
  set(value: boolean) {
    try {
      window.localStorage.setItem(COLLAPSE_KEY, value ? "1" : "0");
    } catch {
      /* storage unavailable: the change lasts until reload */
    }
    memoryCollapsed = value;
    collapseListeners.forEach((l) => l());
  },
};
let memoryCollapsed: boolean | null = null;

function AppLayout({ children, pathname }: { children: ReactNode; pathname: string }) {
  const collapsed = useSyncExternalStore(
    collapseStore.subscribe,
    () => memoryCollapsed ?? collapseStore.get(),
    () => false,
  );
  const [drawer, setDrawer] = useState(false);
  useEffect(() => {
    if (!drawer) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setDrawer(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawer]);

  const toggle = () => collapseStore.set(!collapsed);

  return (
    <div className="min-h-screen lg:flex">
      {/* Desktop / tablet sidebar */}
      <aside
        className={`sticky top-0 hidden h-screen shrink-0 flex-col bg-deep px-3 py-5 transition-[width] duration-200 lg:flex ${collapsed ? "w-[76px]" : "w-64"}`}
        aria-label="Application"
      >
        <Link href="/" className={`mb-8 px-1.5 ${collapsed ? "flex justify-center" : ""}`} aria-label="Food Intelligence home">
          <BrandMark compact={collapsed} inverted />
        </Link>
        <nav aria-label="Main" className="flex-1 overflow-y-auto">
          <NavList pathname={pathname} compact={collapsed} />
        </nav>
        <div className="space-y-3 border-t border-white/10 pt-4">
          <ServicePill compact={collapsed} />
          <button
            type="button"
            onClick={toggle}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-expanded={!collapsed}
            className={`flex w-full items-center gap-2 rounded-xl px-3 py-2 text-xs text-sage/70 transition hover:bg-white/5 hover:text-white ${collapsed ? "justify-center" : ""}`}
          >
            {collapsed ? <IconChevronRight className="h-4 w-4" /> : <IconChevronLeft className="h-4 w-4" />}
            {collapsed ? null : "Collapse"}
          </button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <div className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-line bg-white/90 px-4 backdrop-blur lg:hidden">
        <Link href="/" aria-label="Food Intelligence home"><BrandMark /></Link>
        <button
          type="button"
          onClick={() => setDrawer(true)}
          aria-label="Open navigation"
          aria-expanded={drawer}
          aria-controls="mobile-drawer"
          className="flex h-11 w-11 items-center justify-center rounded-xl border border-line text-ink"
        >
          <IconMenu />
        </button>
      </div>

      {drawer ? (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <button type="button" aria-label="Close navigation" className="absolute inset-0 bg-deep/40" onClick={() => setDrawer(false)} />
          <div id="mobile-drawer" className="animate-fade-up absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col bg-deep px-3 py-5">
            <div className="mb-6 flex items-center justify-between px-1.5">
              <BrandMark inverted />
              <button type="button" onClick={() => setDrawer(false)} aria-label="Close navigation" className="flex h-11 w-11 items-center justify-center rounded-xl text-sage hover:bg-white/10">
                <IconClose />
              </button>
            </div>
            <nav aria-label="Main (mobile)" className="flex-1 overflow-y-auto">
              <NavList pathname={pathname} compact={false} onNavigate={() => setDrawer(false)} />
            </nav>
            <div className="border-t border-white/10 pt-4"><ServicePill compact={false} /></div>
          </div>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:px-10 lg:py-10">
          {children}
        </main>
        <footer className="border-t border-line px-4 py-5 text-xs text-muted sm:px-6 lg:px-10">
          <p className="mx-auto max-w-7xl">
            Consumer decision-support, not a medical or clinical assessment. Product data from user-submitted pages, uploads
            and Open Food Facts (ODbL). <Link href="/methodology" className="underline hover:text-forest">Methodology and limitations</Link>
          </p>
        </footer>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "/";
  if (pathname === "/") {
    return (
      <div className="flex min-h-screen flex-col">
        <SiteHeader />
        <main id="main" className="flex-1">{children}</main>
        <SiteFooter />
      </div>
    );
  }
  return <AppLayout pathname={pathname}>{children}</AppLayout>;
}
