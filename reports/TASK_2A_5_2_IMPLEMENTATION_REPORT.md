# Task 2A-5.2 Implementation Report

## Correction

When product URL hostname supports Zepto attribution, `listing.retailer_name` now uses provenance from the exact `Product source URL` cell. `input_locator` identifies the cell, `raw_value` contains the cell URL, and `source_url` matches both the attributed URL and `listing.listing_url.value`. Unsupported or missing product URLs leave retailer attribution unknown. Image metadata is not used to infer the retailer. Retailer names on price observations continue to come from their respective price-column context.

The importer version is `complete-product-catalog/1.2`.

## Regression and release checks

- Zepto URL: retailer attribution and provenance point to `Sheet1!row:2 / Product source URL`; raw and source URLs match the listing URL.
- Unsupported domain: retailer attribution remains null even when image metadata contains a platform name.
- Missing URL: retailer attribution and listing URL remain null.
- Product/listing and price record IDs: all 100 IDs match the pre-correction release; all remain unique.
- Release counts: 25 product/listing records, 75 price records, 100 acquisition records total.
- Candidate annotation validation: pass, zero errors and warnings.
- Source workbook SHA-256: `66b23c65bad489ff3ac4ee150d14c578e949d708ef580f6d4883a8a9a6b5712f` (matches manifest).

## Changed files

- `src/acquisition/catalog_workbook.py`
- `tests/test_catalog_workbook_candidate.py`
- `reports/COMPLETE_PRODUCT_CATALOG_FIELD_MAPPING.md`
- `reports/TASK_2A_5_2_IMPLEMENTATION_REPORT.md`
- Regenerated files in `data/annotation/candidate_sources/complete_product_catalog/`: `candidate_annotations.jsonl`, `acquisition_observations.jsonl`, `image_references.jsonl`, `source_workbook_rows.jsonl`, `data_quality_report.json`, `annotation_validation_report.json`, and `import_manifest.json`.

## Focused tests

```text
python -m pytest tests/test_catalog_workbook_candidate.py tests/test_acquisition_foundation.py tests/test_fetch.py -q
50 passed
```

The supplied workbook was not modified. No images were downloaded, websites accessed, database/schema changes made, dependencies installed, or candidates promoted.
