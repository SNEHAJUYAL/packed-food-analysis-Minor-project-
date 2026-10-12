"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AnalysisStatusBadge, GradeBadge, SyntheticBadge } from "./badges";
import { EmptyState, ErrorState, LoadingState } from "./ui";
import { api } from "@/lib/api";
import { formatInr, formatNumber, formatTimestamp, hostOf, humanize } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import type { Category, ProductSummary } from "@/lib/types";

export function CategorySelect({
  value,
  onChange,
  categories,
  allowAll = true,
  id = "category-filter",
}: {
  value: string;
  onChange: (v: string) => void;
  categories: Category[];
  allowAll?: boolean;
  id?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-medium text-muted">Category</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)} className="rounded-lg border border-line bg-white px-3 py-2 text-sm">
        {allowAll ? <option value="">All categories</option> : null}
        {categories.map((c) => (
          <option key={c.id} value={c.id}>
            {c.label} ({c.product_count})
          </option>
        ))}
      </select>
    </div>
  );
}

export function useCategories(): Category[] {
  const [cats, setCats] = useState<Category[]>([]);
  useEffect(() => {
    const ctrl = new AbortController();
    api.categories(ctrl.signal).then((r) => setCats(r.categories ?? [])).catch(() => setCats([]));
    return () => ctrl.abort();
  }, []);
  return cats;
}

export function ProductRow({
  p,
  selected,
  onToggle,
  disabled,
}: {
  p: ProductSummary;
  selected?: boolean;
  onToggle?: (id: number) => void;
  disabled?: boolean;
}) {
  const unit = p.pack_unit ?? "g/ml";
  return (
    <li className="flex items-start gap-3 rounded-2xl border border-line bg-white p-4">
      {onToggle ? (
        <input
          type="checkbox"
          className="mt-2 h-4 w-4 accent-brand-600"
          checked={!!selected}
          disabled={disabled && !selected}
          onChange={() => onToggle(p.product_id)}
          aria-label={`Select ${p.name ?? `product ${p.product_id}`} for comparison`}
        />
      ) : null}
      <GradeBadge grade={p.grade} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <Link href={`/products/${p.product_id}`} className="font-medium text-ink hover:underline">
              {p.name ?? `Product ${p.product_id}`}
            </Link>
            <p className="text-xs text-muted">
              {[p.brand, p.category ? humanize(p.category) : null].filter(Boolean).join(" · ")}
            </p>
          </div>
          <p className="text-right text-sm">
            {p.overall !== null ? <span className="font-semibold text-ink">{p.overall} / 100</span> : <span className="text-muted">Not scored</span>}
          </p>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600">
          {p.is_synthetic ? <SyntheticBadge /> : null}
          <AnalysisStatusBadge status={p.status} />
          <span>Pack {p.pack_size !== null ? `${formatNumber(p.pack_size)} ${p.pack_unit ?? ""}` : "not found"}</span>
          <span>{formatInr(p.price_per_100)} per 100 {unit}</span>
          <span>{p.source_url ? hostOf(p.source_url) : humanize(p.source_type)}</span>
          <span>checked {formatTimestamp(p.collected_at)}</span>
        </div>
      </div>
    </li>
  );
}

export function ProductsBrowser() {
  const categories = useCategories();
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [selected, setSelected] = useState<number[]>([]);
  const [state, retry] = useApi((signal) => api.listProducts({ category, q: submitted, limit: 50 }, signal), [category, submitted]);

  const toggle = (id: number) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : s.length >= 6 ? s : [...s, id]));

  return (
    <div className="space-y-4">
      <form
        className="flex flex-col gap-3 sm:flex-row sm:items-end"
        onSubmit={(e) => {
          e.preventDefault();
          setSubmitted(query.trim());
        }}
      >
        <div className="flex flex-1 flex-col gap-1">
          <label htmlFor="product-search" className="text-xs font-medium text-muted">Search name or brand</label>
          <input
            id="product-search"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="rounded-lg border border-line bg-white px-3 py-2 text-sm"
            placeholder="e.g. oats"
          />
        </div>
        <CategorySelect value={category} onChange={(v) => { setCategory(v); setSelected([]); }} categories={categories} />
        <button type="submit" className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
          Search
        </button>
      </form>

      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-white p-3 text-sm ring-1 ring-line">
        <span className="text-slate-700">
          {selected.length} selected for comparison (2–6, same category)
        </span>
        <Link
          href={selected.length >= 2 ? `/compare?ids=${selected.join(",")}` : "#"}
          aria-disabled={selected.length < 2}
          onClick={(e) => selected.length < 2 && e.preventDefault()}
          className={`rounded-lg px-3 py-1.5 font-medium ${selected.length >= 2 ? "bg-brand-600 text-white hover:bg-brand-700" : "cursor-not-allowed bg-slate-100 text-slate-400"}`}
        >
          Compare selected
        </Link>
      </div>

      {state.kind === "loading" ? <LoadingState label="Loading stored products…" /> : null}
      {state.kind === "error" ? (
        <ErrorState
          title="Could not load products"
          message={state.error.message}
          code={state.error.code}
          action={<button type="button" className="underline" onClick={retry}>Try again</button>}
        />
      ) : null}
      {state.kind === "ready" ? (
        state.data.products.length === 0 ? (
          <EmptyState title="No stored products match.">
            <p>
              <Link href="/" className="text-brand-700 underline">Analyse a product page</Link> to add one.
            </p>
          </EmptyState>
        ) : (
          <>
            <p className="text-xs text-muted">
              Showing {state.data.products.length} of {state.data.total}
            </p>
            <ul className="space-y-3">
              {state.data.products.map((p) => (
                <ProductRow key={p.product_id} p={p} selected={selected.includes(p.product_id)} onToggle={toggle} disabled={selected.length >= 6} />
              ))}
            </ul>
          </>
        )
      ) : null}
    </div>
  );
}
