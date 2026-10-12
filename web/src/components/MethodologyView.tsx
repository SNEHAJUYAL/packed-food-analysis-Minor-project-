"use client";

import { EvidenceBadge, ClaimStatusBadge } from "./badges";
import { Card, ErrorState, ExternalLink, LoadingState, SectionHeading } from "./ui";
import { api } from "@/lib/api";
import { formatPercent, humanize, safeHref } from "@/lib/format";
import { CLAIM_STATUSES, EVIDENCE_LABELS } from "@/lib/labels";
import { useApi } from "@/lib/useApi";
import type { Methodology, Row } from "@/lib/types";

const THRESHOLD_COLUMNS = ["parameter", "category", "basis", "direction", "green_bound", "red_bound", "unit", "source", "status", "date_checked"];
const CLAIM_COLUMNS = ["claim_label", "nutrient", "condition", "threshold_solid", "threshold_liquid", "threshold_per_100kcal", "unit", "regulation", "clause", "source_url", "status", "date_checked"];
const CATEGORY_WEIGHT_COLUMNS = ["category", "nutrient", "weight", "source", "notes"];

function pickColumns(rows: Row[], preferred: string[]): string[] {
  const keys = new Set<string>();
  rows.forEach((r) => Object.keys(r).forEach((k) => keys.add(k)));
  const chosen = preferred.filter((k) => keys.has(k));
  return chosen.length ? chosen : Array.from(keys).filter((k) => k !== "patterns");
}

function Cell({ value }: { value: unknown }) {
  if (value === null || value === undefined || value === "") return <span className="text-muted">—</span>;
  if (typeof value === "string") {
    const href = /^https?:\/\//.test(value) ? safeHref(value) : null;
    if (href) return <ExternalLink href={href}>Source</ExternalLink>;
    return <>{value}</>;
  }
  if (typeof value === "number" || typeof value === "boolean") return <>{String(value)}</>;
  return <code className="text-xs">{JSON.stringify(value)}</code>;
}

export function DataTable({ rows, preferred, caption }: { rows: Row[] | undefined; preferred: string[]; caption: string }) {
  if (!rows || rows.length === 0) return <p className="text-sm text-muted">Not provided by the API.</p>;
  const cols = pickColumns(rows, preferred);
  return (
    <div className="-mx-4 overflow-x-auto sm:mx-0">
      <table className="w-full min-w-[720px] text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
          <tr>
            {cols.map((c) => (
              <th key={c} scope="col" className="px-3 py-2 font-medium">{humanize(c)}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line align-top">
          {rows.map((r, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c} className="max-w-xs px-3 py-2 text-slate-700">
                  <Cell value={r[c]} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function gradeBands(m: Methodology): { grade: string; min: number }[] {
  if (Array.isArray(m.grade_bands)) return m.grade_bands;
  return Object.entries(m.grade_bands ?? {})
    .filter(([, v]) => typeof v === "number")
    .map(([grade, min]) => ({ grade, min: min as number }))
    .sort((a, b) => b.min - a.min);
}

const MISSING_DATA_FALLBACK = [
  "A missing value is stored as unknown, never as zero.",
  "Nutrients without a value or without a sourced benchmark are left out of the nutrition score, and the coverage is reported.",
  "The nutrition score needs a minimum share of the category weight to be known; below that, the product is not scored overall.",
  "Claims that cannot be checked are marked “cannot be verified from available information”.",
  "Value for money is only scored when other stored products in the same category give a comparison set.",
];

const FRESHNESS_FALLBACK = [
  "Every report shows when the page was collected (“last checked”) and whether it was later verified.",
  "Reference tables show the date their sources were last checked.",
];

const asList = (v: string[] | string | null | undefined): string[] | null =>
  Array.isArray(v) ? (v.length ? v : null) : typeof v === "string" && v ? [v] : null;

export function MethodologyContent({ m }: { m: Methodology }) {
  const missingData = asList(m.missing_data) ?? MISSING_DATA_FALLBACK;
  const freshness = [...(asList(m.freshness) ?? FRESHNESS_FALLBACK), "Prices and recipes change; check the current pack before deciding."];
  const bands = gradeBands(m);
  const evidence = m.evidence_labels && Object.keys(m.evidence_labels).length ? m.evidence_labels : Object.fromEntries(Object.entries(EVIDENCE_LABELS).map(([k, v]) => [k, v.meaning]));
  const statuses = m.claim_statuses && Object.keys(m.claim_statuses).length ? m.claim_statuses : Object.fromEntries(Object.entries(CLAIM_STATUSES).map(([k, v]) => [k, v.meaning]));

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted">
        Methodology version <span className="font-medium text-ink">{m.version}</span>. A prototype: weights and curve
        parameters are design choices still to be calibrated, not validated science.
      </p>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <SectionHeading title="Dimension weights" />
          <ul className="space-y-2 text-sm">
            {Object.entries(m.dimension_weights ?? {}).map(([k, w]) => (
              <li key={k} className="grid grid-cols-[110px_1fr_48px] items-center gap-2">
                <span className="text-slate-700">{humanize(k)}</span>
                <span className="h-2 rounded-full bg-slate-100"><span className="block h-2 rounded-full bg-brand-500" style={{ width: `${Math.min(w * 100, 100)}%` }} /></span>
                <span className="text-right tabular-nums">{formatPercent(w)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-muted">
            When a dimension cannot be scored it is left out and the remaining weights are renormalised. No overall score is
            given without a nutrition score.
          </p>
        </Card>
        <Card>
          <SectionHeading title="Grade bands" />
          {bands.length ? (
            <table className="w-full text-sm">
              <caption className="sr-only">Grade bands</caption>
              <thead className="text-xs uppercase tracking-wide text-muted"><tr><th scope="col" className="py-1 text-left font-medium">Grade</th><th scope="col" className="py-1 text-left font-medium">Overall score</th></tr></thead>
              <tbody className="divide-y divide-line">
                {bands.map((b, i) => (
                  <tr key={b.grade}>
                    <td className="py-1.5 font-semibold">{b.grade}</td>
                    <td className="py-1.5 tabular-nums">{i === 0 ? `${b.min} and above` : `${b.min} to ${bands[i - 1].min - 1}`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-muted">Not provided by the API.</p>
          )}
        </Card>
      </div>

      <Card>
        <SectionHeading title="Nutrient thresholds" subtitle="Benchmarks behind the traffic lights and nutrition sub-scores, with their sources." />
        <DataTable rows={m.thresholds} preferred={THRESHOLD_COLUMNS} caption="Nutrient thresholds and sources" />
      </Card>

      <Card>
        <SectionHeading title="Claim rules" subtitle="Regulatory conditions used to check printed claims, with the regulation and clause." />
        <DataTable rows={m.claim_rules} preferred={CLAIM_COLUMNS} caption="Claim rules" />
      </Card>

      {m.category_weights?.length ? (
        <Card>
          <SectionHeading title="Category nutrient weights" />
          <DataTable rows={m.category_weights} preferred={CATEGORY_WEIGHT_COLUMNS} caption="Category nutrient weights" />
        </Card>
      ) : null}

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <SectionHeading title="Evidence labels" />
          <dl className="space-y-3 text-sm">
            {Object.entries(evidence).map(([k, v]) => (
              <div key={k}>
                <dt><EvidenceBadge label={k} /></dt>
                <dd className="mt-1 text-slate-700">{v}</dd>
              </div>
            ))}
          </dl>
        </Card>
        <Card>
          <SectionHeading title="Claim statuses" />
          <dl className="space-y-3 text-sm">
            {Object.entries(statuses).map(([k, v]) => (
              <div key={k}>
                <dt><ClaimStatusBadge status={k} /></dt>
                <dd className="mt-1 text-slate-700">{v}</dd>
              </div>
            ))}
          </dl>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <SectionHeading title="Missing data" />
          <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-700">
            {missingData.map((t, i) => <li key={i}>{t}</li>)}
          </ul>
        </Card>
        <Card>
          <SectionHeading title="Freshness" />
          <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-700">
            {freshness.map((t, i) => <li key={i}>{t}</li>)}
          </ul>
        </Card>
      </div>

      <Card>
        <SectionHeading title="Data sources and licensing" />
        {m.data_sources?.length ? (
          <ul className="space-y-2 text-sm">
            {m.data_sources.map((s) => (
              <li key={s.name}>
                <span className="font-medium text-ink">{s.name}</span>
                {s.licence ? <span className="text-slate-700"> · {s.licence}</span> : null}
                {s.use ? <span className="block text-slate-600">{s.use}</span> : null}
              </li>
            ))}
          </ul>
        ) : null}
        <p className="mt-3 text-sm text-slate-700">
          Open Food Facts data is available under the Open Database License (ODbL); it is credited here and any derived
          database is shared alike. Product pages are fetched only where robots.txt allows.{" "}
          <ExternalLink href="https://world.openfoodfacts.org/terms-of-use">Open Food Facts terms</ExternalLink>
        </p>
      </Card>

      {m.limitations?.length ? (
        <Card>
          <SectionHeading title="Limitations" />
          <ul className="list-disc space-y-1.5 pl-5 text-sm text-slate-700">
            {m.limitations.map((l, i) => <li key={i}>{l}</li>)}
          </ul>
        </Card>
      ) : null}

      {m.scoring ? (
        <details className="rounded-2xl border border-line bg-white p-4 text-sm">
          <summary className="cursor-pointer font-medium text-ink">Full scoring configuration</summary>
          <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-50 p-3 text-xs">{JSON.stringify(m.scoring, null, 2)}</pre>
        </details>
      ) : null}
    </div>
  );
}

export function MethodologyView() {
  const [state, retry] = useApi((signal) => api.methodology(signal), []);
  if (state.kind === "loading") return <LoadingState label="Loading methodology…" />;
  if (state.kind === "error") {
    return (
      <ErrorState
        title="Could not load the methodology"
        message={state.error.message}
        code={state.error.code}
        action={<button type="button" className="underline" onClick={retry}>Try again</button>}
      />
    );
  }
  return <MethodologyContent m={state.data} />;
}
