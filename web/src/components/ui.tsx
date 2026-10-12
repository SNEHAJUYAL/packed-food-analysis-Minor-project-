"use client";

import { useId, useState, type ReactNode } from "react";
import type { Tone } from "@/lib/labels";

const TONE_CLASSES: Record<Tone, string> = {
  green: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  teal: "bg-teal-50 text-teal-800 ring-teal-200",
  amber: "bg-amber-50 text-amber-900 ring-amber-200",
  slate: "bg-slate-100 text-slate-700 ring-slate-200",
  blue: "bg-sky-50 text-sky-800 ring-sky-200",
  violet: "bg-violet-50 text-violet-800 ring-violet-200",
  rose: "bg-rose-50 text-rose-800 ring-rose-200",
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
        className={`${open ? "visible opacity-100" : "invisible opacity-0"} absolute left-1/2 top-full z-30 mt-1.5 w-64 max-w-[80vw] -translate-x-1/2 rounded-lg bg-slate-800 px-3 py-2 text-xs font-normal normal-case leading-snug tracking-normal text-white shadow-lg transition-opacity`}
      >
        {children}
      </span>
    </span>
  );
}

export function Card({ children, className = "", id }: { children: ReactNode; className?: string; id?: string }) {
  return (
    <div id={id} className={`rounded-2xl border border-line bg-white p-4 shadow-sm sm:p-6 ${className}`}>
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
        <h2 id={id} className="text-lg font-semibold text-ink sm:text-xl">
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

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-3 rounded-2xl border border-line bg-white p-6 text-sm text-muted">
      <Spinner />
      {label}
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
    <div role="alert" className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950 sm:p-6">
      <p className="font-semibold">{title}</p>
      <p className="mt-1">{message}</p>
      {code && code !== "error" ? <p className="mt-2 text-xs text-amber-800">Code: {code}</p> : null}
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-muted">
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
