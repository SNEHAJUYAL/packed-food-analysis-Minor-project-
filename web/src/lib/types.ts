// Types mirroring docs/api.md. Fields the contract adds but the current backend may not
// send yet are optional, and every renderer treats them as possibly absent.

export type EvidenceLabel = "declared" | "derived" | "interpreted" | "verified" | "unknown";

export interface Evidence<T = unknown> {
  value: T | null;
  label: EvidenceLabel;
  source?: string | null;
  note?: string | null;
}

export type AnalysisStatus = "complete" | "partial" | "insufficient_data";
export type Grade = "A" | "B" | "C" | "D" | "E";
export type TrafficLight = "green" | "yellow" | "red";
export type NutritionBasis = "per_100g" | "per_100ml";

export type ClaimStatus =
  | "consistent with available evidence"
  | "requires context"
  | "potential inconsistency for review"
  | "cannot be verified from available information";

export type DimensionName = "nutrition" | "ingredients" | "transparency" | "claims" | "value";

export type Preference = "balanced" | "nutrition" | "price" | "transparency";

export interface ApiErrorBody {
  detail?: { code?: string; message?: string } | string | unknown;
}

export interface Health {
  status: string;
  database: "ok" | "unavailable";
  methodology_version: string;
  product_count: number;
}

export interface AnalyzeUrlRequest {
  url: string;
  category?: string | null;
  refresh?: boolean;
}

export interface CandidateProvenance {
  source_id: string;
  source_url: string;
  extraction_method: string;
  collected_at: string;
  raw_value?: unknown;
  evidence_state?: string;
}

export interface CandidateFieldEvidence {
  field_path: string;
  original_value: unknown;
  normalized_value?: unknown;
  provenance: CandidateProvenance;
  validation_status: "candidate" | "requires_review" | "conflict" | "invalid";
}

export interface CandidateIssue {
  code: string;
  field_path: string;
  message: string;
  severity: "error" | "warning" | "info";
}

export interface ProductURLCandidateResult {
  status: "candidate" | "blocked" | "invalid" | "failed";
  submitted_url: string;
  source_id?: string | null;
  candidate?: {
    candidate_id: string;
    status: "candidate";
    source_id: string;
    source_attribution?: string | null;
    license?: string | null;
    submitted_url: string;
    final_url: string;
    extracted_at: string;
    normalized_product: Product;
    field_evidence: CandidateFieldEvidence[];
    images: {
      image_url: string;
      source: string;
      image_type: string;
      product_association: "product_entity" | "page_level_unverified";
      validation_status: "url_syntax_valid_not_fetched" | "requires_review" | "invalid";
      provenance: CandidateProvenance;
    }[];
    issues: CandidateIssue[];
  } | null;
  issues?: CandidateIssue[];
  error_code?: string | null;
  message?: string | null;
}

export interface AnalyzeUploadRequest {
  file: File;
  /** Where the product was listed, if known. */
  page_url?: string | null;
  /** Shop it is from, e.g. blinkit.com. */
  site?: string | null;
  category?: string | null;
  /** Product name, when the image does not show it. */
  name?: string | null;
  /** Optional corrections/additions; user values take precedence over extracted values. */
  corrections?: {
    brand?: string | null;
    variant?: string | null;
    pack_size_text?: string | null;
    ingredients_text?: string | null;
    nutrition_basis?: NutritionBasis | null;
    nutrition_text?: string | null;
  };
}

export interface ManualAnalyzeRequest {
  name: string;
  brand?: string | null;
  category?: string | null;
  variant?: string | null;
  pack_size?: number | null;
  pack_unit?: "g" | "ml" | null;
  ingredients_text?: string | null;
  nutrition_basis?: NutritionBasis | null;
  nutrition?: Record<string, string>;
  price_inr?: number | null;
}

export interface ProductSummary {
  product_id: number;
  name: string | null;
  brand: string | null;
  category: string | null;
  pack_size: number | null;
  pack_unit: "g" | "ml" | null;
  price_per_100: number | null;
  overall: number | null;
  grade: Grade | null;
  status: AnalysisStatus;
  source_type: string;
  is_synthetic: boolean;
  source_url: string | null;
  collected_at: string;
}

export interface ProductList {
  products: ProductSummary[];
  total: number;
}

export interface SourceInfo {
  source_type: string;
  source_url: string | null;
  /** Shop the listing came from, e.g. blinkit.com (null for Open Food Facts and sample records). */
  site?: string | null;
  extraction_method?: string | null;
  collected_at?: string | null;
  last_verified_at?: string | null;
  source_reliability?: string | null;
}

export interface ExtractionLogEntry {
  step: string;
  outcome: "ok" | "skipped" | "failed" | string;
  detail?: string | null;
}

export interface NutritionOriginal {
  value: string | number | null;
  basis_text?: string | null;
  source?: string | null;
}

export interface AdditiveRef {
  ins?: string | null;
  name?: string | null;
  functional_class?: string | null;
  group?: string | null;
}

export interface IngredientItem {
  position: number;
  text: string;
  name?: string | null;
  term?: string | null;
  match?: "exact" | "contained" | "fuzzy" | "none" | string | null;
  match_score?: number | null;
  percent?: number | null;
  classes?: string[];
  functional_category?: string | null;
  explanation?: string | null;
  reference_source?: string | null;
  status?: "matched" | "fuzzy_match" | "uncertain" | string | null;
  additives?: AdditiveRef[];
  sub_ingredients?: IngredientItem[];
}

export interface Product {
  product_id?: number | string | null;
  name: Evidence<string>;
  brand: Evidence<string>;
  category: Evidence<string>;
  variant?: Evidence<string>;
  pack_size: Evidence<number>;
  pack_unit: Evidence<string>;
  price_inr: Evidence<number>;
  image_url?: Evidence<string>;
  mrp_inr?: Evidence<number>;
  discount_percent?: Evidence<number>;
  availability?: Evidence<string>;
  multipack_count?: Evidence<number>;
  retailer?: Evidence<string>;
  ingredients_raw?: Evidence<string>;
  nutrition_basis: NutritionBasis | null;
  nutrition: Record<string, Evidence<number>>;
  nutrition_original?: Record<string, NutritionOriginal> | null;
  ingredients_normalised?: IngredientItem[] | null;
  additives_ins?: string[];
  allergens?: string[];
  claims_raw?: string[];
  source_url?: string | null;
  collected_at?: string | null;
  last_verified_at?: string | null;
  conflict_flag?: boolean;
  conflicts?: string[];
  warnings?: string[];
}

export interface NutritionFact {
  value: number | null;
  unit: string;
  evidence: EvidenceLabel;
}

export interface Subscore {
  subscore: number | null;
  reason: string | null;
  benchmark_source?: string | null;
}

export interface ScoreRow {
  name: string;
  score: number | null;
  weight: number;
  effective_weight: number;
  contribution: number | null;
}

export interface NutritionDimension {
  score: number | null;
  basis?: NutritionBasis | null;
  coverage?: number | null;
  facts?: Record<string, NutritionFact>;
  traffic_lights?: Record<string, TrafficLight>;
  subscores?: Record<string, Subscore>;
  detail?: { raw?: number; score?: number; coverage?: number; rows?: ScoreRow[]; missing?: string[] };
  explanation: string[];
}

export interface IngredientsDimension {
  score: number | null;
  groups?: Record<string, string[]>;
  explanation: string[];
}

export interface TransparencyDimension {
  score: number | null;
  missing?: string[];
  explanation: string[];
}

export interface ClaimResult {
  claim_id?: string | null;
  claim: string;
  matched_text?: string | null;
  status: ClaimStatus | string;
  facts?: string[];
  reason?: string | null;
  missing_information?: string[];
  rule?: string | null;
  rule_status?: string | null;
  source_url?: string | null;
}

export interface ClaimsDimension {
  score: number | null;
  explanation: string[];
  claims: ClaimResult[];
}

export interface ValueDimension {
  score: number | null;
  price_per_100?: number | null;
  category_median?: number | null;
  peer_count?: number | null;
  explanation: string[];
}

export interface Dimensions {
  nutrition: NutritionDimension;
  ingredients: IngredientsDimension;
  transparency: TransparencyDimension;
  claims: ClaimsDimension;
  value: ValueDimension;
}

export interface Overall {
  score: number | null;
  grade: Grade | null;
  raw?: number | null;
  coverage?: number | null;
  missing?: string[];
  rows?: ScoreRow[];
  notes?: string[];
}

export interface IngredientsNormalised {
  items: IngredientItem[];
  additives_ins?: string[];
  allergens?: string[];
  advisory_allergens?: string[];
  allergen_advisory?: unknown;
  unmatched?: string[];
}

export interface Report {
  product: Product;
  dimensions: Dimensions;
  overall: Overall;
  ingredients_normalised?: IngredientsNormalised | null;
  fop_warning_simulation?: { status: string; triggers?: string[]; reason?: string | null };
  disclaimer?: string;
}

export interface ProductAnalysis {
  product_id: number;
  status: AnalysisStatus;
  is_synthetic: boolean;
  source: SourceInfo;
  missing_fields: string[];
  conflicts: string[];
  extraction_log?: ExtractionLogEntry[];
  methodology_version: string;
  report: Report;
  extras?: ProductExtras;
}

export interface Micronutrient {
  label: string;
  value: number;
  unit: string;
  group: "mineral" | "vitamin" | "other";
  source: string;
}

/** Shown on the report but not scored. */
export interface ProductExtras {
  micronutrients?: Record<string, Micronutrient>;
  image_url?: string | null;
  off_nutriscore_grade?: string | null;
  price_observation_count?: number;
}

export interface SearchStoredHit {
  product_id: number;
  name: string | null;
  brand: string | null;
  category: string | null;
  barcode?: string | null;
  pack_size?: number | null;
  pack_unit?: "g" | "ml" | null;
  price_inr?: number | null;
  price_retailer?: string | null;
  price_evidence?: PriceEvidence | null;
  source_url?: string | null;
  collected_at?: string | null;
  overall: number | null;
  grade: Grade | null;
  status: AnalysisStatus;
  price_per_100: number | null;
  is_synthetic: boolean;
  image_url?: string | null;
}

export interface SearchOnlineHit {
  barcode: string;
  name: string | null;
  brand: string | null;
  quantity: string | null;
  nutriscore_grade: string | null;
  image_url: string | null;
  product_id: number | null;
  stored: boolean;
  source_url: string;
}

export interface SearchResult {
  query: string;
  stored: SearchStoredHit[];
  online: SearchOnlineHit[];
  notes: string[];
  attribution: string;
}

export type PriceEvidence = "invoice" | "hand" | "unverified" | "synthetic";

export interface PriceObservationRow {
  id: number;
  retailer: string;
  retailer_label: string;
  price_inr: number;
  pack_size: number | null;
  pack_unit: string | null;
  price_per_100: number | null;
  observed_at: string | null;
  source: string | null;
  source_url: string | null;
  evidence: PriceEvidence;
  evidence_text: string;
  is_mrp: boolean;
  outlier: boolean;
}

export interface RetailerPrice {
  retailer: string;
  retailer_label: string;
  observations: number;
  evidence: PriceEvidence;
  outlier: boolean;
  latest_price_inr: number;
  latest_price_per_100: number | null;
  latest_observed_at: string | null;
  pack_size: number | null;
  pack_unit: string | null;
  lowest_price_per_100: number | null;
  highest_price_per_100: number | null;
  change_inr: number | null;
  change_percent: number | null;
  trend: "up" | "down" | "flat" | null;
  source_url: string | null;
}

export interface PriceSummary {
  product_id: number;
  basis: string;
  is_synthetic: boolean;
  observations: PriceObservationRow[];
  retailers: RetailerPrice[];
  cheapest: string | null;
  spread: { cheapest: string; dearest: string; difference_per_100: number; difference_percent: number | null } | null;
  vs_category: { category_median_per_100: number; peer_count: number; difference_percent: number } | null;
  mrp: { price_inr: number; observed_at: string | null; evidence_text: string } | null;
  notes: string[];
  retailer_options: Record<string, string>;
}

export interface PriceEntryRequest {
  retailer: string;
  price_inr: number;
  pack_size_text?: string | null;
  observed_at?: string | null;
  place?: string | null;
  listing_url?: string | null;
}

export interface CompareRequest {
  product_ids: number[];
  priorities?: Partial<Record<DimensionName, number>> | null;
}

export interface Pick {
  product_id: number;
  reason: string;
  name?: string | null;
  brand?: string | null;
  is_synthetic?: boolean | null;
}

export interface CompareProduct {
  product_id: number;
  name: string | null;
  brand: string | null;
  is_synthetic: boolean;
  overall: number | null;
  grade: Grade | null;
  status?: AnalysisStatus | null;
  priority_score?: number | null;
  dimensions: Partial<Record<DimensionName, number | null>>;
  nutrition: Record<string, { value: number | null; label: EvidenceLabel; unit?: string | null }>;
  price_per_100: number | null;
  completeness: number | null;
  ingredient_classes: string[];
  claims: { matched_text?: string | null; status: string; claim?: string | null }[];
  source_url: string | null;
  collected_at: string | null;
}

export interface CompareResult {
  category: string | null;
  basis: NutritionBasis | null;
  methodology_version: string;
  priorities?: Partial<Record<DimensionName, number>> | null;
  products: CompareProduct[];
  ingredient_differences?: { shared_classes: string[]; only_in: Record<string, string[]> };
  picks?: {
    best_match?: Pick | null;
    lowest_price_per_100?: Pick | null;
    best_nutrition?: Pick | null;
  };
  rationale?: string[];
}

export interface Alternative {
  product_id: number;
  rank: number;
  name: string | null;
  brand: string | null;
  is_synthetic: boolean;
  overall: number | null;
  grade: Grade | null;
  nutrition: number | null;
  transparency: number | null;
  price_per_100: number | null;
  similarity: number | null;
  preference_score: number | null;
  matching_attributes: string[];
  rationale: string;
  source_url: string | null;
  site?: string | null;
  collected_at: string | null;
}

export interface AlternativesResult {
  source_product_id: number;
  preference: Preference;
  methodology_version: string;
  eligible_count: number;
  /** Shop the source product came from, if known. */
  site?: string | null;
  /** same_site: drawn only from products analysed from that shop; all: every stored product. */
  scope?: "same_site" | "all";
  alternatives: Alternative[];
  picks?: {
    best_match?: (Partial<Alternative> & { product_id: number; reason?: string }) | null;
    lowest_unit_price?: (Partial<Alternative> & { product_id: number; reason?: string }) | null;
    best_nutrition?: (Partial<Alternative> & { product_id: number; reason?: string }) | null;
  };
  message: string | null;
}

export interface Category {
  id: string;
  label: string;
  product_count: number;
}

export type Row = Record<string, unknown>;

export interface Methodology {
  version: string;
  dimension_weights: Record<string, number>;
  grade_bands: { grade: string; min: number }[] | Record<string, unknown>;
  scoring?: Record<string, unknown>;
  thresholds?: Row[];
  claim_rules?: Row[];
  category_weights?: Row[];
  evidence_labels?: Record<string, string>;
  claim_statuses?: Record<string, string>;
  data_sources?: { name: string; licence?: string; use?: string; url?: string }[];
  limitations?: string[];
  missing_data?: string[] | string | null;
  freshness?: string[] | string | null;
}
