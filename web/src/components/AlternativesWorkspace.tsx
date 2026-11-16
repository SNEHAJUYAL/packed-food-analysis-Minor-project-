"use client";

import Link from "next/link";
import { AlternativesPanel } from "./AlternativesPanel";
import { AnalysisStatusBadge, GradeBadge, SyntheticBadge } from "./badges";
import { ErrorState, LoadingState, Note, ScoreRing, buttonClass } from "./ui";
import { api } from "@/lib/api";
import { basisLabel, formatInr, formatNumber, humanize, nutrientUnit } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import type { ProductAnalysis } from "@/lib/types";

const KEY_NUTRIENTS = ["total_sugars", "saturated_fat", "sodium", "fibre", "protein"];

/** The product being replaced: identity, score and the nutrients alternatives are judged against. */
function OriginalProduct({ analysis }: { analysis: ProductAnalysis }) {
  const { report } = analysis;
  const p = report.product;
  const basis = basisLabel(p.nutrition_basis);
  return (
    <section aria-labelledby="original-heading" className="rounded-[var(--radius-card)] border border-line bg-white p-5 shadow-[var(--shadow-card)] sm:p-6">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">Original product</p>
      <div className="mt-3 flex flex-wrap items-center gap-4">
        <ScoreRing score={report.overall.score} size={72} stroke={7} label={report.overall.score !== null && report.overall.score !== undefined ? `Overall score ${report.overall.score} out of 100` : "Overall score not computed"} />
        <GradeBadge grade={report.overall.grade} />
        <div className="min-w-0 flex-1">
          <h2 id="original-heading" className="text-lg font-semibold text-ink">{p.name?.value || "Unnamed product"}</h2>
          <p className="text-sm text-muted">{[p.brand?.value, p.category?.value ? humanize(String(p.category.value)) : null].filter(Boolean).join(" · ")}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {analysis.is_synthetic ? <SyntheticBadge /> : null}
            <AnalysisStatusBadge status={analysis.status} />
          </div>
        </div>
        <Link href={`/products/${analysis.product_id}`} className={buttonClass.secondary}>Full report</Link>
      </div>
      <dl className="mt-5 grid grid-cols-2 gap-3 border-t border-line pt-4 sm:grid-cols-3 lg:grid-cols-6">
        {KEY_NUTRIENTS.map((k) => {
          const v = p.nutrition?.[k]?.value;
          return (
            <div key={k}>
              <dt className="text-xs text-muted">{humanize(k)}</dt>
              <dd className="mt-0.5 text-sm font-semibold tabular-nums text-ink">
                {v === null || v === undefined ? <span className="font-normal text-muted">Not found</span> : `${formatNumber(v)} ${nutrientUnit(k)}`}
              </dd>
            </div>
          );
        })}
        <div>
          <dt className="text-xs text-muted">Price per 100</dt>
          <dd className="mt-0.5 text-sm font-semibold tabular-nums text-ink">{formatInr(report.dimensions.value?.price_per_100 ?? null)}</dd>
        </div>
      </dl>
      <p className="mt-3 text-xs text-muted">Nutrients {basis}.</p>
    </section>
  );
}

export function AlternativesWorkspace({ productId }: { productId: number }) {
  const [state, retry] = useApi((signal) => api.getProduct(productId, signal), [productId]);
  return (
    <div className="space-y-6">
      {state.kind === "loading" ? <LoadingState label="Loading the original product…" lines={2} /> : null}
      {state.kind === "error" ? (
        <ErrorState title={state.error.status === 404 ? "Product not found" : "Could not load this product"} message={state.error.message} code={state.error.code}
          action={<span className="flex gap-4">{state.error.status !== 404 ? <button type="button" className="font-medium underline" onClick={retry}>Try again</button> : null}<Link className="font-medium underline" href="/alternatives">Choose another product</Link></span>} />
      ) : null}
      {state.kind === "ready" ? <OriginalProduct analysis={state.data} /> : null}
      <Note>
        Suggestions are stored products in the same category and nutrition basis that have an overall score and beat this
        product on the preference you choose (a lower unit price must also come with an overall score that is no worse).
        Text similarity over name, brand, category and ingredients breaks ties. A higher score is an indicator from the
        listing, not a medical judgement; open each report before deciding.
      </Note>
      <AlternativesPanel productId={productId} />
    </div>
  );
}
