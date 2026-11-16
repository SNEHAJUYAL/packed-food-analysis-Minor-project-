"use client";

import { useMemo, useState } from "react";
import { UncertaintyIndicator } from "./badges";
import { Badge, Card, EmptyState, InfoTip, SectionHeading } from "./ui";
import { formatNumber, humanize } from "@/lib/format";
import { INGREDIENT_STATUS, ingredientStatus } from "@/lib/labels";
import type { IngredientItem, Report } from "@/lib/types";

// Sub-entries that only hold a bracketed percentage (e.g. "62%") are parser annotations of the
// parent's original text, which is already shown, so they are not listed as ingredients.
const PERCENT_ONLY = /^\s*\d+(?:[.,]\d+)?\s*%\s*$/;
const isAnnotation = (i: IngredientItem) => !i.name && PERCENT_ONLY.test(i.text ?? "");

function IngredientRow({ item, depth = 0 }: { item: IngredientItem; depth?: number }) {
  const status = ingredientStatus(item);
  const uncertain = INGREDIENT_STATUS[status]?.uncertain ?? true;
  const subs = (item.sub_ingredients ?? []).filter((s) => !isAnnotation(s));
  const classes = item.classes ?? [];
  const hasPercent = typeof item.percent === "number" && Number.isFinite(item.percent);
  return (
    <li className={`${depth > 0 ? "border-l-2 border-line pl-3" : ""}`}>
      <div className={`rounded-2xl border p-3.5 ${uncertain ? "border-[#f1d2a8] bg-[#fdf8f0]" : "border-line bg-white"}`}>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-sm font-medium text-ink">
              {depth === 0 ? <span className="mr-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-slate-100 px-1 text-[11px] font-semibold text-muted">{item.position}</span> : null}
              <span>{item.text}</span>
              {hasPercent ? <span className="ml-2 text-xs font-normal text-slate-600">({formatNumber(item.percent!)}% declared)</span> : null}
            </p>
            <p className="mt-0.5 text-xs text-muted">
              Normalised: {item.name ? <span className="text-slate-700">{item.name}</span> : <span>not identified</span>}
              {item.term && item.term !== item.name ? <span> (dictionary term: {item.term})</span> : null}
            </p>
          </div>
          <span className="flex items-center gap-1">
            <UncertaintyIndicator status={status} />
            {typeof item.match_score === "number" && uncertain ? (
              <span className="text-xs text-muted">match score {formatNumber(item.match_score, 2)}</span>
            ) : null}
          </span>
        </div>
        {item.functional_category || classes.length ? (
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {item.functional_category ? <Badge tone="blue">{humanize(item.functional_category)}</Badge> : null}
            {classes.map((c) => (
              <Badge key={c} tone="slate">{humanize(c)}</Badge>
            ))}
          </div>
        ) : null}
        {item.explanation ? <p className="mt-2 text-sm text-slate-700">{item.explanation}</p> : null}
        {item.additives && item.additives.length ? (
          <ul className="mt-2 space-y-0.5 text-xs text-slate-700">
            {item.additives.map((a, i) => (
              <li key={i}>
                {a.ins ? `INS ${a.ins}` : "Additive"}
                {a.name ? ` · ${a.name}` : ""}
                {a.functional_class ? ` · ${humanize(a.functional_class)}` : ""}
              </li>
            ))}
          </ul>
        ) : null}
        {item.reference_source ? <p className="mt-2 text-xs text-muted">Reference: {item.reference_source}</p> : null}
      </div>
      {subs.length ? (
        <ul className="mt-2 space-y-2 pl-3" aria-label={`Components of ${item.text}`}>
          {subs.map((s, i) => (
            <IngredientRow key={`${s.position}-${i}`} item={s} depth={depth + 1} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

export function IngredientExplorer({ report }: { report: Report }) {
  const norm = report.ingredients_normalised;
  const items = useMemo(() => norm?.items ?? report.product.ingredients_normalised ?? [], [norm, report.product]);
  const [onlyUncertain, setOnlyUncertain] = useState(false);
  const uncertainCount = items.filter((i) => INGREDIENT_STATUS[ingredientStatus(i)]?.uncertain ?? true).length;
  const shown = onlyUncertain ? items.filter((i) => INGREDIENT_STATUS[ingredientStatus(i)]?.uncertain ?? true) : items;
  const raw = report.product.ingredients_raw?.value;
  const allergens = norm?.allergens ?? report.product.allergens ?? [];
  const advisory = norm?.advisory_allergens ?? [];
  const ins = norm?.additives_ins ?? report.product.additives_ins ?? [];
  const unmatched = norm?.unmatched ?? [];

  return (
    <Card>
      <section aria-labelledby="ingredients-heading">
        <SectionHeading
          id="ingredients-heading"
          title="Ingredient explorer"
          subtitle="In label order. Percentages appear only where the label declares them. Classes describe processing and disclosure, not health effects."
          action={
            uncertainCount > 0 ? (
              <label className="inline-flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={onlyUncertain} onChange={(e) => setOnlyUncertain(e.target.checked)} className="h-4 w-4 accent-brand-600" />
                Only uncertain ({uncertainCount})
              </label>
            ) : null
          }
        />
        {raw ? (
          <details className="mb-4 rounded-2xl border border-line bg-slate-50/60 p-3.5 text-sm">
            <summary className="cursor-pointer font-medium text-ink">Ingredient list as printed</summary>
            <p className="mt-2 text-slate-700">{raw}</p>
          </details>
        ) : null}
        {items.length === 0 ? (
          <EmptyState title="No ingredient list was found on this listing." />
        ) : (
          <ol className="space-y-2" aria-label="Ingredients in label order">
            {shown.map((item, i) => (
              <IngredientRow key={`${item.position}-${i}`} item={item} />
            ))}
          </ol>
        )}

        <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
          <div className={`rounded-2xl border p-3.5 ${allergens.length ? "border-[#f2cbc7] bg-[#fdf3f2]" : "border-line bg-slate-50/60"}`}>
            <dt className="font-semibold text-ink">Allergens detected</dt>
            <dd className="mt-1.5 text-slate-700">
              {allergens.length ? (
                <span className="flex flex-wrap gap-1.5">
                  {allergens.map((a) => <Badge key={a} tone="rose">{humanize(a)}</Badge>)}
                </span>
              ) : "None detected in the text"}
              {allergens.length ? <span className="mt-1.5 block text-xs text-muted">Detected from the ingredient text; always check the pack if you have an allergy.</span> : null}
            </dd>
          </div>
          {advisory.length ? (
            <div>
              <dt className="font-medium text-ink">“May contain” advisories</dt>
              <dd className="text-slate-700">{advisory.map(humanize).join(", ")}</dd>
            </div>
          ) : null}
          <div className="rounded-2xl border border-line bg-slate-50/60 p-3.5">
            <dt className="font-semibold text-ink">INS codes</dt>
            <dd className="mt-1.5 text-slate-700">{ins.length ? <span className="flex flex-wrap gap-1.5">{ins.map((c) => <Badge key={c} tone="blue">INS {c}</Badge>)}</span> : "None declared"}</dd>
          </div>
          {unmatched.length ? (
            <div>
              <dt className="flex items-center gap-1 font-medium text-ink">
                Unmatched text
                <InfoTip label="About unmatched text">Parts of the ingredient list that matched no dictionary entry.</InfoTip>
              </dt>
              <dd className="text-slate-700">{unmatched.join(", ")}</dd>
            </div>
          ) : null}
        </dl>
      </section>
    </Card>
  );
}
