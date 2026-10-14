"use client";

import Link from "next/link";
import { useState } from "react";
import { GradeBadge, SyntheticBadge } from "./badges";
import { Badge, Card, EmptyState, ErrorState, ExternalLink, LoadingState, SectionHeading } from "./ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { formatInr, formatNumber, formatTimestamp, hostOf, safeHref } from "@/lib/format";
import { PREFERENCES } from "@/lib/labels";
import type { Alternative, AlternativesResult, Preference } from "@/lib/types";

const PICK_LABELS: { key: "best_match" | "lowest_unit_price" | "best_nutrition"; label: string }[] = [
  { key: "best_match", label: "Best match for this preference" },
  { key: "lowest_unit_price", label: "Lowest price per 100" },
  { key: "best_nutrition", label: "Best nutrition score" },
];

export function PreferenceSelector({ value, onChange }: { value: Preference; onChange: (p: Preference) => void }) {
  return (
    <div role="radiogroup" aria-label="Rank alternatives by" className="flex flex-wrap gap-1.5">
      {PREFERENCES.map((p) => (
        <button
          key={p.id}
          type="button"
          role="radio"
          aria-checked={value === p.id}
          title={p.hint}
          onClick={() => onChange(p.id)}
          className={`rounded-full px-3 py-1.5 text-sm ring-1 ring-inset ${
            value === p.id ? "bg-brand-600 text-white ring-brand-600" : "bg-white text-slate-700 ring-line hover:bg-slate-50"
          }`}
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}

function AlternativeItem({ alt, sourceId }: { alt: Alternative; sourceId: number }) {
  const href = safeHref(alt.source_url);
  return (
    <li className="rounded-xl border border-line p-4">
      <div className="flex items-start gap-3">
        <span className="mt-1 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-700" aria-label={`Rank ${alt.rank}`}>
          {alt.rank}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <Link href={`/products/${alt.product_id}`} className="font-medium text-ink hover:underline">
                {alt.name ?? `Product ${alt.product_id}`}
              </Link>
              {alt.brand ? <p className="text-xs text-muted">{alt.brand}</p> : null}
            </div>
            <div className="flex items-center gap-2">
              {alt.is_synthetic ? <SyntheticBadge /> : null}
              <GradeBadge grade={alt.grade} size="sm" />
              <span className="text-sm font-semibold text-ink">{alt.overall ?? "—"}</span>
            </div>
          </div>
          <p className="mt-2 text-sm text-slate-700">{alt.rationale}</p>
          {alt.matching_attributes?.length ? (
            <div className="mt-2 flex flex-wrap gap-1.5" aria-label="Matching attributes">
              {alt.matching_attributes.map((m) => (
                <Badge key={m} tone="teal">{m}</Badge>
              ))}
            </div>
          ) : null}
          <dl className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600">
            <div><dt className="inline">Nutrition </dt><dd className="inline font-medium">{alt.nutrition ?? "not scored"}</dd></div>
            <div><dt className="inline">Transparency </dt><dd className="inline font-medium">{alt.transparency ?? "not scored"}</dd></div>
            <div><dt className="inline">Price per 100 </dt><dd className="inline font-medium">{formatInr(alt.price_per_100)}</dd></div>
            {alt.similarity !== null && alt.similarity !== undefined ? (
              <div><dt className="inline">Similarity </dt><dd className="inline font-medium">{formatNumber(alt.similarity, 2)}</dd></div>
            ) : null}
          </dl>
          <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted">
            {href ? <ExternalLink href={href}>{hostOf(href)}</ExternalLink> : null}
            {alt.collected_at ? <span>checked {formatTimestamp(alt.collected_at)}</span> : null}
            <Link href={`/compare?ids=${sourceId},${alt.product_id}`} className="text-brand-700 hover:underline">
              Compare side by side
            </Link>
          </p>
        </div>
      </div>
    </li>
  );
}

export function AlternativesPanel({ productId, initialPreference = "balanced" }: { productId: number; initialPreference?: Preference }) {
  const [preference, setPreference] = useState<Preference>(initialPreference);
  const [state] = useApi((signal) => api.alternatives(productId, preference, 5, signal), [productId, preference]);

  const nameOf = (id: number, data: AlternativesResult) => {
    const a = data.alternatives.find((x) => x.product_id === id);
    return a?.name ?? `Product ${id}`;
  };

  return (
    <Card>
      <section aria-labelledby="alternatives-heading">
        <SectionHeading
          id="alternatives-heading"
          title="Alternatives"
          subtitle="Only stored products in the same category and nutrition basis are considered. Nothing is suggested beyond what the analysis returns."
          action={<PreferenceSelector value={preference} onChange={setPreference} />}
        />
        {state.kind === "loading" ? <LoadingState label="Finding alternatives…" /> : null}
        {state.kind === "error" ? <ErrorState title="Alternatives unavailable" message={state.error.message} code={state.error.code} /> : null}
        {state.kind === "ready" ? (
          <div className="space-y-4">
            <p className="text-xs text-muted">
              {state.data.eligible_count} eligible stored product{state.data.eligible_count === 1 ? "" : "s"} considered · methodology v
              {state.data.methodology_version}
            </p>
            {state.data.message ? (
              <p role="status" className="rounded-xl bg-slate-50 p-3 text-sm text-slate-700">
                {state.data.message}
              </p>
            ) : null}
            {state.data.picks && PICK_LABELS.some((p) => state.data.picks?.[p.key]) ? (
              <div className="grid gap-3 sm:grid-cols-3">
                {PICK_LABELS.map(({ key, label }) => {
                  const pick = state.data.picks?.[key];
                  return (
                    <div key={key} className="rounded-xl bg-brand-50 p-3">
                      <p className="text-xs font-medium uppercase tracking-wide text-brand-700">{label}</p>
                      {pick ? (
                        <>
                          <Link href={`/products/${pick.product_id}`} className="mt-1 block font-medium text-ink hover:underline">
                            {pick.name ?? nameOf(pick.product_id, state.data)}
                          </Link>
                          {pick.is_synthetic ? <div className="mt-1"><SyntheticBadge /></div> : null}
                          {pick.reason || pick.rationale ? (
                            <p className="mt-1 text-xs text-slate-700">{pick.reason ?? pick.rationale}</p>
                          ) : null}
                        </>
                      ) : (
                        <p className="mt-1 text-sm text-muted">No pick</p>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : null}
            {state.data.alternatives.length ? (
              <ol className="space-y-3" aria-label="Ranked alternatives">
                {state.data.alternatives.map((a) => (
                  <AlternativeItem key={a.product_id} alt={a} sourceId={productId} />
                ))}
              </ol>
            ) : !state.data.message ? (
              <EmptyState title="No suitable alternative is stored for this product yet." />
            ) : null}
          </div>
        ) : null}
      </section>
    </Card>
  );
}
