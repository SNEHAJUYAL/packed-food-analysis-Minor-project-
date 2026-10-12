"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { AlternativesPanel } from "./AlternativesPanel";
import { AnalysisStatusBadge, EvidenceBadge, SyntheticBadge } from "./badges";
import { ClaimPanel } from "./ClaimPanel";
import { DataQuality } from "./DataQuality";
import { IngredientExplorer } from "./IngredientExplorer";
import { NutritionTable } from "./NutritionTable";
import { ScoreSummary } from "./ScoreSummary";
import { Card, ExternalLink } from "./ui";
import { formatInr, formatNumber, formatTimestamp, hostOf, humanize, safeHref, unitFromBasis } from "@/lib/format";
import type { Evidence, ProductAnalysis } from "@/lib/types";

const SECTIONS = [
  { id: "score", label: "Score" },
  { id: "nutrition", label: "Nutrition" },
  { id: "ingredients", label: "Ingredients" },
  { id: "claims", label: "Claims" },
  { id: "quality", label: "Evidence" },
  { id: "alternatives", label: "Alternatives" },
];

function Field({ label, ev, children }: { label: string; ev?: Evidence | null; children?: ReactNode }) {
  const known = ev ? ev.value !== null && ev.value !== undefined && ev.value !== "" : true;
  return (
    <div className="min-w-0">
      <dt className="text-xs uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-0.5 flex flex-wrap items-center gap-1.5 text-sm text-ink">
        {known ? children ?? String(ev?.value) : <span className="text-muted">Not found</span>}
        {ev ? <EvidenceBadge label={ev.label} source={ev.source} note={ev.note} /> : null}
      </dd>
    </div>
  );
}

export function StatusBanner({ analysis }: { analysis: ProductAnalysis }) {
  if (analysis.status === "complete") return null;
  const partial = analysis.status === "partial";
  const missing = analysis.missing_fields ?? [];
  return (
    <div role="status" className={`rounded-2xl border p-4 text-sm ${partial ? "border-amber-200 bg-amber-50 text-amber-950" : "border-slate-300 bg-slate-100 text-slate-800"}`}>
      <p className="font-semibold">{partial ? "Partial data" : "Insufficient data"}</p>
      <p className="mt-1">
        {partial
          ? "Some information was not found on the listing. Scores use only what is known, unscored parts are left out rather than counted as zero, and the remaining weights are renormalised."
          : "Too little information was found to score this product reliably. What was found is shown below with its evidence label."}
      </p>
      {missing.length ? <p className="mt-1">Missing: {missing.map(humanize).join(", ")}.</p> : null}
    </div>
  );
}

export function ReportView({ analysis, showAlternatives = true }: { analysis: ProductAnalysis; showAlternatives?: boolean }) {
  const { report, source } = analysis;
  const p = report.product;
  const href = safeHref(source?.source_url ?? p.source_url);
  const unit = unitFromBasis(p.nutrition_basis);
  const pricePer100 = report.dimensions.value?.price_per_100 ?? null;
  const name = p.name?.value || "Unnamed product";

  return (
    <article className="space-y-6" aria-labelledby="product-title">
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          {analysis.is_synthetic ? <SyntheticBadge /> : null}
          <AnalysisStatusBadge status={analysis.status} />
          {p.category?.value ? <span className="text-xs text-muted">{humanize(String(p.category.value))}</span> : null}
        </div>
        <h1 id="product-title" className="mt-2 text-2xl font-semibold text-ink sm:text-3xl">
          {name}
        </h1>
        {p.brand?.value ? <p className="mt-1 text-muted">{p.brand.value}</p> : null}

        <dl className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Brand" ev={p.brand} />
          <Field label="Category" ev={p.category}>{p.category?.value ? humanize(String(p.category.value)) : null}</Field>
          <Field label="Variant" ev={p.variant ?? { value: null, label: "unknown" }} />
          <Field label="Pack size" ev={p.pack_size}>
            {formatNumber(p.pack_size?.value ?? null)} {p.pack_unit?.value ?? ""}
          </Field>
          <Field label="Price" ev={p.price_inr}>{formatInr(p.price_inr?.value ?? null)}</Field>
          <Field label={`Price per 100 ${unit}`} ev={null}>
            {pricePer100 !== null ? (
              <>
                {formatInr(pricePer100)} <EvidenceBadge label="derived" source="price ÷ pack size × 100" />
              </>
            ) : (
              <span className="text-muted">Not available (needs price and pack size)</span>
            )}
          </Field>
          <Field label="Last checked" ev={null}>{formatTimestamp(source?.collected_at ?? p.collected_at)}</Field>
          <Field label="Last verified" ev={null}>
            {source?.last_verified_at ? formatTimestamp(source.last_verified_at) : <span className="text-muted">Not verified</span>}
          </Field>
        </dl>
        <div className="mt-5 flex flex-col gap-1 border-t border-line pt-4 text-sm text-slate-700 sm:flex-row sm:flex-wrap sm:gap-x-6">
          <span>
            Source:{" "}
            {href ? <ExternalLink href={href}>{hostOf(href)}</ExternalLink> : <span className="text-muted">{humanize(source?.source_type ?? "unknown")}</span>}
          </span>
          {source?.source_reliability ? <span>Reliability: {humanize(source.source_reliability)}</span> : null}
          {source?.extraction_method ? <span>Extraction: {source.extraction_method}</span> : null}
          <span>Methodology v{analysis.methodology_version}</span>
        </div>
      </Card>

      <StatusBanner analysis={analysis} />

      <nav aria-label="Report sections" className="sticky top-[57px] z-30 -mx-4 overflow-x-auto border-y border-line bg-canvas/95 px-4 py-2 backdrop-blur sm:mx-0 sm:rounded-xl sm:border">
        <ul className="flex gap-1 whitespace-nowrap">
          {SECTIONS.filter((s) => showAlternatives || s.id !== "alternatives").map((s) => (
            <li key={s.id}>
              <a href={`#${s.id}`} className="rounded-lg px-3 py-1.5 text-sm text-slate-700 hover:bg-white">
                {s.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <div id="score" className="scroll-mt-32"><ScoreSummary report={report} /></div>
      <div id="nutrition" className="scroll-mt-32"><NutritionTable report={report} /></div>
      <div id="ingredients" className="scroll-mt-32"><IngredientExplorer report={report} /></div>
      <div id="claims" className="scroll-mt-32"><ClaimPanel report={report} /></div>
      <div id="quality" className="scroll-mt-32"><DataQuality analysis={analysis} /></div>
      {showAlternatives ? (
        <div id="alternatives" className="scroll-mt-32">
          <AlternativesPanel productId={analysis.product_id} />
          <p className="mt-2 text-right text-sm">
            <Link className="text-brand-700 hover:underline" href={`/products/${analysis.product_id}/alternatives`}>
              Open alternatives on their own page
            </Link>
          </p>
        </div>
      ) : null}

      <p className="rounded-2xl bg-slate-100 p-4 text-sm text-slate-700">
        {report.disclaimer ?? "Consumer decision-support assessment, not a medical or clinical score."}{" "}
        <Link href="/methodology" className="text-brand-700 underline">How scores are calculated</Link>
      </p>
    </article>
  );
}
