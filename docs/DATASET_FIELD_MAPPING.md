# Dataset field mapping

**Mapping version:** `1.0`, target annotation schema `1.0`, taxonomy `india-packaged-food-v1`. No source column is treated as package-verified unless physical/package evidence is separately reviewed.

## Workbook and worksheet routing

| Source workbook | Product worksheet | Rows present | Handling |
|---|---|---:|---|
| `misleading_indian_food_products.xlsx` | `Misleading Food Claims` | 22 | Each nonempty product row becomes a separate candidate. Blank trailing header is retained as `column_8`. |
| `indian_packaged_food_annotation_records.xlsx` | `Dataset Annotation Records` | 25 | Each nonempty product row becomes a separate candidate. |
| `master_verified_food_corpus.xlsx` | `Verified Research Corpus` | 38 | Each nonempty product row becomes a separate candidate. Source verification wording is retained as an assertion only. |
| `master_verified_food_corpus.xlsx` | `Data Collection Checklist` | 38 | Joined as supplemental source-row provenance by Product ID or exact name+brand; never treated as product evidence and does not create a second candidate when matched. Current cells say Pending. |

The supplied books all include title/information rows before the header and an empty separator row; the importer locates the first row containing Product Name and Brand, then preserves Excel source row numbers. Empty rows are counted and skipped. It does not treat declared workbook totals/titles as verified counts.

## Column mapping

| Workbook column (aliases accepted) | Candidate output path | State / interpretation |
|---|---|---|
| Product ID / ID / Record ID | `import_metadata.source_record_identifier`, `evidence.source_records[].external_id` | Preserved as source-local identifier; never treated as barcode. |
| Product Name / Name | `identity.product_name` and normalized candidate name | `requires_review` with source-row reference; exact package name not confirmed. Original cell preserved. |
| Brand / Brand Name | `identity.brand.name` and normalized candidate brand | `requires_review`; no stable brand ID is generated. |
| Category / Product Category | `normalized_fields.source_category_whitespace_normalized`, `normalized_fields.candidate_category`, `identity.category` | Source category retained. Taxonomy map is a proposed value in `requires_review`; no forced mapping for ambiguous categories. |
| Front-of-Pack Claim / Claim | `research_assertions.front_of_pack_marketing_claim` | Source claim only. `label.claims` stays missing because the package was not inspected. |
| Actual Ingredients / Reality / Ingredients | `research_assertions.reported_ingredient_or_reality_description` | Source-provided descriptive assertion only. `label.ingredients_original` and normalized ingredients stay missing. |
| Primary Misleading Concern / Concern / Allegation | `research_assertions.alleged_misleading_concern` | Allegation/assertion; not encoded as truth or a binary misleading label. |
| Regulatory / Scrutiny Status | `research_assertions.reported_regulatory_or_scrutiny_statement` | Verbatim source statement; not evidence of an official notice or ruling. |
| Verification Status | `research_assertions.source_claimed_verification_status` | Source claim preserved. Actual pipeline status remains `unverified`. |
| Evidence Source / Evidence Reference | `research_assertions.reported_evidence_reference_text` | Source text only; not converted to a URL, citation or verified evidence. |
| Checklist photo columns | `supplemental_source_rows[].source_fields[]` | Pending/status values preserved only; they do not create package evidence. |
| All other columns | `source_fields[]` | Every cell preserved with one-based column index, original header, original value and whitespace-normalized value. |

All 11 nutrient fields, nutrition basis, serving details, claims-as-label, allergens, GTIN and pack quantity are explicitly represented with the annotation schema’s `missing` state unless a future source provides an actual evidenced value. No such values are fabricated from the research descriptions.

## Category mapping rules

The taxonomy is the 16-category research taxonomy listed in `data/annotation/README.md`, not the narrower production database enum.

| Source category | Candidate mapping rule | Status |
|---|---|---|
| `Instant Noodles` | `noodles_pasta` | `mapped_requires_review` |
| `Fruit Juices`, `Health Drinks` | `packaged_beverages` | `mapped_requires_review`; health-drink category is not a precise product form. |
| `Breakfast Cereals` | `breakfast_cereals_muesli`; name containing oats/millet may propose `oats_millet_products` | `mapped_requires_review` |
| `Dairy`, `Dairy Alternatives` | `dairy_dairy_alternatives` | `mapped_requires_review`; source framing can be inaccurate. |
| `Ready-to-Eat` | `ready_to_eat_ready_to_cook` | `mapped_requires_review` |
| `Protein Bars` | `protein_bars_snacks` | `mapped_requires_review` |
| `Sauces & Condiments` | `sauces_condiments_dips`; product name “jam” may propose `spreads`, “soup” may propose ready-to-eat | `mapped_requires_review` |
| `Staples` | `packaged_staples_mixes` | `mapped_requires_review` |
| `Biscuits & Snacks` | Product-name cue can propose biscuits/cookies, chips/savoury snacks, or namkeen | `mapped_requires_review`; broad source label requires review. |
| `Spices`, `Honey & Sweeteners`, `Spices & Staples`, unknown | No forced mapping | `requires_review`; spices are not silently treated as staples. |

## Identity and duplicate candidate rules

Stable candidate ID is SHA-256 over workbook basename, worksheet, Excel row number and source-local Product ID (truncated with a `cand_` prefix). It remains the same for repeated imports of the same row layout; no source files are changed. Source-record IDs use the same stable ingredients with a `src_` prefix.

Exact normalized brand+product-name pairs across rows are `possible_duplicate`. Same-brand names with similarity ≥0.94 are also candidates. For Bhujia names sharing a family token but differing explicit descriptors (e.g. Aloo, Nagpur, Sev), the relationship is marked `distinct_variant` rather than merged. All other candidates remain `unresolved`. `confirmed_duplicate` is never assigned by code. Pack size and GTIN are unavailable, so name+brand similarity cannot confirm physical identity.

The Knorr row in `misleading_indian_food_products.xlsx` has a blank Front-of-Pack Claim cell and text in the unheaded final column. The importer flags `alignment_suspected`, preserves both exact positions, leaves the claim field missing and places the row in the suspicious-record report. It does not move the text.
