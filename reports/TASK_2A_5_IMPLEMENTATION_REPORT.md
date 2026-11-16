# Task 2A-5 Implementation Report

## Corrections

- Persisted each normalized product/listing record in `acquisition_observations.jsonl`, alongside the existing three separate retailer price observations per row.
- Added separate count fields for candidate annotations, product/listing records, price observations, and total acquisition records to the JSON quality report, manifest, and CLI summary.
- Made acquisition record IDs deterministic and row-specific using source ID, worksheet row, and a SHA-256 fingerprint of original headers and cell values. Duplicate `Product Submission ID` values remain unchanged and flagged; they no longer collide in record IDs.
- Removed retailer inference from `ImageReference.source_platform`. A product/listing is attributed to Zepto only when its product URL hostname is a Zepto domain. Other hosts leave retailer identity unset. Image source platform remains on each image reference.
- Removed normalized-unit targets from nutrition parsing. Original amounts and units are retained, while normalized values/units stay null without an explicit conversion.
- Updated the quality report and field mapping to document the record split, ID strategy, retailer attribution, and nutrition unit semantics.

## Result for the supplied workbook

| Record type | Count |
|---|---:|
| Candidate annotations | 25 |
| Product/listing acquisition records | 25 |
| Retailer price observations | 75 |
| Total acquisition records | 100 |
| Image references | 125 |

All 100 acquisition record IDs are unique. The manifest and quality report agree on the counts. The 25 annotation records remain candidates; schema validation reports zero errors and zero warnings. The source workbook hash still matches the import manifest.

## Changed files

- `src/acquisition/catalog_workbook.py`
- `scripts/import_product_catalog_candidate.py`
- `tests/test_catalog_workbook_candidate.py`
- `reports/COMPLETE_PRODUCT_CATALOG_QUALITY_REPORT.md`
- `reports/COMPLETE_PRODUCT_CATALOG_FIELD_MAPPING.md`
- `data/annotation/candidate_sources/complete_product_catalog/candidate_annotations.jsonl`
- `data/annotation/candidate_sources/complete_product_catalog/acquisition_observations.jsonl`
- `data/annotation/candidate_sources/complete_product_catalog/image_references.jsonl`
- `data/annotation/candidate_sources/complete_product_catalog/source_workbook_rows.jsonl`
- `data/annotation/candidate_sources/complete_product_catalog/data_quality_report.json`
- `data/annotation/candidate_sources/complete_product_catalog/annotation_validation_report.json`
- `data/annotation/candidate_sources/complete_product_catalog/import_manifest.json`

## Tests

Command:

```text
python -m pytest tests/test_catalog_workbook_candidate.py tests/test_acquisition_foundation.py tests/test_fetch.py -q
```

Result: **47 passed**.

New regression coverage includes 25 synthetic products producing exactly 100 acquisition records, unique/deterministic record IDs across reruns, duplicate submission IDs without collisions, product/listing versus price-observation separation, missing and invalid prices, date-only observations, retailer attribution independent of image platform, and preserving mg/g and kJ/kcal without normalization.

No dependency was installed. The workbook was not modified, and the importer made no network or database requests.
