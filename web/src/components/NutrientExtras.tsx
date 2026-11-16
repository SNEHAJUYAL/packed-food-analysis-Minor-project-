"use client";

import { Card, Note, SectionHeading } from "./ui";
import { formatNumber } from "@/lib/format";
import type { ProductAnalysis } from "@/lib/types";

const GROUPS = [
  { id: "mineral", title: "Minerals" },
  { id: "vitamin", title: "Vitamins" },
  { id: "other", title: "Other nutrients" },
] as const;

/** Minerals, vitamins and other nutrients the source declares per 100 g/ml. Shown, not scored. */
export function NutrientExtras({ analysis }: { analysis: ProductAnalysis }) {
  const micro = analysis.extras?.micronutrients ?? {};
  const entries = Object.entries(micro);
  const per = analysis.report?.product?.nutrition_basis === "per_100ml" ? "100 ml" : "100 g";
  return (
    <Card>
      <SectionHeading
        id="micronutrients-heading"
        title="Minerals and vitamins"
        subtitle={`What the source declares per ${per}. These are shown for information and are not part of the score.`}
      />
      {entries.length ? (
        <div className="grid gap-4 md:grid-cols-3">
          {GROUPS.map((g) => {
            const rows = entries.filter(([, v]) => v.group === g.id);
            if (!rows.length) return null;
            return (
              <div key={g.id}>
                <h3 className="text-sm font-semibold text-ink">{g.title}</h3>
                <dl className="mt-2 divide-y divide-line rounded-xl border border-line bg-white">
                  {rows.map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between px-3 py-2 text-sm">
                      <dt className="text-slate-700">{v.label}</dt>
                      <dd className="font-medium tabular-nums text-ink">{formatNumber(v.value, 2)} {v.unit}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            );
          })}
        </div>
      ) : (
        <Note>
          The source does not declare any minerals or vitamins for this product, so none are shown. Missing values are
          not treated as zero.
        </Note>
      )}
      {entries.length ? <p className="mt-3 text-xs text-muted">Source: {entries[0][1].source}.</p> : null}
    </Card>
  );
}
