import type { Category, Grade, Health, ProductList, ProductSummary } from "./types";
import { api } from "./api";

/** The list endpoint caps `limit` at 500 (src/api/main.py); stats say how many records they cover. */
export const CATALOG_LIMIT = 500;

export interface CountRow {
  key: string;
  label: string;
  count: number;
}

export interface CatalogStats {
  total: number;
  loaded: number;
  real: number;
  synthetic: number;
  scored: number;
  withUnitPrice: number;
  grades: CountRow[];
  scoreBins: CountRow[];
  statuses: CountRow[];
  sources: CountRow[];
  categories: CountRow[];
  recent: ProductSummary[];
  health: Health | null;
}

const GRADES: Grade[] = ["A", "B", "C", "D", "E"];
const STATUS_LABELS: Record<string, string> = {
  complete: "Complete",
  partial: "Partial data",
  insufficient_data: "Insufficient data",
};
const SOURCE_LABELS: Record<string, string> = {
  open_food_facts: "Open Food Facts",
  synthetic: "Synthetic demo",
  synthetic_sample: "Synthetic demo",
  url: "Product URL",
  saved_page: "Saved page upload",
  photo: "Photo / screenshot",
  manual: "Manual entry",
};

export function sourceLabel(sourceType: string): string {
  return SOURCE_LABELS[sourceType] ?? sourceType.replace(/_/g, " ");
}

function tally(items: string[], labels: (k: string) => string): CountRow[] {
  const m = new Map<string, number>();
  for (const k of items) m.set(k, (m.get(k) ?? 0) + 1);
  return [...m.entries()].map(([key, count]) => ({ key, label: labels(key), count })).sort((a, b) => b.count - a.count);
}

export function computeStats(list: ProductList, categories: Category[], health: Health | null): CatalogStats {
  const products = list.products ?? [];
  const scored = products.filter((p) => p.overall !== null && p.overall !== undefined);
  const grades: CountRow[] = [
    ...GRADES.map((g) => ({ key: g, label: `Grade ${g}`, count: products.filter((p) => p.grade === g).length })),
    { key: "none", label: "Not graded", count: products.filter((p) => !p.grade).length },
  ];
  const scoreBins: CountRow[] = Array.from({ length: 10 }, (_, i) => {
    const lo = i * 10;
    const hi = i === 9 ? 100 : lo + 9;
    return {
      key: String(lo),
      label: `${lo}–${hi}`,
      count: scored.filter((p) => {
        const v = p.overall as number;
        return i === 9 ? v >= 90 : v >= lo && v < lo + 10;
      }).length,
    };
  });
  const recent = [...products]
    .sort((a, b) => (Date.parse(b.collected_at) || 0) - (Date.parse(a.collected_at) || 0))
    .slice(0, 6);
  return {
    total: list.total ?? products.length,
    loaded: products.length,
    real: products.filter((p) => !p.is_synthetic).length,
    synthetic: products.filter((p) => p.is_synthetic).length,
    scored: scored.length,
    withUnitPrice: products.filter((p) => p.price_per_100 !== null && p.price_per_100 !== undefined).length,
    grades,
    scoreBins,
    statuses: tally(products.map((p) => p.status), (k) => STATUS_LABELS[k] ?? k),
    sources: tally(products.map((p) => (p.is_synthetic ? "synthetic" : p.source_type)), sourceLabel),
    categories: categories
      .map((c) => ({ key: c.id, label: c.label, count: c.product_count }))
      .filter((c) => c.count > 0)
      .sort((a, b) => b.count - a.count),
    recent,
    health,
  };
}

/** Everything the dashboard and insights pages show, from three real endpoints. */
export async function loadCatalogStats(signal: AbortSignal): Promise<CatalogStats> {
  const [list, cats, health] = await Promise.all([
    api.listProducts({ limit: CATALOG_LIMIT }, signal),
    api.categories(signal).then((r) => r.categories ?? []).catch(() => [] as Category[]),
    api.health(signal).catch(() => null),
  ]);
  return computeStats(list, cats, health);
}
