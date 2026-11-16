"use client";

import Link from "next/link";
import { NutrientExtras } from "./NutrientExtras";
import { PricePanel } from "./PricePanel";
import Image from "next/image";
import { useState } from "react";
import type { ReactNode } from "react";
import { AlternativesPanel } from "./AlternativesPanel";
import { AnalysisStatusBadge, EvidenceBadge, SyntheticBadge } from "./badges";
import { ClaimPanel } from "./ClaimPanel";
import { DataQuality } from "./DataQuality";
import { IngredientExplorer } from "./IngredientExplorer";
import { NutritionTable } from "./NutritionTable";
import { ScoreSummary } from "./ScoreSummary";
import { IconAlert, IconImage } from "./icons";
import { Breadcrumbs, Card, ExternalLink, ScoreRing } from "./ui";
import { formatInr, formatNumber, formatTimestamp, hostOf, humanize, safeHref, unitFromBasis } from "@/lib/format";
import type { Evidence, ProductAnalysis } from "@/lib/types";

const SECTIONS = [
  { id: "score", label: "Score" },
  { id: "nutrition", label: "Nutrition" },
  { id: "micronutrients", label: "Minerals" },
  { id: "prices", label: "Prices" },
  { id: "ingredients", label: "Ingredients" },
  { id: "claims", label: "Claims" },
  { id: "quality", label: "Evidence" },
  { id: "alternatives", label: "Alternatives" },
];

function Field({ label, ev, children }: { label: string; ev?: Evidence | null; children?: ReactNode }) {
  const known = ev ? ev.value !== null && ev.value !== undefined && ev.value !== "" : true;
  return (
    <div className="min-w-0 rounded-xl bg-slate-50/70 px-3 py-2.5">
      <dt className="text-[11px] font-medium uppercase tracking-wider text-muted">{label}</dt>
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
    <div role="status" className={`rounded-[var(--radius-card)] border p-4 text-sm sm:p-5 ${partial ? "border-[#f1d2a8] bg-[#fdf6ec] text-[#5c3a10]" : "border-slate-300 bg-slate-100 text-slate-800"}`}>
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
  const imageUrl = p.image_url?.value;
  const [imageFailed, setImageFailed] = useState(false);
  const safeImageUrl = typeof imageUrl === "string" && /^https:\/\//i.test(imageUrl) ? imageUrl : null;

  const overall = report.overall;
  return (
    <article className="space-y-6" aria-labelledby="product-title">
      <Breadcrumbs crumbs={[{ label: "Product explorer", href: "/products" }, { label: name }]} />
      {["saved_page", "photo", "manual"].includes(source?.source_type ?? "") ? (
        <div role="status" className="flex gap-3 rounded-2xl border border-[#f1d2a8] bg-[#fdf6ec] px-4 py-3 text-sm text-[#5c3a10]">
          <IconAlert className="mt-0.5 h-5 w-5 shrink-0 text-[#b87422]" />
          <div>
          <p className="font-semibold">User-supplied evidence · not independently verified</p>
          <p className="mt-1">{source.source_type === "saved_page"
            ? "This saved page was parsed locally as uploaded. Its contents may be incomplete or out of date."
            : source.source_type === "photo"
              ? "OCR or image reading can misread packaging. Check the extracted text against the original image."
              : source.extraction_method === "web-search"
                ? "Ingredients and nutrition were found by web search on the page linked below. They are web-sourced and were not checked against the pack."
                : source.extraction_method === "purchase-invoice"
                  ? "Only the name, brand and pack size are known, from a purchase invoice. Nutrition and ingredients are not available yet."
                  : "These product details were entered manually and were not checked against package evidence."}</p>
          </div>
        </div>
      ) : null}
      <Card>
        <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
        <div>
        {safeImageUrl && !imageFailed ? (
          <div className="overflow-hidden rounded-2xl border border-line bg-white">
            <Image
              src={safeImageUrl}
              alt={`${name} product image`}
              width={960}
              height={540}
              unoptimized
              referrerPolicy="no-referrer"
              className="mx-auto h-60 w-full object-contain p-3"
              priority
              onError={() => setImageFailed(true)}
            />
            <p className="border-t border-line bg-slate-50 px-3 py-2 text-xs text-muted">
              Product image from {p.image_url?.source ?? "the extracted listing"}.
            </p>
          </div>
        ) : (
          <div className="flex h-full min-h-48 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-muted">
            <IconImage className="mb-2 h-8 w-8 text-slate-300" />
            <p>Product image not available from this source.</p>
            {imageUrl ? <p className="mt-1 text-xs">Image source: {p.image_url?.source ?? "product listing"}.</p> : null}
          </div>
        )}
        </div>
        <div className="min-w-0">
        <div className="flex flex-col-reverse gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              {analysis.is_synthetic ? <SyntheticBadge /> : null}
              <AnalysisStatusBadge status={analysis.status} />
              {p.category?.value ? <span className="rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-medium text-forest">{humanize(String(p.category.value))}</span> : null}
            </div>
            <h1 id="product-title" className="mt-3 text-2xl font-bold leading-tight text-ink sm:text-[2rem]">
              {name}
            </h1>
            {p.brand?.value ? <p className="mt-1 text-base text-muted">{p.brand.value}</p> : null}
          </div>
          <a href="#score" className="flex shrink-0 items-center gap-3 self-start rounded-2xl border border-line p-3 transition hover:border-brand-300 hover:bg-brand-50/40">
            <ScoreRing
              score={overall.score}
              size={84}
              label={overall.score !== null && overall.score !== undefined ? `Overall score ${overall.score} out of 100` : "Overall score not computed"}
              caption="overall"
            />
            <span className="pr-1 text-xs text-muted">
              <span className="block font-semibold text-ink">Decision-support score</span>
              {overall.grade ? `Grade ${overall.grade}` : "No grade"} · see breakdown
            </span>
          </a>
        </div>

        <section className="mt-5" aria-labelledby="overview-heading">
          <h2 id="overview-heading" className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">Product overview</h2>
          <dl className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">
            <Field label="Brand" ev={p.brand} />
            <Field label="Category" ev={p.category}>{p.category?.value ? humanize(String(p.category.value)) : null}</Field>
            <Field label="Variant" ev={p.variant ?? { value: null, label: "unknown" }} />
            <Field label="Retailer" ev={p.retailer} />
            <Field label="Product image" ev={p.image_url}>
              {safeImageUrl && !imageFailed ? "Available" : "Not available"}
            </Field>
          </dl>
        </section>
        <section className="mt-5 border-t border-line pt-4" aria-labelledby="commercial-heading">
          <h2 id="commercial-heading" className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">Price and pack details</h2>
          <dl className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">
            <Field label="Pack size" ev={p.pack_size}>
              {formatNumber(p.pack_size?.value ?? null)} {p.pack_unit?.value ?? ""}
            </Field>
            <Field label="Units in pack" ev={p.multipack_count} />
            <Field label="Selling price" ev={p.price_inr}>{formatInr(p.price_inr?.value ?? null)}</Field>
            <Field label="MRP" ev={p.mrp_inr}>{formatInr(p.mrp_inr?.value ?? null)}</Field>
            <Field label="Discount" ev={p.discount_percent}>
              {p.discount_percent?.value != null ? `${formatNumber(p.discount_percent.value)}%` : null}
            </Field>
            <Field label="Availability" ev={p.availability}>
              {p.availability?.value ? humanize(String(p.availability.value).split("/").pop() ?? "") : null}
            </Field>
          <Field label={`Price per 100 ${unit}`} ev={null}>
            {pricePer100 !== null ? (
              <>
                {formatInr(pricePer100)} <EvidenceBadge label="derived" source="price ÷ pack size × 100" />
              </>
            ) : (
              <span className="text-muted">Not available (needs price and pack size)</span>
            )}
          </Field>
          </dl>
        </section>
        <section className="mt-5 border-t border-line pt-4" aria-labelledby="source-heading">
          <h2 id="source-heading" className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">Source and extraction</h2>
          <dl className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">
            <Field label="Last checked" ev={null}>{formatTimestamp(source?.collected_at ?? p.collected_at)}</Field>
            <Field label="Last verified" ev={null}>
              {source?.last_verified_at ? formatTimestamp(source.last_verified_at) : <span className="text-muted">Not verified</span>}
            </Field>
          </dl>
        </section>
        <div className="mt-5 flex flex-col gap-1 border-t border-line pt-4 text-sm text-slate-700 sm:flex-row sm:flex-wrap sm:gap-x-6">
          <span>
            Source:{" "}
            {href ? <ExternalLink href={href}>{hostOf(href)}</ExternalLink> : <span className="text-muted">{humanize(source?.source_type ?? "unknown")}</span>}
          </span>
          {source?.source_reliability ? <span>Reliability: {humanize(source.source_reliability)}</span> : null}
          {source?.extraction_method ? <span>Extraction: {source.extraction_method}</span> : null}
          <span>Methodology v{analysis.methodology_version}</span>
        </div>
        </div>
        </div>
      </Card>

      <StatusBanner analysis={analysis} />

      <nav aria-label="Report sections" className="sticky top-14 z-30 -mx-4 overflow-x-auto border-y border-line bg-canvas/95 px-4 py-2 backdrop-blur sm:mx-0 sm:rounded-2xl sm:border lg:top-3">
        <ul className="flex gap-1 whitespace-nowrap">
          {SECTIONS.filter((s) => showAlternatives || s.id !== "alternatives").map((s) => (
            <li key={s.id}>
              <a href={`#${s.id}`} className="inline-block rounded-xl px-3.5 py-2 text-sm font-medium text-slate-700 transition hover:bg-white hover:text-forest">
                {s.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <div id="score" className="scroll-mt-32"><ScoreSummary report={report} /></div>
      <div id="nutrition" className="scroll-mt-32"><NutritionTable report={report} /></div>
      <div id="micronutrients" className="scroll-mt-32"><NutrientExtras analysis={analysis} /></div>
      <div id="prices" className="scroll-mt-32"><PricePanel productId={analysis.product_id} /></div>
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

      <p className="rounded-[var(--radius-card)] border border-line bg-white p-4 text-sm text-slate-700">
        {report.disclaimer ?? "Consumer decision-support assessment, not a medical or clinical score."}{" "}
        <Link href="/methodology" className="text-brand-700 underline">How scores are calculated</Link>
      </p>
    </article>
  );
}
