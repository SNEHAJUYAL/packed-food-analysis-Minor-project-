"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { GradeBadge, SyntheticBadge } from "./badges";
import { IconArrowRight, IconSearch } from "./icons";
import { Badge, Card, EmptyState, Note, Spinner, buttonClass, inputClass } from "./ui";
import { ApiError, api } from "@/lib/api";
import { formatInr, formatNumber, humanize } from "@/lib/format";
import type { SearchResult } from "@/lib/types";

/**
 * Find any packaged product by name or brand. Stored products open straight away; Open Food Facts
 * results are brought in and scored on request.
 */
export function ProductSearch({ initialQuery = "" }: { initialQuery?: string }) {
  const router = useRouter();
  const [text, setText] = useState(initialQuery);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [importing, setImporting] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const value = text.trim();
    if (value.length < 2) {
      setError("Type at least two letters of a product name or brand.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setResult(await api.search(value));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The search could not be completed.");
    } finally {
      setBusy(false);
    }
  }

  async function analyse(code: string) {
    setImporting(code);
    setError(null);
    try {
      const out = await api.importOff(code);
      router.push(`/products/${out.product_id}`);
    } catch (err) {
      setImporting(null);
      setError(err instanceof ApiError ? err.message : "This product could not be analysed.");
    }
  }

  const nothing = result && !result.stored.length && !result.online.length;
  const storedIds = result?.stored.map((p) => p.product_id).slice(0, 6) ?? [];
  const hasComparableMatches = storedIds.length >= 2;
  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-brand-100 bg-brand-50/60 p-3 sm:p-4">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-ink">Find a packaged food</p>
            <p className="mt-0.5 text-xs text-muted">Search stored reports and Open Food Facts by name or brand.</p>
          </div>
          <span className="hidden rounded-full bg-white px-2.5 py-1 text-[11px] font-medium text-forest ring-1 ring-brand-100 sm:inline-flex">
            Name or brand
          </span>
        </div>
        <form onSubmit={onSubmit} role="search" className="flex flex-col gap-2 sm:flex-row" aria-label="Search packaged food products">
          <label className="sr-only" htmlFor="product-search">Product name or brand</label>
          <div className="relative min-w-0 flex-1">
            <IconSearch className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-forest" />
          <input
            id="product-search"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="For example: Maggi masala noodles, Horlicks, ragi chips"
            className={`${inputClass} h-14 border-2 border-brand-300 bg-white pl-12 pr-4 text-base shadow-sm placeholder:text-slate-400 focus:border-forest focus:ring-4 focus:ring-brand-100`}
            autoComplete="off"
            disabled={busy}
          />
          </div>
          <button type="submit" className={`${buttonClass.primary} min-h-14 px-6`} disabled={busy}>
          {busy ? <><Spinner className="h-4 w-4" /> Searching…</> : "Search"}
          </button>
        </form>
      </div>

      {error ? <p role="alert" className="rounded-xl bg-[#fdf6ec] px-4 py-3 text-sm text-[#5c3a10]">{error}</p> : null}
      {result?.notes.map((n) => <Note key={n} tone="warn">{n}</Note>)}
      {nothing ? (
        <EmptyState title="No product found">
          Nothing matched “{result.query}”. Try a shorter name or the brand, paste the product link, upload a photo of
          the pack, or enter the details by hand.
        </EmptyState>
      ) : null}

      {result?.stored.length ? (
        <Card>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-ink">Analysed product matches ({result.stored.length})</h3>
              <p className="mt-1 text-xs text-muted">Grades and prices below come from stored product records and dated observations.</p>
            </div>
            {hasComparableMatches ? (
              <Link href={`/compare?ids=${storedIds.join(",")}`} className={`${buttonClass.secondary} !py-2`}>
                Compare matches
              </Link>
            ) : null}
          </div>
          <ul className="mt-3 divide-y divide-line">
            {result.stored.map((p) => (
              <li key={p.product_id} className="flex items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <Link href={`/products/${p.product_id}`} className="font-medium text-ink hover:text-forest hover:underline">
                    {p.brand && !(p.name ?? "").toLowerCase().startsWith(p.brand.toLowerCase()) ? `${p.brand} ` : ""}{p.name ?? "Unnamed product"}
                  </Link>
                  <p className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted">
                    {p.category ? <span>{humanize(p.category)}</span> : <span>Other category</span>}
                    {p.pack_size != null ? <span>{formatNumber(p.pack_size)} {p.pack_unit ?? ""}</span> : null}
                    {p.price_per_100 != null ? <span>{formatInr(p.price_per_100)} per 100 g/ml</span> : null}
                    {p.is_synthetic ? <SyntheticBadge /> : null}
                  </p>
                  <p className="mt-1 text-xs text-slate-600">
                    {p.price_inr != null
                      ? `${formatInr(p.price_inr)}${p.price_retailer ? ` at ${p.price_retailer}` : ""}${p.price_evidence ? ` · ${p.price_evidence} price` : ""}`
                      : "Retailer price not available"}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  {p.grade ? <GradeBadge grade={p.grade} size="sm" /> : <span className="text-xs text-muted">No grade</span>}
                  <div className="flex flex-wrap justify-end gap-2">
                    <Link href={`/products/${p.product_id}`} className={buttonClass.ghost} aria-label={`Open ${p.name ?? "product"}`}>
                      Open <IconArrowRight className="h-4 w-4" />
                    </Link>
                    <Link href={`/products/${p.product_id}/alternatives`} className={`${buttonClass.secondary} !px-3 !py-2`}>
                      Alternatives
                    </Link>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {result?.online.length ? (
        <Card>
          <h3 className="text-sm font-semibold text-ink">Found on Open Food Facts ({result.online.length})</h3>
          <p className="mt-1 text-xs text-muted">{result.attribution} Analysing one stores it and scores it. Retailer prices are not provided by this source.</p>
          <ul className="mt-3 grid gap-3 sm:grid-cols-2">
            {result.online.map((p) => (
              <li key={p.barcode} className="flex gap-3 rounded-2xl border border-line bg-white p-3">
                <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-slate-50">
                  {p.image_url && /^https:\/\//.test(p.image_url) ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={p.image_url} alt="" className="h-full w-full object-contain" referrerPolicy="no-referrer" loading="lazy" />
                  ) : (
                    <IconSearch className="h-6 w-6 text-slate-300" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-ink" title={p.name ?? undefined}>{p.name}</p>
                  <p className="truncate text-xs text-muted">{[p.brand, p.quantity].filter(Boolean).join(" · ") || "Brand not stated"}</p>
                  <div className="mt-2 flex items-center gap-2">
                    {p.stored && p.product_id ? (
                      <Link href={`/products/${p.product_id}`} className={buttonClass.secondary}>Open report</Link>
                    ) : (
                      <button type="button" className={buttonClass.secondary} disabled={importing !== null} onClick={() => analyse(p.barcode)}>
                        {importing === p.barcode ? <><Spinner className="h-4 w-4" /> Analysing…</> : "Analyse"}
                      </button>
                    )}
                    {p.nutriscore_grade && /^[a-e]$/.test(p.nutriscore_grade) ? (
                      <Badge tone="slate">OFF Nutri-Score {p.nutriscore_grade.toUpperCase()}</Badge>
                    ) : null}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}
    </div>
  );
}
