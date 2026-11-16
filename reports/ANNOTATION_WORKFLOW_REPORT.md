# Task 2A-3 annotation workflow implementation report

**Status:** research annotation infrastructure created; no real records were annotated or verified.  
**Date:** 16 November 2026.  
**Production data/schema/application:** unchanged; no dataset imports, dependency installs, model training, commit, push, or deployment.

## Repository evidence reused

- `data/sample/off_india_subset.jsonl` contains 466 real OFF-derived rows (documented from an India bulk-export snapshot dated 12 October 2026). Prior Task 2A reports profile 466 unique barcodes, 438 normalized unique names, 349 ingredient lists, 331 raw pack quantities, 288 quantities parsed by the current parser, and only 55 rows with all ten mapped nutrient fields. It is a crowdsourced reference set, not manually verified ground truth.
- `data/verified/pack_check/pack_check_sheet.csv` has 200 prepared candidates, but zero reviewer/date/pack-found or label-result fields completed. It is an existing review queue, not an annotated set. The new workflow keeps it untouched and can preserve each `off_code`/URL as a source record.
- `data/verified/verified_products_template.csv` is header-only. Existing schema fields in `src/core/schema.py` and `src/database/models.py` provide `Evidence` source labels, product fields, original/normalized nutrients, ordered ingredient text, sources and review timestamps, but no stable brand→family→variant hierarchy. The new research JSONL stays separate rather than adding production columns/migrations.
- Current category mapping has five production categories; `data/reference/category_keywords.csv`, `off_category_map.csv`, `ingredient_terms.csv`, `ingredient_classes.csv` and `ins_codes.csv` are useful references, not gold labels. The research taxonomy is versioned separately and broader.
- Existing evaluation fixtures are small and team-authored: four synthetic HTML pages, 57 phrase labels and 22 hand-worked claim cases. Existing evaluation documentation correctly says they are not independent accuracy claims.
- Existing Task 2A reports were consulted: `DATA_SOURCE_AUDIT.md`, `DATASET_SCHEMA_COMPARISON.md`, `DATA_QUALITY_ASSESSMENT.md`, `ML_FOUNDATION_ASSESSMENT.md` and `DATASET_READINESS_MATRIX.md`.

## Deliverables created

| Path | Purpose |
|---|---|
| `docs/annotation_guidelines.md` | Field-by-field instructions, evidence rules, six explicit missing states, identity hierarchy, transcription/normalization, provenance, review, disagreement and split eligibility. |
| `docs/annotation_data_dictionary.md` | JSONL schema paths, field types, IDs, states, nutrients/units, provenance, revision and split-manifest contract. |
| `data/annotation/README.md` | Isolated versioned layout, proposed 16-leaf taxonomy, source-copy policy and commands. |
| `data/annotation/schema_v1.json` | Versioned structural schema descriptor. |
| `data/annotation/annotation_template.jsonl` | One blank `record_type: template` object with missing values; not a product or annotation. |
| `data/annotation/review_log_template.jsonl` | Blank append-only review event shape; no invented reviewer/event. |
| `data/annotation/splits/.gitkeep` | Keeps the generated-manifest directory present; no research split exists yet. |
| `scripts/validate_annotation_dataset.py` | Standard-library, read-only JSONL validation, missingness/category profile, GTIN check digit/duplicate candidates, near-duplicate warnings, quantity/unit/basis/provenance/reviewer checks. Never merges or rewrites records. |
| `scripts/create_grouped_splits.py` | Deterministic family-grouped and strict brand-held-out split manifest generator. Validates input first, excludes templates and nonverified/unresolved annotations, groups shared families/variants/verified GTIN/source lineage and conservative close-name candidates, then audits leakage and fails if any protected group crosses partitions. |
| `tests/test_annotation_tools.py` | Synthetic-only temporary tests for blank template, explicit synthetic fixture opt-in, deterministic family/brand splits, leakage detection, GTIN duplicate warnings, invalid units and too-few groups. |

The schema/template include no product facts. Any test records are explicitly `synthetic_fixture`, carry no package evidence or reviewer identity, and are skipped unless a test-only opt-in flag is used.

## Validation behavior

The validator emits JSON with included/skipped counts, category distribution, field-state missingness, errors and warnings. Its checks include:

- Required top-level structures and field wrappers, recognized missing state, basic types, category/taxonomy version, quantity and supported units.
- GTIN digit count and check digit; duplicate GTIN and exact/near identity collisions are flagged as review candidates, never automatically merged.
- Original and normalized nutrient values/units, normalized per-100 g/ml basis consistency, nonnegative numeric values and same-basis panels.
- Ordered ingredient sequence, original mention preservation, canonical ID requirement only for verified normalization, and unresolved normalization warnings.
- Source IDs, source role/license and package-evidence reference/license fields; references on verified fields must resolve.
- Record verification state and reviewer/timestamp/package evidence if a record is marked verified.
- Split generation only accepts record-level verified annotations with stable brand/family/variant IDs. It writes a JSON manifest containing input hash, dataset/taxonomy versions, seed, ratios, record membership/counts, exclusions, group component details and leakage audit.

No current real annotation dataset is present, so production-like validation and real split generation correctly remain unavailable. The blank template validates as an empty template, not as a verified product. The grouped split algorithm approximates requested record ratios because whole leakage groups cannot be divided; assess category/source balance in the manifest before using a future split.

## Test evidence

Executed without installing dependencies:

```text
python -m pytest tests/test_annotation_tools.py -q
7 passed in 0.10s

python scripts/validate_annotation_dataset.py data/annotation/annotation_template.jsonl
status: ok; records_included: 0; records_skipped: {"template": 1}; errors: 0; warnings: 0

python -m py_compile scripts/validate_annotation_dataset.py scripts/create_grouped_splits.py tests/test_annotation_tools.py
passed
```

Additional tests verify deterministic seed behavior, every partition populated, family/variant/brand exclusivity in the relevant modes, audit failure when a family is manually placed across train/test, valid UPC check digit, duplicate GTIN warning without merge, rejection of an unsupported pack unit, and refusal when fewer than three independent leakage groups exist. All synthetic test fixtures were created in temporary directories; none were written into the research dataset.

## Limitations and next operation

- No actual package evidence, reviewer records or annotations exist yet. The workflow does not claim that any OFF row has been manually verified.
- Stable `brand_id`, `family_id`, `variant_id` and `pack_id` require a maintained ID register and human decisions; the scripts deliberately do not infer them from names.
- Close-duplicate detection is a conservative heuristic for review, not identity resolution. It can over-group or miss a duplicate; no records are merged.
- Inter-annotator agreement is defined in the guidelines but cannot be calculated until a meaningfully double-annotated set exists.
- The split tool groups same families/variants/verified barcodes/source record IDs and likely close same-brand names. Correct source-lineage linking still depends on annotators assigning shared stable IDs and preserving source references.
- No full-project test suite was run because only research tooling was changed; the targeted seven tests and CLI/template checks passed.

Next, populate 200–300 rows from real package/manufacturer evidence using the existing pack-check queue as a candidate list, double-annotate at least 20% (minimum 40 at 200 rows), adjudicate conflicts without forcing unresolved values, validate, freeze a version, then generate family and brand-held-out manifests.
