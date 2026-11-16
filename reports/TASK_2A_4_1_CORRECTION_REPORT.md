# Task 2A-4.1 correction report

## Corrections

- Removed the unsupported `final_annotation_validation_report.json` entry from the consolidation guide. The importer generates `annotation_validation_report.json` after candidate JSONL generation, lists it in `import_manifest.json`, and stores the same filename in `annotation_validator.report`.
- Moved the exact `Biscuits & Cookies` / `Cookies` mapping ahead of the broad `Biscuits & Snacks` heuristic. Broad categories remain unresolved without clear product-name cues; namkeen cues remain review-required, and spices remain unmapped.
- Added a SHA-256 `source_row_fingerprint` over ordered original header/value pairs. It is stored separately from the stable candidate record ID. Added an optional read-only `--compare-to` JSONL input and generated `source_row_changes.csv` to report matching candidate IDs whose source fingerprints changed. Legacy candidates without stored fingerprints are compared using preserved source fields and flagged as reconstructed.

## Verification

Executed only synthetic workbook fixtures in temporary directories; no real-data consolidation was run and no existing candidate annotation or source workbook was written.

```text
python -m pytest tests/test_dataset_consolidation.py tests/test_annotation_tools.py -q
16 passed
```

The regression coverage includes all four requested category cases, report pointer/file consistency, unchanged rerun ID and fingerprint stability, changed source row detection under the same candidate ID, and verification that the prior JSONL remains byte-for-byte unchanged.

## Files changed for this correction

- `scripts/consolidate_product_datasets.py`
- `docs/DATASET_CONSOLIDATION_GUIDE.md`
- `tests/test_dataset_consolidation.py`
- `reports/TASK_2A_4_1_CORRECTION_REPORT.md`

No production application code, database schema, model, or real candidate output was changed by this correction.
