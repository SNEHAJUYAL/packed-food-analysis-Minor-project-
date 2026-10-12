"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AnalysisStatusBadge, ClaimStatusBadge, EvidenceBadge, GradeBadge, SyntheticBadge } from "./badges";
import { CategorySelect, ProductRow, useCategories } from "./ProductsBrowser";
import { Badge, Card, EmptyState, ErrorState, ExternalLink, LoadingState, SectionHeading } from "./ui";
import { api } from "@/lib/api";
import { NUTRIENT_ORDER, basisLabel, formatInr, formatNumber, formatPercent, formatTimestamp, hostOf, humanize, nutrientUnit, safeHref } from "@/lib/format";
import { DIMENSIONS } from "@/lib/labels";
import { useApi } from "@/lib/useApi";
import type { CompareProduct, CompareResult } from "@/lib/types";

const SERIES_COLORS = ["#2f8f7f", "#4f86c6", "#8a6fc1", "#d29a3a", "#6b7a8f", "#c4708a"];

const PICKS: { key: "best_match" | "lowest_price_per_100" | "best_nutrition"; label: string }[] = [
  { key: "best_match", label: "Best match" },
  { key: "lowest_price_per_100", label: "Lowest price per 100" },
  { key: "best_nutrition", label: "Best nutrition" },
];

const shortName = (p: CompareProduct) => p.name ?? `Product ${p.product_id}`;

export function ComparePicker({ initial = [] }: { initial?: number[] }) {
  const router = useRouter();
  const categories = useCategories();
  const [category, setCategory] = useState("");
  const [selected, setSelected] = useState<number[]>(initial);
  const [state] = useApi((signal) => api.listProducts({ category, limit: 50 }, signal), [category]);
  const toggle = (id: number) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : s.length >= 6 ? s : [...s, id]));

  return (
    <Card>
      <SectionHeading
        title="Choose products"
        subtitle="Pick 2–6 stored products from one category. Filtering by category keeps the comparison on a consistent basis."
      />
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <CategorySelect id="compare-category" value={category} onChange={(v) => { setCategory(v); setSelected([]); }} categories={categories} />
        <button
          type="button"
          disabled={selected.length < 2}
          onClick={() => router.push(`/compare?ids=${selected.join(",")}`)}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
        >
          Compare {selected.length ? `(${selected.length})` : ""}
        </button>
      </div>
      <div className="mt-4">
        {state.kind === "loading" ? <LoadingState label="Loading stored products…" /> : null}
        {state.kind === "error" ? <ErrorState title="Could not load products" message={state.error.message} code={state.error.code} /> : null}
        {state.kind === "ready" ? (
          state.data.products.length === 0 ? (
            <EmptyState title="No stored products in this category yet." />
          ) : (
            <ul className="space-y-2">
              {state.data.products.map((p) => (
                <ProductRow key={p.product_id} p={p} selected={selected.includes(p.product_id)} onToggle={toggle} disabled={selected.length >= 6} />
              ))}
            </ul>
          )
        ) : null}
      </div>
    </Card>
  );
}

export function CompareResultView({ data }: { data: CompareResult }) {
  const products = data.products ?? [];
  const basis = basisLabel(data.basis);
  const nutrientKeys = NUTRIENT_ORDER.filter((k) => products.some((p) => p.nutrition && k in p.nutrition));
  const chartData = DIMENSIONS.map((d) => {
    const row: Record<string, string | number | null> = { dimension: humanize(d) };
    products.forEach((p) => {
      const v = p.dimensions?.[d];
      row[`p${p.product_id}`] = v === null || v === undefined ? null : Math.round(v);
    });
    return row;
  });
  const nameById = (id: number) => {
    const p = products.find((x) => x.product_id === id);
    return p ? shortName(p) : `Product ${id}`;
  };
  const diffs = data.ingredient_differences;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
        <span>{data.category ? humanize(data.category) : "Category not stated"}</span>
        <span aria-hidden="true">·</span>
        <span>All values {basis}</span>
        <span aria-hidden="true">·</span>
        <span>Methodology v{data.methodology_version}</span>
      </div>

      {data.picks ? (
        <section aria-labelledby="picks-heading">
          <h2 id="picks-heading" className="sr-only">Picks</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            {PICKS.map(({ key, label }) => {
              const pick = data.picks?.[key];
              return (
                <Card key={key} className="!p-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-brand-700">{label}</p>
                  {pick ? (
                    <>
                      <Link href={`/products/${pick.product_id}`} className="mt-1 block font-medium text-ink hover:underline">
                        {pick.name ?? nameById(pick.product_id)}
                      </Link>
                      <p className="mt-1 text-sm text-slate-700">{pick.reason}</p>
                    </>
                  ) : (
                    <p className="mt-1 text-sm text-muted">No pick from the available data.</p>
                  )}
                </Card>
              );
            })}
          </div>
        </section>
      ) : null}

      {data.rationale?.length ? (
        <Card>
          <h2 className="font-semibold text-ink">Rationale</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-700">
            {data.rationale.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </Card>
      ) : null}

      <Card>
        <SectionHeading title="Dimension scores" subtitle="0–100. A missing bar means that dimension was not scored for that product." />
        <div className="h-72 w-full" role="img" aria-label="Grouped bar chart of dimension scores per product">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 8, left: -16 }}>
              <CartesianGrid vertical={false} stroke="#e3e7ec" />
              <XAxis dataKey="dimension" tick={{ fontSize: 12, fill: "#1f2a37" }} interval={0} />
              <YAxis domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={{ fontSize: 12, fill: "#5b6676" }} />
              <Tooltip contentStyle={{ borderRadius: 8, borderColor: "#e3e7ec", fontSize: 12 }} formatter={(v) => (v === null || v === undefined ? "not scored" : `${v} / 100`)} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {products.map((p, i) => (
                <Bar key={p.product_id} dataKey={`p${p.product_id}`} name={shortName(p)} fill={SERIES_COLORS[i % SERIES_COLORS.length]} radius={[4, 4, 0, 0]} isAnimationActive={false} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card className="!px-0 sm:!px-0">
        <div className="px-4 sm:px-6">
          <SectionHeading title="Side by side" subtitle={`Nutrition ${basis}. Missing values are shown as not found, never as zero.`} />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <caption className="sr-only">Product comparison table</caption>
            <thead>
              <tr className="border-b border-line align-bottom">
                <th scope="col" className="sticky left-0 z-10 w-40 bg-white px-4 py-2 text-xs font-medium uppercase tracking-wide text-muted sm:pl-6">Attribute</th>
                {products.map((p) => (
                  <th key={p.product_id} scope="col" className="px-4 py-2 font-medium text-ink">
                    <Link href={`/products/${p.product_id}`} className="hover:underline">{shortName(p)}</Link>
                    {p.brand ? <span className="block text-xs font-normal text-muted">{p.brand}</span> : null}
                    {p.is_synthetic ? <span className="mt-1 block"><SyntheticBadge /></span> : null}
                    {p.status && p.status !== "complete" ? <span className="mt-1 block"><AnalysisStatusBadge status={p.status} /></span> : null}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              <Row label="Overall">
                {products.map((p) => (
                  <td key={p.product_id} className="px-4 py-2">
                    <span className="inline-flex items-center gap-2">
                      <GradeBadge grade={p.grade} size="sm" />
                      {p.overall ?? <span className="text-muted">Not scored</span>}
                    </span>
                  </td>
                ))}
              </Row>
              {DIMENSIONS.map((d) => (
                <Row key={d} label={humanize(d)}>
                  {products.map((p) => (
                    <td key={p.product_id} className="px-4 py-2 tabular-nums">
                      {p.dimensions?.[d] !== null && p.dimensions?.[d] !== undefined ? Math.round(p.dimensions[d]!) : <span className="text-muted">Not scored</span>}
                    </td>
                  ))}
                </Row>
              ))}
              <Row label={`Price per 100 ${data.basis === "per_100ml" ? "ml" : "g"}`}>
                {products.map((p) => (
                  <td key={p.product_id} className="px-4 py-2 tabular-nums">{p.price_per_100 !== null ? formatInr(p.price_per_100) : <span className="text-muted">Not found</span>}</td>
                ))}
              </Row>
              {nutrientKeys.map((k) => (
                <Row key={k} label={humanize(k)}>
                  {products.map((p) => {
                    const n = p.nutrition?.[k];
                    return (
                      <td key={p.product_id} className="px-4 py-2">
                        <span className="flex flex-wrap items-center gap-1.5">
                          {n && n.value !== null ? <span className="tabular-nums">{formatNumber(n.value)} {n.unit ?? nutrientUnit(k)}</span> : <span className="text-muted">Not found</span>}
                          {n ? <EvidenceBadge label={n.label} /> : null}
                        </span>
                      </td>
                    );
                  })}
                </Row>
              ))}
              <Row label="Data completeness">
                {products.map((p) => (
                  <td key={p.product_id} className="px-4 py-2">{formatPercent(p.completeness)}</td>
                ))}
              </Row>
              <Row label="Ingredient classes">
                {products.map((p) => (
                  <td key={p.product_id} className="px-4 py-2">
                    <span className="flex flex-wrap gap-1">
                      {p.ingredient_classes?.length ? p.ingredient_classes.map((c) => <Badge key={c}>{humanize(c)}</Badge>) : <span className="text-muted">None identified</span>}
                    </span>
                  </td>
                ))}
              </Row>
              <Row label="Claims">
                {products.map((p) => (
                  <td key={p.product_id} className="px-4 py-2">
                    {p.claims?.length ? (
                      <ul className="space-y-1.5">
                        {p.claims.map((c, i) => (
                          <li key={i}>
                            <span className="block text-ink">“{c.matched_text ?? c.claim}”</span>
                            <ClaimStatusBadge status={c.status} />
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <span className="text-muted">No claims matched</span>
                    )}
                  </td>
                ))}
              </Row>
              <Row label="Source">
                {products.map((p) => {
                  const href = safeHref(p.source_url);
                  return (
                    <td key={p.product_id} className="px-4 py-2 text-xs">
                      {href ? <ExternalLink href={href}>{hostOf(href)}</ExternalLink> : <span className="text-muted">—</span>}
                      <span className="block text-muted">checked {formatTimestamp(p.collected_at)}</span>
                    </td>
                  );
                })}
              </Row>
            </tbody>
          </table>
        </div>
      </Card>

      {diffs ? (
        <Card>
          <SectionHeading title="Ingredient class differences" subtitle="Classes describe processing and disclosure signals, not health effects." />
          <div className="space-y-3 text-sm">
            <div>
              <p className="font-medium text-ink">Shared by all</p>
              <div className="mt-1 flex flex-wrap gap-1">
                {diffs.shared_classes?.length ? diffs.shared_classes.map((c) => <Badge key={c}>{humanize(c)}</Badge>) : <span className="text-muted">None</span>}
              </div>
            </div>
            {Object.entries(diffs.only_in ?? {}).map(([id, classes]) => (
              <div key={id}>
                <p className="font-medium text-ink">Only in {nameById(Number(id))}</p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {classes.length ? classes.map((c) => <Badge key={c} tone="blue">{humanize(c)}</Badge>) : <span className="text-muted">None</span>}
                </div>
              </div>
            ))}
          </div>
        </Card>
      ) : null}
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <tr className="align-top">
      <th scope="row" className="sticky left-0 z-10 bg-white px-4 py-2 font-medium text-slate-700 sm:pl-6">{label}</th>
      {children}
    </tr>
  );
}

export function CompareView({ ids }: { ids: number[] }) {
  const enough = ids.length >= 2;
  const [state, retry] = useApi(enough ? (signal) => api.compare({ product_ids: ids }, signal) : null, [ids.join(",")]);

  if (!enough) {
    return (
      <div className="space-y-4">
        {ids.length === 1 ? <p className="text-sm text-muted">Choose at least one more product.</p> : null}
        <ComparePicker initial={ids} />
      </div>
    );
  }
  return (
    <div className="space-y-4">
      <p className="text-sm">
        <Link href="/compare" className="text-brand-700 hover:underline">Change products</Link>
      </p>
      {state.kind === "loading" ? <LoadingState label="Comparing products…" /> : null}
      {state.kind === "error" ? (
        <ErrorState
          title="Could not compare these products"
          message={state.error.message}
          code={state.error.code}
          action={
            <div className="flex gap-4">
              <button type="button" className="underline" onClick={retry}>Try again</button>
              <Link href="/compare" className="underline">Choose other products</Link>
            </div>
          }
        />
      ) : null}
      {state.kind === "ready" ? <CompareResultView data={state.data} /> : null}
    </div>
  );
}
