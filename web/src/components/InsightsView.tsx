"use client";

import Link from "next/link";
import { ChartCard, CountBarChart, ShareBar } from "./charts";
import { CoverageNote, GRADE_COLOR } from "./DashboardView";
import { Badge, ErrorState, LoadingState, Note, PageHeader, scoreColor } from "./ui";
import { loadCatalogStats, type CatalogStats } from "@/lib/catalog";
import { useApi } from "@/lib/useApi";

/**
 * Snapshot of reports/evaluation_results.json (methodology v0.1.0). These evaluate deterministic
 * extractors and rules on small labelled sets; they are not accuracy figures for a trained model.
 */
const EVALUATION_SNAPSHOT: { component: string; metric: string; data: string; status: "run" | "not run" }[] = [
  { component: "Page extraction (JSON-LD + HTML)", metric: "Precision 1.00 · recall 0.81 (60 fields)", data: "4 synthetic test pages, hand-labelled", status: "run" },
  { component: "OCR (Tesseract)", metric: "Character error rate 0.8%", data: "1 rendered label fixture, not a camera photo", status: "run" },
  { component: "Ingredient classification (dictionary rules)", metric: "F1 1.00", data: "57 team-labelled ingredient phrases", status: "run" },
  { component: "Claim checks (FSSAI rules)", metric: "Status accuracy 100%", data: "22 hand-worked regulatory cases", status: "run" },
  { component: "Product matching (fuzzy name match)", metric: "Correct match 98.9%", data: "90 perturbed queries over 40 synthetic records", status: "run" },
  { component: "Nutrition score vs Nutri-Score", metric: "Spearman ρ 0.76", data: "339 Open Food Facts India products", status: "run" },
  { component: "Alternative recommendations", metric: "Not measured", data: "Needs relevance judgements (Precision@3, NDCG@5)", status: "not run" },
  { component: "Expert ranking agreement", metric: "Not measured", data: "No expert rankings collected yet", status: "not run" },
];

const NOT_AVAILABLE = [
  { name: "Sugar and sodium distributions", why: "Nutrient values are returned per product report, not in the product list." },
  { name: "Ingredient, additive and allergen frequency", why: "Ingredient analysis is per product; there is no catalogue-wide aggregate endpoint." },
  { name: "Claim verification distribution", why: "Claim results are part of each product report only." },
];

function InsightsContent({ stats }: { stats: CatalogStats }) {
  const missing = stats.statuses;
  return (
    <div className="space-y-6">
      <CoverageNote stats={stats} />
      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Overall score distribution" subtitle={`${stats.scored} scored products, in 10-point bands (0–100)`}>
          {stats.scored ? (
            <CountBarChart rows={stats.scoreBins} layout="vertical" xLabel="Overall score" colorFor={(r) => scoreColor(Number(r.key) + 5)} />
          ) : (
            <p className="text-sm text-muted">No product has an overall score yet.</p>
          )}
        </ChartCard>
        <ChartCard title="Grade distribution" subtitle="Grades follow the methodology's bands; ungraded means not enough data">
          <CountBarChart rows={stats.grades} layout="vertical" colorFor={(r) => GRADE_COLOR[r.key] ?? "#234b39"} />
        </ChartCard>
        <ChartCard title="Missing nutritional information" subtitle="Analysis status per product: how complete the source data was">
          <CountBarChart rows={missing} />
          <p className="mt-2 text-xs text-muted">Partial and insufficient records keep unknown values as unknown; they are never filled in as zero.</p>
        </ChartCard>
        <ChartCard title="Products by category" subtitle="Stored products per category">
          {stats.categories.length ? <CountBarChart rows={stats.categories} /> : <p className="text-sm text-muted">No categories reported.</p>}
        </ChartCard>
        <ChartCard title="Real versus synthetic records" subtitle="Synthetic demo records exist to show value-for-money and are labelled everywhere">
          <ShareBar parts={[
            { label: "Real records", count: stats.real, color: "#234b39" },
            { label: "Synthetic demo records", count: stats.synthetic, color: "#a9c08f" },
          ]} />
        </ChartCard>
        <ChartCard title="Unit price coverage" subtitle="Price per 100 g/ml needs both a price and a pack size">
          <ShareBar parts={[
            { label: "With a unit price", count: stats.withUnitPrice, color: "#234b39" },
            { label: "No price or pack size", count: stats.loaded - stats.withUnitPrice, color: "#cdd3ca" },
          ]} />
        </ChartCard>
      </div>

      <ChartCard title="Component evaluation snapshot" subtitle="From reports/evaluation_results.json · methodology v0.1.0">
        <Note>
          No independently trained, product-specific machine-learning model is used for scoring. The figures below evaluate
          deterministic extractors, dictionary rules and the scoring formula on small labelled sets. Read them with their sample
          sizes; they are not general accuracy claims.
        </Note>
        <div className="mt-4 -mx-5 overflow-x-auto sm:mx-0">
          <table className="w-full min-w-[640px] text-left text-sm">
            <caption className="sr-only">Component evaluation results</caption>
            <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
              <tr>
                <th scope="col" className="px-5 py-2 font-medium sm:px-3">Component</th>
                <th scope="col" className="px-3 py-2 font-medium">Result</th>
                <th scope="col" className="px-3 py-2 font-medium">Evaluated on</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {EVALUATION_SNAPSHOT.map((r) => (
                <tr key={r.component} className="align-top">
                  <th scope="row" className="px-5 py-2.5 font-medium text-ink sm:px-3">{r.component}</th>
                  <td className="px-3 py-2.5">{r.status === "run" ? <span className="tabular-nums text-ink">{r.metric}</span> : <Badge tone="slate">Not measured</Badge>}</td>
                  <td className="px-3 py-2.5 text-slate-700">{r.data}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </ChartCard>

      <ChartCard title="Not available from the current API" subtitle="Shown here so their absence is explicit rather than hidden">
        <ul className="grid gap-3 md:grid-cols-3">
          {NOT_AVAILABLE.map((n) => (
            <li key={n.name} className="rounded-xl border border-dashed border-slate-300 p-4">
              <p className="text-sm font-medium text-ink">{n.name}</p>
              <p className="mt-1 text-xs text-muted">{n.why}</p>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-muted">
          Each of these is visible for a single product in its <Link href="/products" className="underline hover:text-forest">product report</Link>.
        </p>
      </ChartCard>
    </div>
  );
}

export function InsightsView() {
  const [state, retry] = useApi((signal) => loadCatalogStats(signal), []);
  return (
    <>
      <PageHeader
        eyebrow="Analytics"
        title="Insights & analytics"
        description="Distributions across the stored catalogue, and what has (and has not) been measured about the analysis itself."
        crumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Insights & analytics" }]}
      />
      {state.kind === "loading" ? <LoadingState label="Computing insights…" lines={5} /> : null}
      {state.kind === "error" ? (
        <ErrorState title="Could not load insights" message={state.error.message} code={state.error.code}
          action={<button type="button" className="font-medium underline" onClick={retry}>Try again</button>} />
      ) : null}
      {state.kind === "ready" ? <InsightsContent stats={state.data} /> : null}
    </>
  );
}
