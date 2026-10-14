"use client";

import { EvidenceBadge } from "./badges";
import { Badge, BulletList, Card, SectionHeading } from "./ui";
import { humanize } from "@/lib/format";
import { EVIDENCE_ORDER } from "@/lib/labels";
import type { Evidence, ProductAnalysis } from "@/lib/types";

const PRODUCT_FIELDS = ["name", "brand", "category", "variant", "pack_size", "pack_unit", "price_inr", "ingredients_raw"] as const;

/** Count evidence labels across product fields and nutrients. */
export function evidenceCounts(analysis: ProductAnalysis): Record<string, number> {
  const p = analysis.report.product;
  const counts: Record<string, number> = {};
  const add = (e: Evidence | undefined | null) => {
    if (!e || typeof e !== "object" || !("label" in e)) return;
    counts[e.label] = (counts[e.label] ?? 0) + 1;
  };
  for (const f of PRODUCT_FIELDS) add(p[f] as Evidence | undefined);
  for (const e of Object.values(p.nutrition ?? {})) add(e);
  return counts;
}

export function DataQuality({ analysis }: { analysis: ProductAnalysis }) {
  const { report } = analysis;
  const counts = evidenceCounts(analysis);
  const conflicts = Array.from(new Set([...(analysis.conflicts ?? []), ...(report.product.conflicts ?? [])]));
  const missing = Array.from(new Set([...(analysis.missing_fields ?? []), ...(report.dimensions.transparency.missing ?? [])]));
  const warnings = report.product.warnings ?? [];
  const log = analysis.extraction_log ?? [];
  const fop = report.fop_warning_simulation;

  return (
    <Card>
      <section aria-labelledby="quality-heading">
        <SectionHeading id="quality-heading" title="Evidence and data quality" subtitle="Where each value came from, and what is missing or disputed." />
        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <h3 className="text-sm font-medium text-ink">Evidence status of fields</h3>
            <ul className="mt-2 space-y-1.5">
              {EVIDENCE_ORDER.filter((l) => counts[l]).map((l) => (
                <li key={l} className="flex items-center justify-between gap-2 text-sm">
                  <EvidenceBadge label={l} />
                  <span className="tabular-nums text-slate-700">{counts[l]}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="space-y-4">
            <div>
              <h3 className="text-sm font-medium text-ink">Missing fields</h3>
              {missing.length ? (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {missing.map((m) => (
                    <Badge key={m} tone="slate">{humanize(m)}</Badge>
                  ))}
                </div>
              ) : (
                <p className="mt-1 text-sm text-slate-700">No core fields missing.</p>
              )}
            </div>
            <div>
              <h3 className="text-sm font-medium text-ink">Conflicting values</h3>
              {conflicts.length ? (
                <BulletList className="mt-1" items={conflicts} />
              ) : (
                <p className="mt-1 text-sm text-slate-700">No conflicts between sources.</p>
              )}
            </div>
            {warnings.length ? (
              <div>
                <h3 className="text-sm font-medium text-ink">Extraction notes</h3>
                <BulletList className="mt-1" items={warnings} />
              </div>
            ) : null}
          </div>
        </div>
        {fop ? (
          <p className="mt-4 text-sm text-slate-700">
            <span className="font-medium text-ink">Front-of-pack warning simulation:</span> {fop.status}
            {fop.reason ? ` — ${fop.reason}` : ""}
          </p>
        ) : null}
        {log.length ? (
          <details className="mt-4 text-sm">
            <summary className="cursor-pointer font-medium text-ink">Extraction log ({log.length} steps)</summary>
            <ol className="mt-2 space-y-1">
              {log.map((s, i) => (
                <li key={i} className="flex flex-wrap gap-2">
                  <Badge tone={s.outcome === "ok" ? "teal" : s.outcome === "failed" ? "amber" : "slate"}>{s.outcome}</Badge>
                  <span className="font-medium text-ink">{humanize(s.step)}</span>
                  {s.detail ? <span className="text-slate-600">{s.detail}</span> : null}
                </li>
              ))}
            </ol>
          </details>
        ) : null}
      </section>
    </Card>
  );
}
