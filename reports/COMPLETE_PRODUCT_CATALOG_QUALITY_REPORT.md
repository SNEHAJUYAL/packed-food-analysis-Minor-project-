# Complete Product Catalog Candidate Audit

## Scope and handling

Audited `Complete_Product_Catalog_With_JSON_Photos.xlsx` as a separate candidate source. The source workbook was opened read-only. Its product rows were not merged into the existing verified corpus or production database. No image was downloaded and no retailer URL was requested. The generated records remain `candidate` / `unverified` and are not training data.

The import release is under [`data/annotation/candidate_sources/complete_product_catalog/`](../data/annotation/candidate_sources/complete_product_catalog/). It contains the original workbook cell snapshot for both sheets, candidate annotations, price-observation candidates, parsed image references, validation reports and a manifest. The manifest records the source workbook SHA-256. The source row locator is the worksheet and Excel row number; each product annotation also stores a deterministic source-row fingerprint.

## Workbook and preservation results

| Check | Result |
|---|---:|
| Worksheets | 2 (`Sheet1`, `Price & Category Summary`) |
| Product records | 25 |
| Unique product submission IDs | 25 / 25 (FP001–FP025) |
| Product-sheet columns | 22 |
| Nonempty rows retained across both sheets | 45, including headers/title/summary and formula cells |
| Product fields populated in source | 22 / 22 fields for every product row |
| Image JSON references parsed | 125 / 125 expected (five per product) |
| Product/listing acquisition records | 25 (one per product row) |
| Retailer price observations retained separately | 75 (three per product row) |
| Total acquisition records in `acquisition_observations.jsonl` | 100 |
| Source price-check dates retained as date-only values | 25 / 25 |
| Annotation schema validation | Pass: 25 records, 0 errors, 0 warnings |

The summary sheet's formulas are retained as formula strings; cached formula results are not recalculated. The source file itself was not changed. Product/listing records and price observations share the JSONL file but remain distinguishable: product/listing records have no `observation`; price records do. The report and manifest carry separate counts for each type.

## Validation findings

### Barcodes

Barcode validation distinguishes text cells from numeric Excel cells. For this workbook, 24 barcode cells are numeric and one is text; the text cell passes the GTIN checksum check. Numeric cells are preserved as numbers in the source snapshot and acquisition candidate, flagged `numeric_barcode_requires_review`, and omitted from the string-typed annotation GTIN candidate while their raw values remain in source fields and barcode metadata. No leading zeroes are reconstructed. Numeric GTIN values also trigger the generic acquisition validator's invalid-type `invalid_gtin` warning; they are not counted as checksum failures. A checksum-valid text value remains a candidate, not a verified product identity.

### Category, pack and ingredients

Source category counts are in `data_quality_report.json`. Fourteen records have no sufficiently confident candidate mapping to the existing category taxonomy and remain unmapped for review. The source category text remains preserved. Pack text is preserved for all 25; 21 parse as grams and four as millilitres. Seven contain a stated quantity range and are flagged for review; parsed quantities are candidate interpretations only. Ingredient transcription text is present for all 25, but none is independently package-verified or ingredient-normalized.

### Nutrition

Nutrition text is present for all 25 records and states a per-100-g/ml basis. The conservative text parser recognized 230 nutrient fields across the dataset. Original panel text and original nutrient amounts/units (including mg/g and kJ/kcal) are retained. No normalized amount or unit is populated because this importer performs no nutrient unit conversion.

### Images and retailer evidence

All 125 image references were parsed into structured records retaining `product_id`, PVID, image type/index, source platform, URL, MIME type/status and source-cell provenance. Their `source_platform` describes image provenance only. A product/listing retailer is set to Zepto only when the product URL host is a Zepto domain; image-hosting platform is never used to infer retailer identity. Other/unsupported listing URL hosts leave the product/listing retailer null. URLs were syntax-checked as HTTP(S) only; reachability, image contents and product association were not independently checked.

The workbook has one source product URL per row (Zepto). Individual product evidence URLs are absent for Blinkit and Swiggy Instamart for all 25 products (50 missing retailer-specific URLs total). Workbook source notes are preserved as claims, not treated as verification evidence.

### Prices and dates

Blinkit, Zepto and Swiggy Instamart price columns are retained as separate candidate price records. This workbook has 75 populated positive numeric values, all counted as populated-but-unverified price observations; it has zero missing and zero invalid price placeholders. Missing and invalid values remain null placeholders in the existing candidate record structure and are counted separately; they are not described as collected price observations. The workbook's indicative planning range is retained only in original source fields and is not substituted for a retailer price. Price values use INR based on the rupee-denominated source headers. The supplied date is stored as `observed_date`; `observed_at` and PIN code remain null. Import execution time is separately recorded as import provenance, not as a source collection time.

## Issues summary

The machine-readable report lists 119 issues: 50 absent Blinkit/Instamart listing URLs, 24 numeric-barcode review flags, 24 generic invalid-GTIN-type validation flags for those numeric cells, 14 unmapped categories, and seven ranged pack sizes. Repeated validation messages are deduplicated using source-row identity, product-record identity, field path, code and message; matching issues from distinct workbook rows remain separate. No records were automatically merged or promoted to verified status.

## Outputs

- `candidate_annotations.jsonl` — 25 isolated annotation-schema records.
- `acquisition_observations.jsonl` — 25 product/listing records and 75 separate retailer price-observation records (100 total; candidate status). Record IDs include the source row number and source-row fingerprint, so duplicate submission IDs cannot collide and unchanged reruns are deterministic.
- `image_references.jsonl` — 125 structured image references.
- `source_workbook_rows.jsonl` — all nonempty original cells/formulas from both sheets with sheet/row/column provenance.
- `data_quality_report.json` and `annotation_validation_report.json` — findings and schema validation.
- `import_manifest.json` — source hash, importer version and output inventory.

## Limitations

Source license and original data collection provenance are not specified in the workbook. The claims of product verification in its notes were not independently validated. No pack/photo/ingredient/nutrition/barcode/price verification, image retrieval, price recency check, product matching, or category adjudication was performed. Candidate records must not be treated as verified training examples without a separate evidence-based review.

## Test results

Synthetic workbook tests and relevant acquisition/fetch tests: **47 passed**. Coverage includes a 25-row/100-record release, duplicate submission IDs, separate product and price record types, missing/invalid prices, date-only observations, image-vs-retailer attribution, and nutrition mg/g and kJ/kcal semantics. Fixtures are clearly synthetic and are not represented as real products. The actual workbook import was checked against the existing annotation schema: **25 records, 0 errors, 0 warnings**. See the Task 2A-5 implementation report for details.
