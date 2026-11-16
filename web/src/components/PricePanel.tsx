"use client";

import { useState, type FormEvent } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Badge, Card, EmptyState, ErrorState, ExternalLink, LoadingState, Note, SectionHeading, Spinner, buttonClass, inputClass } from "./ui";
import { ApiError, api } from "@/lib/api";
import { formatInr, formatNumber, safeHref } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import type { PriceEvidence, PriceSummary } from "@/lib/types";

const EVIDENCE_TONE: Record<PriceEvidence, "green" | "teal" | "amber" | "violet"> = {
  invoice: "green", hand: "teal", unverified: "amber", synthetic: "violet",
};
const EVIDENCE_LABEL: Record<PriceEvidence, string> = {
  invoice: "Invoice-backed", hand: "Entered by hand", unverified: "Unverified", synthetic: "Synthetic demo",
};
const LINE_COLORS = ["#234b39", "#b87422", "#3c6e9e", "#8a4fa3", "#c0504d", "#4d8f6a", "#6b6b6b", "#a37c2c"];

function day(iso: string | null): string {
  if (!iso) return "date unknown";
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function TrendArrow({ trend, change, pct }: { trend: string | null; change: number | null; pct: number | null }) {
  if (!trend || change === null) return <span className="text-muted">one observation</span>;
  if (trend === "flat") return <span className="text-muted">no change</span>;
  const up = trend === "up";
  return (
    <span className={up ? "text-[#a3361f]" : "text-forest"}>
      {up ? "▲" : "▼"} {formatInr(Math.abs(change))}{pct !== null ? ` (${up ? "+" : "−"}${formatNumber(Math.abs(pct))}%)` : ""}
    </span>
  );
}

/** Price per 100 g/ml over time, one line per shop. */
function HistoryChart({ data }: { data: PriceSummary }) {
  const shops = Array.from(new Set(data.observations.filter((o) => !o.is_mrp && o.price_per_100 != null).map((o) => o.retailer_label)));
  const byDate = new Map<string, Record<string, number | string>>();
  for (const o of data.observations) {
    if (o.is_mrp || o.price_per_100 == null || !o.observed_at) continue;
    const key = o.observed_at.slice(0, 10);
    const row = byDate.get(key) ?? { date: key };
    row[o.retailer_label] = o.price_per_100;
    byDate.set(key, row);
  }
  const rows = Array.from(byDate.values()).sort((a, b) => String(a.date).localeCompare(String(b.date)));
  if (rows.length < 2) {
    return <Note>Price history needs prices from at least two dates. {rows.length === 1 ? "So far all prices are from one day." : ""}</Note>;
  }
  return (
    <figure aria-label={`Price per ${data.basis} over time`}>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="#eef1ea" vertical={false} />
            <XAxis dataKey="date" tickFormatter={(d: string) => day(d)} tick={{ fontSize: 11, fill: "#5f6961" }} />
            <YAxis tickFormatter={(v: number) => `₹${v}`} tick={{ fontSize: 11, fill: "#5f6961" }} width={56} />
            <Tooltip formatter={(v) => [`₹${Number(v).toFixed(2)} per ${data.basis}`]} labelFormatter={(d) => day(String(d))} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {shops.map((s, i) => (
              <Line key={s} type="monotone" dataKey={s} stroke={LINE_COLORS[i % LINE_COLORS.length]} strokeWidth={2}
                    dot={{ r: 3 }} connectNulls isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="mt-1 text-xs text-muted">Price per {data.basis} on each date a price was recorded. The table below lists every observation.</figcaption>
    </figure>
  );
}

function AddPriceForm({ productId, data, onSaved }: { productId: number; data: PriceSummary; onSaved: (d: PriceSummary) => void }) {
  const [retailer, setRetailer] = useState("");
  const [price, setPrice] = useState("");
  const [size, setSize] = useState("");
  const [date, setDate] = useState("");
  const [place, setPlace] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const value = Number(price);
    if (!retailer) return setError("Choose the shop where you saw the price.");
    if (!(value > 0)) return setError("Enter the selling price in rupees.");
    setBusy(true);
    setError(null);
    try {
      const out = await api.addPrice(productId, {
        retailer, price_inr: value, pack_size_text: size.trim() || null,
        observed_at: date ? new Date(`${date}T12:00:00`).toISOString() : null, place: place.trim() || null,
      });
      onSaved(out);
      setPrice("");
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The price could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <details className="rounded-2xl border border-line bg-white p-4">
      <summary className="cursor-pointer text-sm font-semibold text-ink">Add a price you saw</summary>
      <p className="mt-2 text-xs text-muted">
        Record a price from the Blinkit, Zepto or Instamart app, a shop shelf or the MRP on the pack. It is saved as a
        hand-entered observation with today’s date unless you choose another.
      </p>
      <form onSubmit={submit} className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <label className="text-xs text-muted">Shop
          <select aria-label="Shop" value={retailer} onChange={(e) => setRetailer(e.target.value)} className={`${inputClass} mt-1`} disabled={busy}>
            <option value="">Choose…</option>
            {Object.entries(data.retailer_options).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <label className="text-xs text-muted">Price (₹)
          <input aria-label="Price in rupees" type="number" min="0.01" step="0.01" value={price} onChange={(e) => setPrice(e.target.value)} className={`${inputClass} mt-1`} disabled={busy} />
        </label>
        <label className="text-xs text-muted">Pack size
          <input aria-label="Pack size" placeholder="same as product" value={size} onChange={(e) => setSize(e.target.value)} className={`${inputClass} mt-1`} disabled={busy} />
        </label>
        <label className="text-xs text-muted">Date seen
          <input aria-label="Date seen" type="date" value={date} max={new Date().toISOString().slice(0, 10)} onChange={(e) => setDate(e.target.value)} className={`${inputClass} mt-1`} disabled={busy} />
        </label>
        <label className="text-xs text-muted">City or PIN
          <input aria-label="City or PIN code" value={place} onChange={(e) => setPlace(e.target.value)} className={`${inputClass} mt-1`} disabled={busy} />
        </label>
        <div className="flex items-center gap-3 sm:col-span-2 lg:col-span-5">
          <button type="submit" className={buttonClass.primary} disabled={busy}>
            {busy ? <><Spinner className="h-4 w-4" /> Saving…</> : "Save price"}
          </button>
          {saved && !error ? <span role="status" className="text-sm text-forest">Saved. Value for money was recalculated.</span> : null}
          {error ? <span role="alert" className="text-sm text-[#a3361f]">{error}</span> : null}
        </div>
      </form>
    </details>
  );
}

export function PricePanel({ productId }: { productId: number }) {
  const [state, retry] = useApi((signal) => api.prices(productId, signal), [productId]);
  const [override, setOverride] = useState<PriceSummary | null>(null);

  if (state.kind === "loading") return <Card><LoadingState label="Loading prices…" lines={2} /></Card>;
  if (state.kind === "error") {
    return <Card><ErrorState title="Prices could not be loaded" message={state.error.message} action={<button type="button" className="underline" onClick={retry}>Try again</button>} /></Card>;
  }
  const raw = override ?? state.data;
  // Tolerate partial bodies (older API, test doubles): missing lists are treated as empty.
  const data: PriceSummary = {
    ...raw,
    basis: raw?.basis ?? "100 g",
    observations: raw?.observations ?? [],
    retailers: raw?.retailers ?? [],
    notes: raw?.notes ?? [],
    retailer_options: raw?.retailer_options ?? {},
  };
  const selling = data.observations.filter((o) => !o.is_mrp);

  return (
    <Card>
      <SectionHeading
        id="prices-heading"
        title="Prices across shops"
        subtitle={`Price per ${data.basis} at each shop, how it has moved, and the cheapest place to buy.`}
      />
      <div className="space-y-4">
        {data.notes.map((n) => <Note key={n} tone={data.is_synthetic ? "warn" : "neutral"}>{n}</Note>)}

        {selling.length ? (
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl bg-brand-50/60 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-muted">Cheapest now</p>
              <p className="mt-1 text-lg font-semibold text-ink">{data.cheapest ?? "—"}</p>
              <p className="text-xs text-muted">{data.retailers[0]?.latest_price_per_100 != null ? `${formatInr(data.retailers[0].latest_price_per_100)} per ${data.basis}` : ""}</p>
            </div>
            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-muted">Price difference between shops</p>
              <p className="mt-1 text-lg font-semibold text-ink">
                {data.spread ? `${formatInr(data.spread.difference_per_100)} per ${data.basis}` : "Needs two shops"}
              </p>
              <p className="text-xs text-muted">{data.spread ? `${data.spread.dearest} costs ${formatNumber(data.spread.difference_percent ?? 0)}% more than ${data.spread.cheapest}` : ""}</p>
            </div>
            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-muted">Against its category</p>
              <p className="mt-1 text-lg font-semibold text-ink">
                {data.vs_category ? `${data.vs_category.difference_percent > 0 ? "+" : ""}${formatNumber(data.vs_category.difference_percent)}%` : "No comparison yet"}
              </p>
              <p className="text-xs text-muted">{data.vs_category ? `vs median ${formatInr(data.vs_category.category_median_per_100)} per ${data.basis} of ${data.vs_category.peer_count} stored products` : "Needs priced products in the same category"}</p>
            </div>
          </div>
        ) : (
          <EmptyState title="No price recorded yet">Add a price you saw below to start the comparison.</EmptyState>
        )}

        {data.mrp ? (
          <p className="text-sm text-slate-700">
            MRP on the latest invoice: <strong>{formatInr(data.mrp.price_inr)}</strong> ({day(data.mrp.observed_at)}).
          </p>
        ) : null}

        <HistoryChart data={data} />

        {data.retailers.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-sm">
              <caption className="sr-only">Latest price at each shop</caption>
              <thead>
                <tr className="border-b border-line text-left text-xs uppercase tracking-wide text-muted">
                  <th className="py-2 pr-3 font-medium">Shop</th>
                  <th className="py-2 pr-3 font-medium">Latest price</th>
                  <th className="py-2 pr-3 font-medium">Per {data.basis}</th>
                  <th className="py-2 pr-3 font-medium">Change</th>
                  <th className="py-2 pr-3 font-medium">Seen</th>
                  <th className="py-2 font-medium">Evidence</th>
                </tr>
              </thead>
              <tbody>
                {data.retailers.map((r) => {
                  const href = safeHref(r.source_url);
                  return (
                    <tr key={r.retailer} className="border-b border-line/70">
                      <td className="py-2 pr-3 font-medium text-ink">{href ? <ExternalLink href={href}>{r.retailer_label}</ExternalLink> : r.retailer_label}</td>
                      <td className="py-2 pr-3">{formatInr(r.latest_price_inr)}{r.pack_size ? <span className="text-xs text-muted"> · {formatNumber(r.pack_size)} {r.pack_unit}</span> : null}</td>
                      <td className="py-2 pr-3 tabular-nums">{formatInr(r.latest_price_per_100)}</td>
                      <td className="py-2 pr-3"><TrendArrow trend={r.trend} change={r.change_inr} pct={r.change_percent} /></td>
                      <td className="py-2 pr-3 text-muted">{day(r.latest_observed_at)}{r.observations > 1 ? ` · ${r.observations} prices` : ""}</td>
                      <td className="py-2">
                        <span className="flex flex-wrap gap-1">
                          <Badge tone={EVIDENCE_TONE[r.evidence]}>{EVIDENCE_LABEL[r.evidence]}</Badge>
                          {r.outlier ? <Badge tone="amber" title="Far from this product's other prices">Check</Badge> : null}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}

        {selling.length ? (
          <details className="text-sm">
            <summary className="cursor-pointer font-medium text-ink">Every price observation ({data.observations.length})</summary>
            <ul className="mt-2 space-y-1 text-slate-700">
              {data.observations.map((o) => (
                <li key={o.id}>
                  {day(o.observed_at)} · {o.retailer_label} · {formatInr(o.price_inr)}
                  {o.pack_size ? ` for ${formatNumber(o.pack_size)} ${o.pack_unit}` : ""} · {o.is_mrp ? "MRP" : o.evidence_text}
                  {o.outlier ? " · check" : ""}
                </li>
              ))}
            </ul>
          </details>
        ) : null}

        {!data.is_synthetic ? <AddPriceForm productId={productId} data={data} onSaved={setOverride} /> : null}
      </div>
    </Card>
  );
}
