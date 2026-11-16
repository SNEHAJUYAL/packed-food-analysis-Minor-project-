"use client";

import type { ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CountRow } from "@/lib/catalog";

const INK = "#202b25";
const MUTED = "#5f6961";
const GRID = "#eef1ea";
const BAR = "#234b39";

function TooltipBox({ active, payload, unit }: { active?: boolean; payload?: { payload: CountRow }[]; unit: string }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="rounded-xl border border-line bg-white px-3 py-2 text-xs shadow-[var(--shadow-lift)]">
      <p className="font-semibold text-ink">{row.label}</p>
      <p className="text-muted"><span className="font-semibold text-ink tabular-nums">{row.count}</span> {unit}</p>
    </div>
  );
}

/**
 * Single-series count chart (one hue, no legend: the title names the series). A table view of the
 * same numbers is always available, so the chart never carries information on its own.
 */
export function CountBarChart({
  rows,
  unit = "products",
  layout = "horizontal",
  height,
  colorFor,
  xLabel,
}: {
  rows: CountRow[];
  unit?: string;
  /** horizontal: categories down the side (long labels); vertical: bins along the bottom. */
  layout?: "horizontal" | "vertical";
  height?: number;
  colorFor?: (row: CountRow) => string;
  xLabel?: string;
}) {
  const h = height ?? (layout === "horizontal" ? Math.max(160, rows.length * 34 + 40) : 240);
  const total = rows.reduce((s, r) => s + r.count, 0);
  return (
    <figure className="w-full">
      <div style={{ height: h }} className="w-full" role="img" aria-label={`Bar chart: ${rows.map((r) => `${r.label} ${r.count}`).join(", ")}`}>
        <ResponsiveContainer width="100%" height="100%">
          {layout === "horizontal" ? (
            <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 40, bottom: 4, left: 4 }} barCategoryGap={8}>
              <CartesianGrid horizontal={false} stroke={GRID} />
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: MUTED }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="label" width={132} tick={{ fontSize: 12, fill: INK }} axisLine={false} tickLine={false} />
              <Tooltip cursor={{ fill: "#eaf0e8" }} content={<TooltipBox unit={unit} />} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={18} isAnimationActive={false} label={{ position: "right", fontSize: 11, fill: INK }}>
                {rows.map((r) => <Cell key={r.key} fill={colorFor ? colorFor(r) : BAR} />)}
              </Bar>
            </BarChart>
          ) : (
            <BarChart data={rows} margin={{ top: 16, right: 8, bottom: xLabel ? 18 : 4, left: -18 }} barCategoryGap={4}>
              <CartesianGrid vertical={false} stroke={GRID} />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11, fill: MUTED }}
                axisLine={{ stroke: "#cdd3ca" }}
                tickLine={false}
                interval={0}
                label={xLabel ? { value: xLabel, position: "insideBottom", offset: -12, fontSize: 11, fill: MUTED } : undefined}
              />
              <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: MUTED }} axisLine={false} tickLine={false} />
              <Tooltip cursor={{ fill: "#eaf0e8" }} content={<TooltipBox unit={unit} />} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={36} isAnimationActive={false}>
                {rows.map((r) => <Cell key={r.key} fill={colorFor ? colorFor(r) : BAR} />)}
              </Bar>
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
      <details className="mt-2 text-xs text-muted">
        <summary className="cursor-pointer select-none hover:text-forest">View as table</summary>
        <table className="mt-2 w-full text-left">
          <thead><tr className="border-b border-line"><th scope="col" className="py-1 font-medium">Group</th><th scope="col" className="py-1 text-right font-medium">Count</th><th scope="col" className="py-1 text-right font-medium">Share</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key} className="border-b border-line/60">
                <td className="py-1 text-slate-700">{r.label}</td>
                <td className="py-1 text-right text-ink">{r.count}</td>
                <td className="py-1 text-right">{total ? `${Math.round((r.count / total) * 100)}%` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}

/** Chart container: title says what is counted, subtitle says the unit and coverage. */
export function ChartCard({ title, subtitle, children, action }: { title: string; subtitle?: ReactNode; children: ReactNode; action?: ReactNode }) {
  return (
    <section className="rounded-[var(--radius-card)] border border-line bg-white p-5 shadow-[var(--shadow-card)] sm:p-6">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-ink">{title}</h2>
          {subtitle ? <p className="mt-0.5 text-xs text-muted">{subtitle}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

/** Two-part share bar (e.g. real vs synthetic) with labels, never colour alone. */
export function ShareBar({ parts }: { parts: { label: string; count: number; color: string }[] }) {
  const total = parts.reduce((s, p) => s + p.count, 0);
  if (!total) return <p className="text-sm text-muted">No records.</p>;
  return (
    <div>
      <div className="flex h-3 w-full gap-0.5 overflow-hidden rounded-full bg-slate-100">
        {parts.filter((p) => p.count > 0).map((p) => (
          <span key={p.label} className="h-full first:rounded-l-full last:rounded-r-full" style={{ width: `${(p.count / total) * 100}%`, background: p.color }} />
        ))}
      </div>
      <ul className="mt-3 space-y-1.5 text-sm">
        {parts.map((p) => (
          <li key={p.label} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-2 text-slate-700">
              <span aria-hidden="true" className="h-2.5 w-2.5 rounded-sm" style={{ background: p.color }} />
              {p.label}
            </span>
            <span className="tabular-nums text-ink">
              {p.count} <span className="text-xs text-muted">({Math.round((p.count / total) * 100)}%)</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
