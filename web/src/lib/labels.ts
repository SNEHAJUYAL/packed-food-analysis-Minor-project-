import type { AnalysisStatus, EvidenceLabel, IngredientItem, Preference } from "./types";

/** Meanings from the methodology (src/core/schema.py); the API's own text wins when present. */
export const EVIDENCE_LABELS: Record<EvidenceLabel, { title: string; meaning: string }> = {
  declared: { title: "Declared", meaning: "Stated by the product listing or package." },
  derived: { title: "Derived", meaning: "Calculated from declared data (for example, price per 100 g or a per-serving value scaled to 100 g)." },
  interpreted: { title: "Interpreted", meaning: "Judged against a defined benchmark or rule (for example, a category guessed from the name)." },
  verified: { title: "Verified", meaning: "Checked against an authoritative source." },
  unknown: { title: "Unknown", meaning: "Cannot be established from the available evidence. Missing is never treated as zero." },
};

export const EVIDENCE_ORDER: EvidenceLabel[] = ["declared", "derived", "interpreted", "verified", "unknown"];

export type Tone = "green" | "teal" | "amber" | "slate" | "blue" | "violet" | "rose";

export const EVIDENCE_TONE: Record<EvidenceLabel, Tone> = {
  declared: "blue",
  derived: "teal",
  interpreted: "violet",
  verified: "green",
  unknown: "slate",
};

export function evidenceMeaning(label: string): string {
  return EVIDENCE_LABELS[label as EvidenceLabel]?.meaning ?? "Evidence label reported by the analysis.";
}

export const CLAIM_STATUSES: Record<string, { short: string; meaning: string; tone: Tone }> = {
  "consistent with available evidence": {
    short: "Consistent with available evidence",
    meaning: "The declared values meet the regulatory condition for this claim.",
    tone: "teal",
  },
  "requires context": {
    short: "Requires context",
    meaning: "The claim may be technically met but needs context to be understood fairly.",
    tone: "blue",
  },
  "potential inconsistency for review": {
    short: "Potential inconsistency for review",
    meaning:
      "The declared values do not appear to meet the condition we checked. This is a prompt for review, not a finding of wrongdoing; some routes (such as per-serving) may not have been checked.",
    tone: "amber",
  },
  "cannot be verified from available information": {
    short: "Cannot be verified",
    meaning: "Information needed to check the claim is missing from the listing.",
    tone: "slate",
  },
};

export function claimStatusInfo(status: string) {
  return (
    CLAIM_STATUSES[status] ?? { short: status, meaning: "Status reported by the claim check.", tone: "slate" as Tone }
  );
}

export const ANALYSIS_STATUS: Record<AnalysisStatus, { title: string; meaning: string; tone: Tone }> = {
  complete: { title: "Complete", meaning: "All core fields were found.", tone: "teal" },
  partial: {
    title: "Partial data",
    meaning: "Some fields were not found. Scores use only what is known and weights are renormalised.",
    tone: "amber",
  },
  insufficient_data: {
    title: "Insufficient data",
    meaning: "Too little information was found to score this product reliably.",
    tone: "slate",
  },
};

export const INGREDIENT_STATUS: Record<string, { title: string; meaning: string; uncertain: boolean }> = {
  matched: { title: "Matched", meaning: "Matched a term in the ingredient dictionary.", uncertain: false },
  fuzzy_match: {
    title: "Fuzzy match",
    meaning: "Matched approximately (spelling or wording differs). Check the original text.",
    uncertain: true,
  },
  uncertain: { title: "Uncertain", meaning: "Could not be matched confidently to a known ingredient.", uncertain: true },
  none: { title: "No match", meaning: "Not found in the ingredient dictionary.", uncertain: true },
};

/** Status from the API when present, else derived from `match` for older backend output. */
export function ingredientStatus(item: IngredientItem): string {
  if (item.status) return item.status;
  switch (item.match) {
    case "exact":
    case "contained":
      return "matched";
    case "fuzzy":
      return "fuzzy_match";
    case "none":
      return "none";
    default:
      return "uncertain";
  }
}

export const PREFERENCES: { id: Preference; label: string; hint: string }[] = [
  { id: "balanced", label: "Balanced", hint: "Uses the methodology's dimension weights." },
  { id: "nutrition", label: "Nutrition", hint: "Ranks by the nutrition score." },
  { id: "price", label: "Lower unit price", hint: "Ranks by price per 100 g/ml." },
  { id: "transparency", label: "Transparency", hint: "Ranks by how fully the label is disclosed." },
];

export const DIMENSIONS = ["nutrition", "ingredients", "transparency", "claims", "value"] as const;

export const DIMENSION_INFO: Record<string, string> = {
  nutrition: "Nutrient sub-scores against sourced benchmarks, per 100 g/ml.",
  ingredients: "Ingredient-list signals of processing and disclosure (not safety findings).",
  transparency: "How completely the listing discloses core fields.",
  claims: "Whether printed claims match the regulatory conditions we can check.",
  value: "Price per 100 g/ml against stored products in the same category.",
};

export const ANALYSIS_STEPS = [
  "Validating URL",
  "Fetching page",
  "Reading structured data",
  "Parsing page",
  "Normalising",
  "Scoring",
];

export const LIGHT_LABEL: Record<string, string> = { green: "Green", yellow: "Amber", red: "Red" };
