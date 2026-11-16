"use client";

import Link from "next/link";
import { useState } from "react";
import { GradeBadge, SyntheticBadge } from "./badges";
import { IconArrowRight, IconSearch } from "./icons";
import { CategorySelect, useCategories } from "./ProductsBrowser";
import { EmptyState, ErrorState, LoadingState, buttonClass, inputClass } from "./ui";
import { api } from "@/lib/api";
import { formatInr, humanize } from "@/lib/format";
import { useApi } from "@/lib/useApi";

/** Search stored products and open a per-product page built from `hrefTemplate` ("{id}" is replaced). */
export function ProductPicker({ hrefTemplate, actionLabel }: { hrefTemplate: string; actionLabel: string }) {
  const categories = useCategories();
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [state, retry] = useApi((signal) => api.listProducts({ category, q: submitted, limit: 30 }, signal), [category, submitted]);
  const href = (id: number) => hrefTemplate.replace("{id}", String(id));

  return (
    <div className="space-y-4">
      <form
        className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-line bg-white p-4 shadow-[var(--shadow-card)] sm:flex-row sm:items-end"
        onSubmit={(e) => { e.preventDefault(); setSubmitted(query.trim()); }}
      >
        <div className="flex flex-1 flex-col gap-1">
          <label htmlFor="picker-search" className="text-xs font-medium text-slate-700">Start from a product</label>
          <span className="relative">
            <IconSearch className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input id="picker-search" type="search" value={query} onChange={(e) => setQuery(e.target.value)}
              placeholder="Search name or brand" className={`${inputClass} pl-10`} />
          </span>
        </div>
        <CategorySelect id="picker-category" value={category} onChange={setCategory} categories={categories} />
        <button type="submit" className={`${buttonClass.primary} !py-2.5`}>Search</button>
      </form>

      {state.kind === "loading" ? <LoadingState label="Loading stored products…" /> : null}
      {state.kind === "error" ? (
        <ErrorState title="Could not load products" message={state.error.message} code={state.error.code}
          action={<button type="button" className="font-medium underline" onClick={retry}>Try again</button>} />
      ) : null}
      {state.kind === "ready" ? (
        state.data.products.length === 0 ? (
          <EmptyState title="No stored products match.">
            <p><Link href="/analyze" className="text-forest underline">Analyze a product</Link> to add one.</p>
          </EmptyState>
        ) : (
          <>
            <p className="text-xs text-muted">Showing {state.data.products.length} of {state.data.total}</p>
            <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {state.data.products.map((p) => (
                <li key={p.product_id}>
                  <Link href={href(p.product_id)} className="group flex h-full flex-col rounded-[var(--radius-card)] border border-line bg-white p-4 transition hover:border-brand-300 hover:shadow-[var(--shadow-card)]">
                    <span className="flex items-start gap-3">
                      <GradeBadge grade={p.grade} />
                      <span className="min-w-0 flex-1">
                        <span className="block font-semibold text-ink group-hover:text-forest">{p.name ?? `Product ${p.product_id}`}</span>
                        <span className="block text-xs text-muted">{[p.brand, p.category ? humanize(p.category) : null].filter(Boolean).join(" · ")}</span>
                      </span>
                    </span>
                    <span className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-600">
                      {p.is_synthetic ? <SyntheticBadge /> : null}
                      <span>Score {p.overall ?? "not scored"}</span>
                      <span>· {formatInr(p.price_per_100)} per 100 {p.pack_unit ?? "g/ml"}</span>
                    </span>
                    <span className="mt-auto flex items-center gap-1 pt-3 text-sm font-medium text-forest">
                      {actionLabel} <IconArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </>
        )
      ) : null}
    </div>
  );
}
