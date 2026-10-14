import type { NutritionBasis } from "./types";

const NUTRIENT_LABELS: Record<string, string> = {
  energy: "Energy",
  protein: "Protein",
  carbohydrate: "Carbohydrate",
  total_sugars: "Total sugars",
  added_sugars: "Added sugars",
  total_fat: "Total fat",
  saturated_fat: "Saturated fat",
  trans_fat: "Trans fat",
  fibre: "Fibre",
  sodium: "Sodium",
};

export const NUTRIENT_ORDER = Object.keys(NUTRIENT_LABELS);

export const NUTRIENT_UNITS: Record<string, string> = {
  energy: "kcal",
  sodium: "mg",
};

export function nutrientUnit(key: string): string {
  return NUTRIENT_UNITS[key] ?? "g";
}

/** "total_sugars" -> "Total sugars"; unknown keys are humanised. */
export function humanize(key: string | null | undefined): string {
  if (!key) return "";
  if (NUTRIENT_LABELS[key]) return NUTRIENT_LABELS[key];
  const s = key.replace(/_/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function basisLabel(basis: NutritionBasis | string | null | undefined): string {
  if (basis === "per_100g") return "per 100 g";
  if (basis === "per_100ml") return "per 100 ml";
  return "per 100 g/ml";
}

export function unitFromBasis(basis: NutritionBasis | string | null | undefined): string {
  return basis === "per_100ml" ? "ml" : basis === "per_100g" ? "g" : "g/ml";
}

export function formatNumber(v: number | null | undefined, maxFractionDigits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: maxFractionDigits }).format(v);
}

export function formatInr(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(v);
}

export function formatPercent(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${Math.round(v * 100)}%`;
}

/** Fixed-format timestamp in UTC so server and client render the same text. */
export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getUTCDate()} ${months[d.getUTCMonth()]} ${d.getUTCFullYear()}, ${pad(d.getUTCHours())}:${pad(
    d.getUTCMinutes(),
  )} UTC`;
}

export function hostOf(url: string | null | undefined): string {
  if (!url) return "";
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

/** Only http(s) links are rendered as anchors. */
export function safeHref(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const u = new URL(url);
    return u.protocol === "http:" || u.protocol === "https:" ? u.toString() : null;
  } catch {
    return null;
  }
}

export function parseIds(raw: string | null | undefined): number[] {
  if (!raw) return [];
  const out: number[] = [];
  for (const part of raw.split(",")) {
    const n = Number(part.trim());
    if (Number.isInteger(n) && n > 0 && !out.includes(n)) out.push(n);
  }
  return out.slice(0, 6);
}
