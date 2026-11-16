# Packaged-food annotation guidelines

**Specification:** `annotation_schema_version = "1.0"`  
**Dataset:** separate research data under `data/annotation/`; never production PostgreSQL.  
**Purpose:** create auditable ground truth for future extraction, classification, normalization, identity and recommendation evaluation. These instructions do not authorize copying source content beyond its license.

## Core rules

1. Annotate the exact package variant evidenced by a clear package photo, physical pack, or authoritative manufacturer source. A retailer listing or OFF record can identify a candidate, but is not by itself proof that the current package was checked.
2. Transcribe source text faithfully before normalizing it. Preserve spelling, punctuation, language, order, units and label basis. Keep normalized values in separate fields.
3. Never infer information absent from evidence. Do not derive a flavour from a product family, infer ingredients from a recipe, convert a serving amount into pack size, infer MRP from sale price, or treat an empty field as zero.
4. Set a state for every annotated field using exactly one of: `verified`, `missing`, `illegible`, `not_declared`, `not_applicable`, `requires_review`. `verified` means supported by cited evidence and reviewer inspection, not that the claim is objectively true. Use `not_declared` only after checking the relevant package area/source; use `missing` when evidence was not obtained; use `illegible` when present but unreadable; use `not_applicable` only when the concept does not apply; use `requires_review` when evidence conflicts or identity cannot be resolved.
5. Keep every cited source/version and license. Record capture/retrieval and review dates in ISO 8601 format with timezone. Do not add package images to the repository unless rights and project policy allow it; a controlled reference or hash can be recorded instead.
6. Do not merge duplicate candidates automatically. Retain separate source records and record candidate relationships for human adjudication.

## Identity hierarchy

Assign stable, opaque IDs once and retain them across revisions. Use IDs such as `brand:...`, `family:...`, `variant:...`, `pack:...`; do not derive IDs from mutable display names. Maintain an ID register so spelling corrections do not create new identity. A product variant is the formulation/flavour identity; a pack identity is a sellable quantity/multipack. If uncertain, leave the relevant ID null and set its state to `requires_review`.

| Level | Meaning and annotation rule |
|---|---|
| Brand | Brand printed on or authoritatively associated with the product. Record the exact brand string and a stable `brand_id`. Do not substitute parent company/manufacturer for brand. Multiple printed brands require review and a note. |
| Product family | Consumer-facing line/formulation family shared across flavours/pack sizes (e.g. a brand's named biscuit line). Record evidence-backed family name and `family_id`. Do not group every item from one brand as one family. |
| Exact variant | Distinguishable formulation/flavour/dietary or product form. Record the complete exact name and variant descriptor; assign `variant_id`. Formula changes are separate variants or revisions according to evidence; retain history. |
| Pack identity | Exact declared pack/GTIN combination, including multipack format. Assign `pack_id`. Different net quantities or bundle counts are different pack identities even for the same variant. |

Product names should retain the on-pack name, including brand wording only when printed as part of the name. Keep marketing descriptor/variant separate where the schema has a separate field. Do not “correct” brand or product spelling silently.

## Field-by-field instructions

### Brand, family, variant, flavour and formulation

Capture exact visible wording and evidence reference. Use family only for a clearly shared named product line. Record flavour/formulation only when stated or unambiguously shown on the package. If wording conflicts across pack panels, retain the conflict and set `requires_review`.

### Pack size and multipack count

Copy the declared net quantity as printed, including the original numeric string and unit (`g`, `kg`, `ml`, `L`, `count`, etc.). Store a normalized numeric amount/unit separately when conversion is exact; retain the original unit. Multipack count is the number of individually quantified packs only when the package explicitly states it (e.g. “6 × 20 g”). Distinguish `6 × 20 g` from `120 g` and from six pieces with no declared mass. Do not use serving size as package quantity.

### Barcode / GTIN

Transcribe digits exactly, preserving leading zeroes, and record barcode symbology/source where visible. Normalize by removing only permitted visual separators; never drop leading zeroes. Validate supported GTIN lengths/check digit in the tooling. A failed check digit is a review warning, not permission to change digits. A barcode mismatch between sources is a conflict; do not resolve by selecting the most common value.

### Primary category

Choose one primary category from the versioned `taxonomy_version` and `category` enum in `data/annotation/README.md`. Use the most specific supported leaf, but do not infer a category from nutrition/ingredients alone where product form is unclear. Record the source text/tags separately if useful. For products outside the current taxonomy, use `not_applicable` for this taxonomy and explain in notes; request a taxonomy update rather than forcing the nearest category. The production five-category set is not the annotation taxonomy.

### Ingredients and normalization

Transcribe the full ingredient statement in original order, language and punctuation. Include compound ingredient sublists and parenthetical percentages when legible. Keep precautionary statements (“may contain”) separate from ingredients. If a portion is unreadable, preserve readable text and mark the overall transcription `requires_review` with the unreadable span noted; do not fill from OFF or a different package revision.

Normalize each ingredient mention separately to a canonical term/ID using the versioned dictionary in `data/reference/ingredient_terms.csv`, `ingredient_classes.csv` and `ins_codes.csv` as references. Preserve the raw span and sequence. Record normalization state and dictionary/version/reference. A fuzzy suggestion is not verified normalization; use `requires_review` unless an annotator confirms the mapping. Unknown or ambiguous terms remain unresolved, not deleted. Do not infer health effects or additive function from an ambiguous name.

### Nutrition and serving information

Record each value exactly as printed, including decimal precision, original unit and declared basis. Set one panel basis (`per_100g`, `per_100ml`, `per_serving`, `per_pack`, or other exact printed basis). Store serving size/servings per pack separately. Normalized per-100 g/ml values may be added only with the formula, units and derivation recorded; never replace the original. Do not scale if the panel basis or serving mass/volume is unclear. Keep salt and sodium distinct as printed; any conversion is a derived value, not transcription. A blank nutrient is `not_declared` only after checking the panel; a cropped/blurred panel is `illegible` or `requires_review`.

### Claims and allergens

Transcribe every relevant front/back-of-pack marketing or nutrition claim verbatim, preserving language and qualifiers. Do not evaluate truth as part of transcription. Record allergen “contains” declarations separately from “may contain”/cross-contact statements and from ingredient-derived allergen inference. Do not mark an allergen declaration absent without inspecting the relevant label region. Preserve bold/highlight/contains formatting only when visible and relevant.

### Image/package evidence and provenance

For each evidence item, capture evidence type, a stable reference (controlled storage ID, URL, or file hash), source/owner, observed/capture date, license or permission basis, and which fields it supports. Record all relevant package panels and label/package revision when visible. A product image from a dataset may have different rights from the product data. Do not place a URL or image in the public dataset if source terms prohibit it; retain an approved internal evidence reference instead.

For each source record preserve source name, source-specific record ID, URI where permitted, source snapshot/version or retrieval time, license/attribution, and whether it is primary package/manufacturer evidence or a derivative/crowdsourced source. Record source lineage: OFF, PackSense and Shelfpedia records for the same product are related evidence, not independent confirmations.

## Missing-value states

| State | Meaning | Example |
|---|---|---|
| `verified` | Value was reviewed and supported by the recorded evidence. | Printed “250 g” copied from a clear package image. |
| `missing` | Value is currently unavailable because evidence/source was not obtained. | No package photo was supplied. |
| `illegible` | The field is present in evidence but cannot be read reliably. | GTIN partly obscured in a photo. |
| `not_declared` | Relevant area was inspected and the package/source does not state this field. | No added-sugar value on the nutrition panel. |
| `not_applicable` | The field/concept does not apply under the annotation schema. | Serving count for a product with no serving concept. |
| `requires_review` | Evidence conflicts, identity or interpretation is unresolved, or second review is needed. | Two source records show different pack quantity. |

For `verified`, provide a non-null value (except an explicitly verified empty collection, which must be explained and supported). For the other states, use null/empty only as defined in the data dictionary and provide a note when the reason is not self-evident. A numeric zero is a value only if printed as zero.

## Review, disagreement and adjudication

1. A primary annotator reviews evidence, completes fields and signs with a stable reviewer ID and UTC review timestamp.
2. Double-annotate at least 20% of records (minimum 40 when the set reaches 200), stratified by category, evidence source and language. Also double-review every identity conflict and a sample of high-risk nutrition/ingredient records.
3. Keep both original annotation payloads. Compare field-level normalized values and exact transcription; do not overwrite one annotator with the other.
4. Log disagreement field, each annotation, resolution status and evidence. An adjudicator with a separate reviewer ID resolves only where evidence supports a decision; otherwise retain `requires_review` and exclude that field/record from tasks requiring it.
5. Calculate exact agreement for categorical/identity fields and suitable agreement (e.g. Cohen’s kappa for two categorical reviewers; numeric absolute/relative differences for nutrition) only when sample size and label distribution make it meaningful. Report n, missingness and confidence intervals; do not interpret a metric on a tiny or one-class sample as reliable agreement.
6. Maintain append-only `review_log.jsonl` entries for create, review, disagreement, adjudication and correction events. Every correction references the previous revision and reason. Never rewrite the source package evidence.

## Split eligibility

Only records with stable, reviewed `brand_id`, `family_id`, and `variant_id` can enter grouped splits. Unresolved records remain in the annotation corpus but are excluded and counted in split reports. All source derivatives and packaging revisions of one variant must carry the same `variant_id`; every member of one family must carry the same `family_id`. Use family-grouped splits for the main evaluation and brand-held-out splits as a stricter generalization check. No random row-level split is permitted.
