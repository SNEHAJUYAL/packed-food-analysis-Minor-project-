"use client";

import { scoreColor } from "@/lib/format";

export { scoreColor };

import Link from "next/link";
import { useId, useState, type ReactNode } from "react";
import { IconAlert, IconChevronRight, IconInfo } from "./icons";
import type { Tone } from "@/lib/labels";

const TONE_CLASSES: Record<Tone, string> = {
  green: "bg-brand-50 text-forest ring-brand-100",
  teal: "bg-sage/70 text-deep ring-brand-300/60",
  amber: "bg-[#fbf0e2] text-[#7a4a12] ring-[#f1d2a8]",
  slate: "bg-slate-100 text-slate-700 ring-slate-200",
  blue: "bg-[#eaf1f8] text-[#24527f] ring-[#cfe0f0]",
  violet: "bg-[#f1edf7] text-[#5a3f80] ring-[#ddd3ec]",
  rose: "bg-[#fbecea] text-[#8f3530] ring-[#f2cbc7]",
};

export function Badge({
  tone = "slate",
  children,
  className = "",
  title,
}: {
  tone?: Tone;
  children: ReactNode;
  className?: string;
  title?: string;
}) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TONE_CLASSES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

/**
 * Small accessible tooltip: shows on hover and keyboard focus, toggles on tap (mobile),
 * and is announced through aria-describedby.
 */
export function InfoTip({ label, children, className = "" }: { label: string; children: ReactNode; className?: string }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  return (
    <span className={`relative inline-flex ${className}`} onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button
        type="button"
        aria-label={label}
        aria-describedby={id}
        aria-expanded={open}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen((o) => !o)}
        onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
        className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-slate-300 text-[10px] font-semibold leading-none text-slate-500 hover:border-slate-400 hover:text-slate-700"
      >
        ?
      </button>
      <span
        role="tooltip"
        id={id}
        className={`${open ? "visible opacity-100" : "invisible opacity-0"} absolute left-1/2 top-full z-30 mt-1.5 w-64 max-w-[80vw] -translate-x-1/2 rounded-xl bg-deep px-3 py-2 text-xs font-normal normal-case leading-snug tracking-normal text-white shadow-lg transition-opacity`}
      >
        {children}
      </span>
    </span>
  );
}

export function Card({ children, className = "", id }: { children: ReactNode; className?: string; id?: string }) {
  return (
    <div id={id} className={`rounded-[var(--radius-card)] border border-line bg-white p-4 shadow-[var(--shadow-card)] sm:p-6 ${className}`}>
      {children}
    </div>
  );
}

export function SectionHeading({
  id,
  title,
  subtitle,
  action,
}: {
  id?: string;
  title: string;
  subtitle?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h2 id={id} className="text-lg font-semibold text-ink">
          {title}
        </h2>
        {subtitle ? <p className="mt-1 text-sm text-muted">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={`inline-block h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent ${className}`}
    />
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <span aria-hidden="true" className={`skeleton block rounded-lg ${className}`} />;
}

export function LoadingState({ label = "Loading…", lines = 3 }: { label?: string; lines?: number }) {
  return (
    <div role="status" aria-live="polite" className="rounded-[var(--radius-card)] border border-line bg-white p-5 sm:p-6">
      <p className="flex items-center gap-3 text-sm text-muted">
        <Spinner />
        {label}
      </p>
      {lines > 0 ? (
        <div className="mt-4 space-y-2.5">
          {Array.from({ length: lines }, (_, i) => (
            <Skeleton key={i} className={`h-3 ${i === lines - 1 ? "w-2/3" : "w-full"}`} />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message,
  code,
  action,
}: {
  title?: string;
  message: string;
  code?: string;
  action?: ReactNode;
}) {
  return (
    <div role="alert" className="flex gap-3 rounded-[var(--radius-card)] border border-[#f1d2a8] bg-[#fdf6ec] p-4 text-sm text-[#5c3a10] sm:p-5">
      <IconAlert className="mt-0.5 h-5 w-5 shrink-0 text-[#b87422]" />
      <div className="min-w-0">
        <p className="font-semibold text-[#4a2e0b]">{title}</p>
        <p className="mt-1">{message}</p>
        {code && code !== "error" ? <p className="mt-2 font-mono text-xs text-[#8a5a1c]">Code: {code}</p> : null}
        {action ? <div className="mt-3">{action}</div> : null}
      </div>
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-[var(--radius-card)] border border-dashed border-slate-300 bg-white/70 p-8 text-center text-sm text-muted">
      <span aria-hidden="true" className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-brand-50 text-forest">
        <IconInfo className="h-5 w-5" />
      </span>
      <p className="font-medium text-ink">{title}</p>
      {children ? <div className="mt-2">{children}</div> : null}
    </div>
  );
}

export function ExternalLink({ href, children, className = "" }: { href: string; children: ReactNode; className?: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer nofollow"
      className={`break-all text-brand-700 underline decoration-brand-100 underline-offset-2 hover:decoration-brand-500 ${className}`}
    >
      {children}
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}

export function BulletList({ items, className = "" }: { items: string[] | undefined | null; className?: string }) {
  if (!items || items.length === 0) return null;
  return (
    <ul className={`list-disc space-y-1 pl-5 text-sm text-slate-700 ${className}`}>
      {items.map((t, i) => (
        <li key={i}>{t}</li>
      ))}
    </ul>
  );
}

/* ------------------------------------------------------------------ layout primitives */

export const buttonClass = {
  primary:
    "inline-flex items-center justify-center gap-2 rounded-xl bg-forest px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-deep active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60",
  secondary:
    "inline-flex items-center justify-center gap-2 rounded-xl border border-line bg-white px-4 py-2.5 text-sm font-medium text-ink transition hover:border-brand-300 hover:bg-brand-50 active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60",
  ghost:
    "inline-flex items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-forest transition hover:bg-brand-50",
};

export const inputClass =
  "block w-full rounded-xl border border-line bg-white px-3.5 py-2.5 text-sm text-ink placeholder:text-slate-400 transition focus:border-brand-500 focus:outline-none focus:ring-4 focus:ring-brand-100 disabled:bg-slate-50";

export interface Crumb {
  label: string;
  href?: string;
}

/** Breadcrumb trail; the last item is the current page. */
export function Breadcrumbs({ crumbs }: { crumbs: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mb-3">
      <ol className="flex flex-wrap items-center gap-1 text-xs text-muted">
        {crumbs.map((c, i) => (
          <li key={`${c.label}-${i}`} className="inline-flex min-w-0 items-center gap-1">
            {i > 0 ? <IconChevronRight className="h-3 w-3 shrink-0 text-slate-400" /> : null}
            {c.href ? (
              <Link href={c.href} className="hover:text-forest hover:underline">{c.label}</Link>
            ) : (
              <span aria-current="page" className="truncate text-slate-700">{c.label}</span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

/** Page title block with breadcrumbs, optional eyebrow and actions. */
export function PageHeader({
  title,
  description,
  crumbs,
  eyebrow,
  actions,
}: {
  title: ReactNode;
  description?: ReactNode;
  crumbs?: Crumb[];
  eyebrow?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-6 sm:mb-8">
      {crumbs?.length ? <Breadcrumbs crumbs={crumbs} /> : null}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="max-w-3xl">
          {eyebrow ? <p className="mb-1.5 text-xs font-semibold uppercase tracking-[0.14em] text-brand-500">{eyebrow}</p> : null}
          <h1 className="text-2xl font-bold text-ink sm:text-[2rem] sm:leading-tight">{title}</h1>
          {description ? <p className="mt-2 text-sm leading-6 text-muted sm:text-[15px]">{description}</p> : null}
        </div>
        {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
      </div>
    </header>
  );
}

/** Colour for a 0–100 score: restrained, and never the only signal (the number is always shown). */
/**
 * Circular 0–100 indicator. A missing score draws an empty ring with a dash, never a zero.
 * The label is the accessible name; the number is visible text.
 */
export function ScoreRing({
  score,
  size = 88,
  stroke = 8,
  label,
  caption,
}: {
  score: number | null | undefined;
  size?: number;
  stroke?: number;
  label: string;
  caption?: string;
}) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const known = score !== null && score !== undefined && Number.isFinite(score);
  const value = known ? Math.max(0, Math.min(100, score as number)) : 0;
  return (
    <span className="relative inline-flex shrink-0 items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={label}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#eef1ea" strokeWidth={stroke} />
        {known ? (
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={scoreColor(value)}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${(value / 100) * c} ${c}`}
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
            style={{ transition: "stroke-dasharray 0.6s ease" }}
          />
        ) : null}
      </svg>
      <span aria-hidden="true" className="absolute inset-0 flex flex-col items-center justify-center leading-none">
        <span className="font-display font-bold text-ink tabular-nums" style={{ fontSize: size * 0.28 }}>
          {known ? Math.round(value) : "—"}
        </span>
        {caption ? <span className="mt-1 text-[10px] font-medium uppercase tracking-wider text-muted">{caption}</span> : null}
      </span>
    </span>
  );
}

/** KPI tile. `value` null shows "—" with the given note instead of a made-up figure. */
export function StatCard({
  label,
  value,
  note,
  icon,
}: {
  label: string;
  value: ReactNode;
  note?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="rounded-[var(--radius-card)] border border-line bg-white p-5 shadow-[var(--shadow-card)]">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.1em] text-muted">{label}</p>
        {icon ? <span aria-hidden="true" className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-forest">{icon}</span> : null}
      </div>
      <p className="mt-3 font-display text-3xl font-bold text-ink tabular-nums">{value ?? "—"}</p>
      {note ? <p className="mt-1 text-xs text-muted">{note}</p> : null}
    </div>
  );
}

/** Small info note with an icon, for honest "not available" statements. */
export function Note({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "warn" }) {
  return (
    <p className={`flex gap-2 rounded-xl p-3 text-sm ${tone === "warn" ? "bg-[#fdf6ec] text-[#5c3a10]" : "bg-slate-50 text-slate-700"}`}>
      <IconInfo className={`mt-0.5 h-4 w-4 shrink-0 ${tone === "warn" ? "text-[#b87422]" : "text-brand-500"}`} />
      <span>{children}</span>
    </p>
  );
}
