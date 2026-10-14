"use client";

import { EvidenceBadge, TrafficLight } from "./badges";
import { Card, InfoTip, SectionHeading } from "./ui";
import { NUTRIENT_ORDER, basisLabel, formatNumber, humanize, nutrientUnit } from "@/lib/format";
import type { Report } from "@/lib/types";

/** "70 g" -> "per 70 g"; text that already says "per ..." is kept. */
function basisText(t: string): string {
  return /^\s*per\b/i.test(t) ? t : `per ${t}`;
}

export function NutritionTable({ report }: { report: Report }) {
  const product = report.product;
  const dim = report.dimensions.nutrition;
  const nutrition = product.nutrition ?? {};
  const original = product.nutrition_original ?? {};
  const keys = [
    ...NUTRIENT_ORDER.filter((k) => k in nutrition || (dim.facts && k in dim.facts)),
    ...Object.keys(nutrition).filter((k) => !NUTRIENT_ORDER.includes(k)),
  ];
  const hasOriginal = Object.keys(original).length > 0;
  // Printed values with no normalised counterpart (e.g. salt, from which sodium is derived).
  const originalOnly = Object.keys(original).filter((k) => !keys.includes(k));
  const basis = basisLabel(product.nutrition_basis ?? dim.basis);

  return (
    <Card>
      <section aria-labelledby="nutrition-heading">
        <SectionHeading
          id="nutrition-heading"
          title={`Nutrition ${basis}`}
          subtitle={
            product.nutrition_basis
              ? "Values normalised to a consistent basis. Missing values are shown as not found, never as zero."
              : "No stated nutrition basis was found, so values could not be normalised."
          }
        />
        {keys.length === 0 ? (
          <p className="text-sm text-muted">No nutrition information was found on this listing.</p>
        ) : (
          <div className="-mx-4 overflow-x-auto sm:mx-0">
            <table className="w-full min-w-[560px] text-left text-sm">
              <caption className="sr-only">Nutrition {basis} with traffic lights and evidence labels</caption>
              <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th scope="col" className="px-4 py-2 font-medium">Nutrient</th>
                  <th scope="col" className="px-4 py-2 font-medium">{basis}</th>
                  <th scope="col" className="px-4 py-2 font-medium">
                    <span className="inline-flex items-center gap-1">
                      Light
                      <InfoTip label="About traffic lights">
                        Green, amber and red compare the value with sourced benchmarks (see Methodology). Nutrients without a
                        sourced benchmark have no light.
                      </InfoTip>
                    </span>
                  </th>
                  <th scope="col" className="px-4 py-2 font-medium">Evidence</th>
                  {hasOriginal ? <th scope="col" className="px-4 py-2 font-medium">As printed</th> : null}
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {keys.map((k) => {
                  const ev = nutrition[k];
                  const fact = dim.facts?.[k];
                  const value = ev?.value ?? fact?.value ?? null;
                  const label = ev?.label ?? fact?.evidence ?? "unknown";
                  const unit = fact?.unit ?? nutrientUnit(k);
                  const sub = dim.subscores?.[k];
                  const orig = original[k];
                  return (
                    <tr key={k}>
                      <th scope="row" className="px-4 py-2 font-medium text-ink">
                        <span className="inline-flex items-center gap-1">
                          {humanize(k)}
                          {sub?.benchmark_source || sub?.reason ? (
                            <InfoTip label={`Benchmark for ${humanize(k)}`}>
                              {sub.subscore !== null && sub.subscore !== undefined ? (
                                <span className="block">Sub-score {formatNumber(sub.subscore, 0)} / 100</span>
                              ) : null}
                              {sub.reason ? <span className="block">Not scored: {sub.reason}</span> : null}
                              {sub.benchmark_source ? <span className="mt-1 block text-slate-300">{sub.benchmark_source}</span> : null}
                            </InfoTip>
                          ) : null}
                        </span>
                      </th>
                      <td className="px-4 py-2 tabular-nums">
                        {value === null || value === undefined ? (
                          <span className="text-muted">Not found</span>
                        ) : (
                          `${formatNumber(value)} ${unit}`
                        )}
                      </td>
                      <td className="px-4 py-2">
                        <TrafficLight light={dim.traffic_lights?.[k]} />
                      </td>
                      <td className="px-4 py-2">
                        <EvidenceBadge label={label} source={ev?.source} note={ev?.note} />
                      </td>
                      {hasOriginal ? (
                        <td className="px-4 py-2 text-xs text-slate-600">
                          {orig && orig.value !== null && orig.value !== undefined && orig.value !== "" ? (
                            <>
                              <span className="block text-sm text-ink">{String(orig.value)}</span>
                              {orig.basis_text ? <span className="block">{basisText(orig.basis_text)}</span> : null}
                              {orig.source ? <span className="block text-muted">from {orig.source}</span> : null}
                            </>
                          ) : (
                            <span className="text-muted">—</span>
                          )}
                        </td>
                      ) : null}
                    </tr>
                  );
                })}
                {originalOnly.map((k) => {
                  const orig = original[k];
                  return (
                    <tr key={`orig-${k}`}>
                      <th scope="row" className="px-4 py-2 font-medium text-ink">{humanize(k)}</th>
                      <td className="px-4 py-2 text-xs text-muted">Printed only (not a scored nutrient)</td>
                      <td className="px-4 py-2" />
                      <td className="px-4 py-2" />
                      <td className="px-4 py-2 text-xs text-slate-600">
                        <span className="block text-sm text-ink">{String(orig.value ?? "—")}</span>
                        {orig.basis_text ? <span className="block">{basisText(orig.basis_text)}</span> : null}
                        {orig.source ? <span className="block text-muted">from {orig.source}</span> : null}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </Card>
  );
}
