"use client";

import Link from "next/link";
import { ChartCard, CountBarChart, ShareBar } from "./charts";
import { AnalysisStatusBadge, GradeBadge, SyntheticBadge } from "./badges";
import { IconArrowRight, IconColumns, IconDatabase, IconGrid, IconLeaf, IconLink, IconPencil, IconShield, IconUpload } from "./icons";
import { ServiceStatus } from "./ServiceStatus";
import { EmptyState, ErrorState, LoadingState, Note, PageHeader, StatCard, buttonClass } from "./ui";
import { loadCatalogStats, sourceLabel, type CatalogStats, type CountRow } from "@/lib/catalog";
import { formatTimestamp, humanize } from "@/lib/format";
import { useApi } from "@/lib/useApi";

export const GRADE_COLOR: Record<string, string> = {
  A: "#234b39", B: "#3b6e55", C: "#a9c08f", D: "#e9a65b", E: "#d96b63", none: "#cdd3ca",
};

export function CoverageNote({ stats }: { stats: CatalogStats }) {
  if (stats.loaded >= stats.total) return null;
  return (
    <Note>
      Distributions are computed from the first {stats.loaded} of {stats.total} stored products (the API returns at most
      {" "}{stats.loaded} per request). Totals use the full count.
    </Note>
  );
}

const QUICK = [
  { href: "/analyze", label: "Analyze a product URL", body: "Paste a product page link", icon: IconLink },
  { href: "/analyze#packaging-image-upload", label: "Upload pack photo", body: "Photo, screenshot or saved page", icon: IconUpload },
  { href: "/analyze#manual-entry-form", label: "Enter details manually", body: "Type the label yourself", icon: IconPencil },
  { href: "/compare", label: "Compare products", body: "2–6 in one category", icon: IconColumns },
  { href: "/alternatives", label: "Find alternatives", body: "From stored products", icon: IconLeaf },
];

function RecentList({ stats }: { stats: CatalogStats }) {
  if (!stats.recent.length) {
    return (
      <EmptyState title="No products stored yet.">
        <p><Link href="/analyze" className="text-forest underline">Analyze a product</Link> or run <code>./run.sh seed</code>.</p>
      </EmptyState>
    );
  }
  return (
    <ul className="divide-y divide-line">
      {stats.recent.map((p) => (
        <li key={p.product_id}>
          <Link href={`/products/${p.product_id}`} className="group flex items-center gap-3 py-3 transition hover:bg-brand-50/40 sm:-mx-2 sm:rounded-xl sm:px-2">
            <GradeBadge grade={p.grade} />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-ink group-hover:text-forest">{p.name ?? `Product ${p.product_id}`}</span>
              <span className="block truncate text-xs text-muted">
                {[p.brand, p.category ? humanize(p.category) : null, sourceLabel(p.is_synthetic ? "synthetic" : p.source_type)].filter(Boolean).join(" · ")}
              </span>
            </span>
            <span className="hidden flex-col items-end gap-1 sm:flex">
              {p.is_synthetic ? <SyntheticBadge /> : <AnalysisStatusBadge status={p.status} />}
              <span className="text-[11px] text-muted">{formatTimestamp(p.collected_at)}</span>
            </span>
            <span className="w-12 text-right text-sm font-semibold tabular-nums text-ink">{p.overall ?? "—"}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function DashboardContent({ stats }: { stats: CatalogStats }) {
  const gradeRows: CountRow[] = stats.grades;
  return (
    <div className="space-y-6">
      <CoverageNote stats={stats} />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Products stored" value={stats.total} note="All records in the database" icon={<IconDatabase className="h-4 w-4" />} />
        <StatCard label="Real records" value={stats.real} note={`${stats.synthetic} synthetic demo records labelled separately`} icon={<IconShield className="h-4 w-4" />} />
        <StatCard label="With an overall score" value={stats.scored} note="Unscored when nutrition data is too thin" icon={<IconGrid className="h-4 w-4" />} />
        <StatCard label="With a unit price" value={stats.withUnitPrice} note="Needs a price and a pack size" icon={<IconColumns className="h-4 w-4" />} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <ChartCard title="Products by category" subtitle="Stored products per category, all sources">
          {stats.categories.length ? <CountBarChart rows={stats.categories} /> : <p className="text-sm text-muted">No categories reported by the API.</p>}
        </ChartCard>
        <ChartCard title="Grade distribution" subtitle="Overall grade A–E; ungraded products had too little data to score">
          <CountBarChart rows={gradeRows} layout="vertical" colorFor={(r) => GRADE_COLOR[r.key] ?? "#234b39"} />
        </ChartCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <ChartCard
          title="Recent analyses"
          subtitle="Most recently collected records"
          action={<Link href="/products" className={`${buttonClass.ghost} !px-2 !py-1 text-xs`}>View all <IconArrowRight className="h-3.5 w-3.5" /></Link>}
        >
          <RecentList stats={stats} />
        </ChartCard>
        <div className="space-y-6">
          <ChartCard title="Quick actions">
            <ul className="grid gap-2">
              {QUICK.map(({ href, label, body, icon: Icon }) => (
                <li key={href}>
                  <Link href={href} className="group flex items-center gap-3 rounded-xl border border-line p-3 transition hover:border-brand-300 hover:bg-brand-50/50">
                    <span aria-hidden="true" className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-forest"><Icon className="h-4.5 w-4.5" /></span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium text-ink">{label}</span>
                      <span className="block text-xs text-muted">{body}</span>
                    </span>
                    <IconArrowRight className="h-4 w-4 text-slate-400 transition group-hover:translate-x-0.5 group-hover:text-forest" />
                  </Link>
                </li>
              ))}
            </ul>
          </ChartCard>
          <ChartCard title="Data composition" subtitle="Where the stored records come from">
            <ShareBar parts={stats.sources.map((s, i) => ({ label: s.label, count: s.count, color: ["#234b39", "#a9c08f", "#e9a65b", "#5b7fa6", "#9b7bb0", "#cdd3ca"][i] ?? "#cdd3ca" }))} />
          </ChartCard>
        </div>
      </div>

      <ChartCard title="Ingredient insights" subtitle="Per-product ingredient analysis">
        <Note>
          Ingredient classes, INS additives and allergens are analysed per product and shown in each product report. The API
          does not yet provide catalogue-wide ingredient statistics, so none are charted here.{" "}
          <Link href="/products" className="font-medium text-forest underline">Open a product report</Link> to see its ingredient explorer.
        </Note>
      </ChartCard>
    </div>
  );
}

export function DashboardView() {
  const [state, retry] = useApi((signal) => loadCatalogStats(signal), []);
  return (
    <>
      <PageHeader
        eyebrow="Overview"
        title="Your food intelligence workspace"
        description="A live view of the products stored in this installation: how many, where they came from, and how they score. Every number below comes from the API."
        crumbs={[{ label: "Home", href: "/" }, { label: "Dashboard" }]}
        actions={
          <>
            <Link href="/products" className={buttonClass.secondary}>Explore products</Link>
            <Link href="/analyze" className={buttonClass.primary}>Analyze a product</Link>
          </>
        }
      />
      <div className="mb-6"><ServiceStatus /></div>
      {state.kind === "loading" ? <LoadingState label="Loading dashboard…" lines={5} /> : null}
      {state.kind === "error" ? (
        <ErrorState
          title="Could not load the dashboard"
          message={state.error.message}
          code={state.error.code}
          action={<button type="button" className="font-medium underline" onClick={retry}>Try again</button>}
        />
      ) : null}
      {state.kind === "ready" ? <DashboardContent stats={state.data} /> : null}
    </>
  );
}
