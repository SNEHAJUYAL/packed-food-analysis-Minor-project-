# Task 2A-4 dataset consolidation report

**Completed:** 16 November 2026  
**Operation:** read-only Excel ingestion into research candidate files under `data/annotation/imported_candidates/`. No PostgreSQL import, model training, external API access, dependency installation, or source-workbook modification occurred.

## Inputs inspected and imported

The two workbooks named in the task document were found in Downloads. The separately supplied `master_verified_food_corpus.xlsx` was also inspected and included as an additional source, not as a replacement for either workbook.

| Workbook | Product worksheet rows imported | Supplemental rows | Findings |
|---|---:|---:|---|
| `misleading_indian_food_products.xlsx` | 22 | 0 | 8 columns, including one unheaded final column. Knorr Classic Mixed Vegetable Soup has a blank front-of-pack claim and text in the unheaded final cell. |
| `indian_packaged_food_annotation_records.xlsx` | 25 | 0 | 5 columns. Includes products that overlap with the other source workbooks. |
| `master_verified_food_corpus.xlsx` | 38 | 38 | Product sheet has 10 columns. Its 38-row photo checklist was linked to the product rows by source ID/name/brand and retained as supplemental source provenance, not duplicated as product candidates or treated as photos. |
| **Total candidates** | **85** | **38 linked** | Product source rows remain separate; no records were merged. |

Workbook title-row claims such as “Total Unique Products” or “Verified” were not treated as ground truth. Rows are identified by workbook, worksheet and Excel row. Candidate IDs are stable hashes of workbook basename, worksheet, row and source-local product ID. All original cells remain in `source_fields[]`; whitespace-normalized strings are separate.

Profiled missing source cells on the product sheets: product name, brand and category are present in all 85 rows; the misleading-claims workbook has 1 blank front-of-pack claim and 21 empty cells in the unheaded trailing column; the 25-row annotation workbook has no blank product columns; the master corpus has 1 blank `Evidence Source` cell. All 38 rows in the master photo checklist say `Pending` in each of its four photo columns (152 pending cells; no photos supplied). Product-sheet fields are text, with blank cells retained as null rather than inferred.

## Consolidation results

| Measure | Result |
|---|---:|
| Candidate records | 85 |
| Possible duplicate candidate groups | 37 |
| Exact/close same-brand duplicate candidate pairs | 45 |
| Candidate rows labelled `possible_duplicate` | 78 |
| Distinct-variant relationship pairs | 5 |
| Candidate rows marked `distinct_variant` | 2 |
| Candidate rows otherwise unresolved | 5 |
| Unmapped/uncertain category mappings | 10 |
| Candidate category mappings requiring review | 75 |
| Category review queue rows | 85 |
| Records in claim verification queue | 85 |
| Malformed/suspicious records | 1 |
| Annotation validator | **0 errors, 0 warnings across 85 candidates** |

The 37 groups and 45 pairs are **review candidates, not confirmed duplicates**. Exact-name/brand repeats of Maggi 2-Minute Noodles, Kissan Mixed Fruit Jam, Paper Boat Aam Panna, and Nestlé Milkmaid were flagged across sources. No candidate received `confirmed_duplicate`. Haldiram’s Aloo Bhujia, Nagpur Bhujia and Bhujia Sev were not merged; differing Bhujia descriptors are represented as distinct-variant review relationships where observed.

Category mapping remains unverified throughout. Seventy-five rows have a proposed taxonomy leaf with status `mapped_requires_review`; ten rows remain unmapped with `requires_review` (notably spices, honey/sweeteners and ambiguous “Spices & Staples”). The mapping review CSV includes all 85 rows, including candidates that have a proposed leaf. This follows the rule not to silently place spices into staples.

All 85 rows are in the claim queue because they contain source-provided claim, ingredient/reality, concern, or regulatory/scrutiny assertions. These are preserved as research assertions; the pipeline status is `unverified` even where an input workbook says “Verified …”. No binary misleading/not-misleading label was produced.

### Knorr row handling

The `Misleading Food Claims` sheet’s Excel row 22 contains no value in `Front-of-Pack Claim`, while its unheaded `column_8` contains “Chef's Best / 100% Real Vegetables”. The row is flagged in `malformed_suspicious_records.csv` and with `malformed_flags.alignment_suspected`. Both original cell positions are preserved. The text was not shifted into the claim field. A separate, well-formed Knorr row in the master workbook remains a separate candidate.

## Evidence and annotation status

- All candidates have `annotation_status: pending_review` and `verification.status: unverified`.
- Source product names, brands and category mappings are `requires_review`; no stable brand/family/variant/pack IDs were invented.
- Reported “Actual Ingredients / Reality” is stored under `research_assertions`, not as package transcription. `label.ingredients_original` remains `missing` for every candidate.
- GTIN, pack size, multipack count, nutrition, serving information, label claims, allergens and package-image evidence are missing because these workbooks do not provide physically verified package evidence.
- Source licenses/attribution are marked `unknown` because the workbooks did not establish them. Source snapshot/retrieval dates remain `unknown`. The fixed import timestamp (`2026-11-16T00:00:00Z`) is an explicit reproducibility parameter, not a package capture, source collection or review date.
- The master workbook’s verification wording is retained as `research_assertions.source_claimed_verification_status`; it does not alter pipeline verification. This is especially important because its collection checklist marks all 38 front, back/ingredient, nutrition and barcode photo fields `Pending`.

## Deliverables

Created the import pipeline, field mapping and user guide, tests and this report. Generated candidate files are listed in `import_manifest.json`:

- `consolidated_annotation_candidates.jsonl`
- `consolidated_product_candidates.csv` and `.xlsx`
- `duplicate_candidates.csv`
- `category_mapping_review.csv`
- `claim_verification_queue.csv`
- `malformed_suspicious_records.csv`
- `annotation_validation_report.json`
- `final_annotation_validation_report.json`
- `import_manifest.json`

The review CSV/XLSX include exact original cell data and normalized candidate values in separate columns/fields. The master checklist’s status text is preserved as supplemental source data; no package item is fabricated.

## Validation and tests

Executed:

```text
python -m pytest tests/test_dataset_consolidation.py tests/test_annotation_tools.py -q
11 passed

python -m py_compile scripts/consolidate_product_datasets.py \
  scripts/validate_annotation_dataset.py scripts/create_grouped_splits.py \
  tests/test_dataset_consolidation.py
passed

python scripts/validate_annotation_dataset.py \
  data/annotation/imported_candidates/consolidated_annotation_candidates.jsonl \
  --report data/annotation/imported_candidates/final_annotation_validation_report.json
status ok; 85 records; 0 errors; 0 warnings
```

Synthetic XLSX tests cover two-source import, missing optional columns, empty rows, duplicate candidates, distinct Bhujia variants, suspected Knorr misalignment, uncertain spices mapping, missing GTIN/pack size, stable IDs on repeat imports, create-only output protection, existing-validator compatibility, preserved unverified claim state, supplemental checklist linking and original-cell retention. The real imported JSONL also passed the existing validator. No full application test suite was run because application behavior was not changed.

## Reproduction command

```bash
python scripts/consolidate_product_datasets.py \
  --input /Users/snehajuyal/Downloads/misleading_indian_food_products.xlsx \
  --input /Users/snehajuyal/Downloads/indian_packaged_food_annotation_records.xlsx \
  --input /Users/snehajuyal/Downloads/master_verified_food_corpus.xlsx \
  --out-dir data/annotation/imported_candidates \
  --import-timestamp 2026-11-16T00:00:00Z
```

The output directory is create-only. For a rerun, select a fresh output directory; stable candidate IDs will match for identical row layouts.

## Limitations

The workbooks provide curated descriptive content and allegations, not independently checked package labels. No GTIN, exact package size, nutrition panel, serving size, images, official source URLs, collection dates or reviewer identities were supplied. The exact source claims, purported evidence references and regulatory/scrutiny text still require independent verification before any consumer-facing use or task-specific training. The duplicate matcher is intentionally conservative and may miss true duplicates or flag different packs; human review is required. This task prepared candidates only and did not create verified ground truth.
