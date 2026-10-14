// Test fixtures derived from report_example.json (current backend output for a synthetic
// "Example Foods" page). Variants add the contract-only fields so both shapes are covered.
import reportJson from "./report_example.json";
import type {
  AlternativesResult,
  CompareResult,
  Methodology,
  ProductAnalysis,
  ProductList,
  Report,
} from "@/lib/types";

const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v)) as T;

export const exampleReport = reportJson as unknown as Report;

/** The example as GET /api/products/12 would wrap it (no contract-only fields). */
export function makeAnalysis(overrides: Partial<ProductAnalysis> = {}): ProductAnalysis {
  const report = clone(exampleReport);
  return {
    product_id: 12,
    status: "complete",
    is_synthetic: true,
    source: {
      source_type: "synthetic_sample",
      source_url: report.product.source_url ?? null,
      extraction_method: "json-ld+html",
      collected_at: report.product.collected_at ?? null,
      last_verified_at: null,
      source_reliability: "synthetic",
    },
    missing_fields: ["added_sugars", "trans_fat"],
    conflicts: [],
    extraction_log: [
      { step: "fetch", outcome: "ok", detail: "200 OK" },
      { step: "json-ld", outcome: "ok", detail: "Product found" },
      { step: "llm_fallback", outcome: "skipped", detail: "not needed" },
    ],
    methodology_version: "0.1.0",
    report,
    ...overrides,
  };
}

/** A partial record using the contract's additional fields. */
export function makePartialAnalysis(): ProductAnalysis {
  const a = makeAnalysis({
    status: "partial",
    is_synthetic: false,
    conflicts: ["total_sugars: json-ld says 28, html-table says 30"],
    missing_fields: ["added_sugars", "trans_fat", "price_inr"],
  });
  const r = a.report;
  r.product.price_inr = { value: null, label: "unknown", source: null, note: null };
  r.dimensions.value.price_per_100 = null;
  r.product.nutrition_original = {
    total_sugars: { value: "8.4 g", basis_text: "per 30 g serving", source: "html-table" },
  };
  const items = r.ingredients_normalised!.items;
  items[0] = {
    ...items[0],
    percent: 62,
    status: "matched",
    functional_category: "cereal",
    explanation: "Whole grain cereal declared as the first ingredient.",
    reference_source: "ingredient_terms.csv",
  };
  items[3] = {
    ...items[3],
    text: "Vegtable Oil",
    match: "fuzzy",
    match_score: 86,
    status: "fuzzy_match",
    explanation: "Oil source not named.",
  };
  items[5] = { ...items[5], text: "Natural identicals", name: "", term: null, match: "none", classes: [], status: "uncertain" };
  r.dimensions.claims.claims[0] = {
    ...r.dimensions.claims.claims[0],
    missing_information: ["serving size"],
    source_url: "https://www.fssai.gov.in/upload/uploadfiles/files/Compendium_Advertising_Claims_Regulations_14_12_2022.pdf",
  };
  r.dimensions.claims.claims.push({
    claim_id: "source_of_fibre",
    claim: "Source of fibre",
    matched_text: "Source of Fibre",
    status: "consistent with available evidence",
    facts: ["fibre = 4 g per 100 g (declared)"],
    reason: "Meets the FSSAI condition of at least 3 g per 100 g.",
    rule: "FSS (Advertising and Claims) Regulations, 2018, Schedule I, Sl. No. 14",
    rule_status: "verified_official_text",
  });
  return a;
}

/** Overall not scored (nutrition missing). */
export function makeUnscoredAnalysis(): ProductAnalysis {
  const a = makeAnalysis({ status: "insufficient_data", missing_fields: ["energy", "protein", "total_sugars", "sodium"] });
  a.report.overall = { ...a.report.overall, score: null, grade: null, missing: ["nutrition", "value"], notes: [] };
  a.report.dimensions.nutrition.score = null;
  return a;
}

export const productList: ProductList = {
  total: 3,
  products: [
    {
      product_id: 12, name: "Choco Crunch Whole Grain Cereal - High Protein", brand: "Example Foods", category: "breakfast_cereals",
      pack_size: 375, pack_unit: "g", price_per_100: 48, overall: 69, grade: "C", status: "complete", source_type: "synthetic_sample",
      is_synthetic: true, source_url: "https://brand.example/cereal", collected_at: "2026-10-12T09:02:29+00:00",
    },
    {
      product_id: 3, name: "Plain Oat Flakes", brand: "Sample Mills", category: "breakfast_cereals",
      pack_size: 500, pack_unit: "g", price_per_100: 39.5, overall: 78, grade: "B", status: "complete", source_type: "synthetic_sample",
      is_synthetic: true, source_url: "https://brand.example/oats", collected_at: "2026-10-12T09:05:00+00:00",
    },
    {
      product_id: 7, name: "Honey Loops", brand: null, category: "breakfast_cereals",
      pack_size: null, pack_unit: null, price_per_100: null, overall: null, grade: null, status: "insufficient_data", source_type: "url",
      is_synthetic: false, source_url: null, collected_at: "2026-10-12T09:06:00+00:00",
    },
  ],
};

export const alternatives: AlternativesResult = {
  source_product_id: 12,
  preference: "balanced",
  methodology_version: "0.1.0",
  eligible_count: 2,
  alternatives: [
    {
      product_id: 3, rank: 1, name: "Plain Oat Flakes", brand: "Sample Mills", is_synthetic: true,
      overall: 78, grade: "B", nutrition: 80, transparency: 85, price_per_100: 39.5, similarity: 0.41, preference_score: 72.3,
      matching_attributes: ["same category", "same basis (per 100 g)", "whole grain first"],
      rationale: "Scores 78 against 69 for this product; lower sugar (1 g vs 28 g per 100 g).",
      source_url: "https://brand.example/oats", collected_at: "2026-10-12T09:05:00+00:00",
    },
  ],
  picks: {
    best_match: { product_id: 3, reason: "Highest balanced score among eligible products." },
    lowest_unit_price: { product_id: 3, reason: "₹39.50 per 100 g." },
    best_nutrition: null,
  },
  message: null,
};

export const noAlternatives: AlternativesResult = {
  ...alternatives,
  preference: "nutrition",
  eligible_count: 0,
  alternatives: [],
  picks: { best_match: null, lowest_unit_price: null, best_nutrition: null },
  message: "No stored product in this category scores higher on nutrition.",
};

export const compareResult: CompareResult = {
  category: "breakfast_cereals",
  basis: "per_100g",
  methodology_version: "0.1.0",
  products: [
    {
      product_id: 12, name: "Choco Crunch Whole Grain Cereal - High Protein", brand: "Example Foods", is_synthetic: true,
      overall: 69, grade: "C", dimensions: { nutrition: 61, ingredients: 95, transparency: 90, claims: 0, value: null },
      nutrition: { energy: { value: 410, label: "declared" }, total_sugars: { value: 28, label: "declared" }, added_sugars: { value: null, label: "unknown" } },
      price_per_100: 48, completeness: 0.9, ingredient_classes: ["whole_grain", "added_sugar", "cocoa"],
      claims: [{ matched_text: "High Protein", status: "potential inconsistency for review" }],
      source_url: "https://brand.example/cereal", collected_at: "2026-10-12T09:02:29+00:00",
    },
    {
      product_id: 3, name: "Plain Oat Flakes", brand: "Sample Mills", is_synthetic: true,
      overall: 78, grade: "B", dimensions: { nutrition: 80, ingredients: 100, transparency: 85, claims: null, value: 60 },
      nutrition: { energy: { value: 380, label: "declared" }, total_sugars: { value: 1, label: "declared" }, added_sugars: { value: 0, label: "declared" } },
      price_per_100: 39.5, completeness: 1, ingredient_classes: ["whole_grain"],
      claims: [], source_url: "https://brand.example/oats", collected_at: "2026-10-12T09:05:00+00:00",
    },
  ],
  ingredient_differences: { shared_classes: ["whole_grain"], only_in: { "12": ["added_sugar", "cocoa"], "3": [] } },
  picks: {
    best_match: { product_id: 3, reason: "Higher overall score (78 vs 69)." },
    lowest_price_per_100: { product_id: 3, reason: "₹39.50 vs ₹48.00 per 100 g." },
    best_nutrition: { product_id: 3, reason: "Nutrition 80 vs 61." },
  },
  rationale: ["Both products are breakfast cereals compared per 100 g."],
};

export const methodology: Methodology = {
  version: "0.1.0",
  dimension_weights: { nutrition: 0.4, ingredients: 0.25, transparency: 0.15, claims: 0.1, value: 0.1 },
  grade_bands: [
    { grade: "A", min: 85 },
    { grade: "B", min: 70 },
    { grade: "C", min: 55 },
    { grade: "D", min: 40 },
    { grade: "E", min: 0 },
  ],
  scoring: { min_nutrition_coverage: 0.5 },
  thresholds: [
    {
      parameter: "saturated_fat", category: "all_foods", basis: "per_100g", direction: "lower_better", green_bound: 1.5, red_bound: 5, unit: "g",
      source: "green: FSSAI Schedule I Sl. 4 'low saturated fat' (<=1.5 g/100 g); red: UK DH/FSA 2016 (>5 g/100 g)",
      status: "green_official_red_provisional", date_checked: "2026-10-12",
    },
  ],
  claim_rules: [
    {
      claim_id: "low_sugar", claim_label: "Low sugar", patterns: "low[- ]sugar", nutrient: "total_sugars", condition: "max",
      threshold_solid: 5, threshold_liquid: 2.5, unit: "g per 100 g (solids) or 100 ml (liquids)",
      regulation: "FSS (Advertising and Claims) Regulations, 2018 (compendium 14-12-2022)", clause: "Schedule I, Sl. No. 10 (Sugars: Low), reg. 5(3)",
      source_url: "https://www.fssai.gov.in/upload/uploadfiles/files/Compendium_Advertising_Claims_Regulations_14_12_2022.pdf",
      status: "verified_official_text", date_checked: "2026-10-12",
    },
  ],
  evidence_labels: {
    declared: "stated by the listing or package",
    derived: "calculated from declared data",
    interpreted: "judged against a defined benchmark",
    verified: "checked against an authoritative source",
    unknown: "cannot be established from available evidence",
  },
  claim_statuses: {},
  data_sources: [{ name: "Open Food Facts", licence: "ODbL", use: "Product data fallback" }],
  limitations: ["Prototype weights."],
};
