# Annotation dataset data dictionary

**Schema version:** `1.0`  
**Canonical schema file:** `data/annotation/schema_v1.json`  
**Record encoding:** UTF-8 JSON Lines; one JSON object per line.  
**All timestamps:** ISO 8601 with timezone; use UTC for reviewer actions.

## Top-level record

| Field | Type | Required | Definition |
|---|---|---:|---|
| `schema_version` | string | yes | Schema contract, currently `1.0`. |
| `record_type` | enum | yes | `annotation`, `template`, or `synthetic_fixture`. Templates and synthetic fixtures never count as verified product data. |
| `record_id` | string | yes for annotation | Stable annotation-record ID; immutable across revisions. Source copies of the same physical variant may have separate records but share `variant_id` and `family_id`. |
| `dataset_version` | string | yes | Version of the annotation release (e.g. `0.1.0`). Do not change it in place for a released dataset. |
| `taxonomy_version` | string | yes | Version of the primary-category taxonomy. Current proposed version: `india-packaged-food-v1`. |
| `identity` | object | yes | Product identity and brand→family→variant→pack hierarchy. |
| `label` | object | yes | Original package text, ingredients, nutrition, serving, claims and allergen declarations. |
| `evidence` | object | yes | Source records and package/manufacturer evidence references with licenses. |
| `verification` | object | yes | Record-level workflow status; this does not replace field-level states. |
| `review` | object | yes | Annotator/reviewer IDs, dates, second review, disagreements and adjudication. |
| `revision` | object | yes | Revision number, prior record hash/ID and change reason. |

## Field wrapper and missing states

Every package-derived scalar/list field uses:

```json
{"value": null, "state": "missing", "evidence_refs": [], "note": null}
```

`state` must be one of `verified`, `missing`, `illegible`, `not_declared`, `not_applicable`, `requires_review` (defined in [annotation guidelines](annotation_guidelines.md)). `verified` requires a value and at least one evidence reference. Other states normally use `value: null`; `requires_review` may retain a proposed value, but it is not accepted ground truth. A verified empty list is allowed only when evidence proves no items/declarations and the note explains the inspection.

## Identity fields

| JSON path | Type | Description |
|---|---|---|
| `identity.product_name` | field<string> | Exact on-pack/product display name. |
| `identity.brand.name` | field<string> | Printed/authoritatively supported brand string. |
| `identity.brand.brand_id` | stable string or null | Opaque stable brand identifier, assigned from a maintained ID register. |
| `identity.family.name` | field<string> | Named consumer product line; do not equate brand and family. |
| `identity.family.family_id` | stable string or null | Stable family grouping, shared by flavor/pack variants. Required for grouped splits. |
| `identity.variant.name` | field<string> | Exact variant identity/name. |
| `identity.variant.flavour` | field<string> | Flavor as printed. |
| `identity.variant.formulation` | field<string> | Formulation/product-form descriptor as printed. |
| `identity.variant.variant_id` | stable string or null | Stable formulation/flavour identity across packs and source copies. Required for splits. |
| `identity.pack.pack_id` | stable string or null | Stable specific sellable package identity; different sizes/bundles use different IDs. |
| `identity.pack.gtin` | field<string> | Original barcode digits and evidence. Preserve leading zeroes. |
| `identity.pack.declared_quantity` | field<object> | `{original, amount, unit}`; exact declared pack quantity and optional normalized amount/unit. |
| `identity.pack.multipack_count` | field<integer> | Explicit number of packs in a multipack; do not derive from total weight. |
| `identity.category` | field<string> | One primary category from `taxonomy_version`, or appropriate missing state. |

`brand_id`, `family_id`, `variant_id` and `pack_id` are strings, not names. They are not generated automatically by the validator. Unresolved identity leaves the ID null and prevents that record from grouped splitting.

## Label fields

| JSON path | Type | Description |
|---|---|---|
| `label.ingredients_original` | field<string> | Verbatim full ingredients text, preserving language, punctuation and order. |
| `label.ingredients_normalized` | array<object> | Ordered mentions with `sequence`, `original_text`, `canonical_name`, `canonical_id`, `state`, `dictionary_version`, `evidence_refs`, and `note`. Unknown/ambiguous mentions stay unresolved. |
| `label.nutrition.basis` | field<string> | Exact stated basis; normalized enum may be `per_100g`, `per_100ml`, `per_serving`, `per_pack`, or `other`. |
| `label.nutrition.panel_source_text` | field<string> | Original panel heading/basis text, if separately captured. |
| `label.nutrition.nutrients.<name>` | object | `{original_value: field, normalized_value: field, original_unit: string|null, normalized_unit: string|null, normalized_basis: per_100g|per_100ml|null}`. Retain exact original and normalized value separately. |
| `label.serving.size` | field<object> | Original amount/unit and optional normalized amount/unit. |
| `label.serving.servings_per_pack` | field<number> | Printed serving count per pack, not inferred. |
| `label.claims` | field<array<string>> | Verbatim claims; do not adjudicate truth in transcription. |
| `label.allergens.contains` | field<array<string>> | Explicit “contains” declarations only. |
| `label.allergens.precautionary` | field<array<string>> | “May contain”/cross-contact declarations. |
| `label.allergens.other_text` | field<string> | Other exact allergen statement, when not represented by the two lists. |

Every record must include all canonical nutrient keys (`energy`, `protein`, `carbohydrate`, `total_sugars`, `added_sugars`, `total_fat`, `saturated_fat`, `trans_fat`, `fibre`, `sodium`, and `salt`) with explicit original/normalized value states, even when absent from the package. Canonical normalized units: kcal for energy, mg for sodium, g for other masses. The original unit/value remains mandatory when known. `sodium` and `salt` are distinct keys.

## Evidence, review and revision

`evidence.source_records[]` keeps each original source record with `source_name`, `external_id`, `uri`, `snapshot_or_retrieved_at`, `license`, `attribution`, `source_role` (`primary`, `derivative`, `crowdsourced`, `other`) and `derived_from[]`. `evidence.package_items[]` keeps `evidence_id`, `kind`, `reference`, `sha256`, `captured_at`, `license_or_permission`, `owner`, `fields_supported[]`, and `note`. Never invent a URI, license, reviewer or capture event.

`verification.status` is `unverified`, `partially_verified`, `verified`, or `requires_review`. `review.primary_reviewer_id` and `review.primary_reviewed_at` identify the first review; second reviewer fields may be null. `review.disagreements[]` and `review.adjudication` retain unresolved/resolved differences. `review.log_refs[]` points to append-only events in `data/annotation/review_log.jsonl`.

`revision.number` starts at 1; `revision.previous_record_sha256` is null for initial records; `revision.change_reason` describes the change. Preserve the previous version in the versioned dataset release. Corrections must not erase original evidence.

## Split manifest

The split script emits JSON containing schema/dataset/taxonomy versions, source file SHA-256, split mode (`family` or `brand_held_out`), seed, requested proportions, eligible/excluded counts, group key, record IDs per partition, group assignments, and a leakage audit. Do not include package images or source data in the manifest. The manifest is a generated evaluation artifact and must be regenerated only from a frozen dataset release.
