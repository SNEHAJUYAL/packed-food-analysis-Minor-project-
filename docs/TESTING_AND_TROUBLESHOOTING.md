# Testing and troubleshooting

## 1. Results of the consolidation run (16 November 2026, Mac, Python 3.13.9, Node 22)

| Check | Command | Result |
| --- | --- | --- |
| Python tests (SQLite) | `./run.sh test` (run as `python -m pytest -q` with `PYTHONPATH=src`) | **242 passed** in 11.4 s, including both XLSX-dependent modules |
| Frontend tests | `./run.sh test-web` (Vitest + Testing Library) | **47 passed**, 7 files |
| TypeScript | `cd web && npx tsc --noEmit` | exit 0 |
| ESLint | `cd web && npm run lint` | exit 0 |
| Whitespace | `git diff --check` | clean |
| Alembic | `alembic current` | `0002 (head)` |
| Annotation validator | `scripts/validate_annotation_dataset.py …consolidated_annotation_candidates.jsonl` | ok, 85 records, 0 errors, 0 warnings |
| Live API smoke test | `curl` on `/api/health`, `/api/products`, `/api/reference/categories`, `/api/reference/methodology`, `/openapi.json` | all 200; 11 routes listed |
| Source policy, live | candidate preview for a Blinkit URL | 403, `status: blocked`, `unsupported_source`, no request to Blinkit |
| Web pages, live | `/`, `/products`, `/compare`, `/methodology` | all 200 |
| CLI | `./run.sh analyse tests/fixtures/cereal_jsonld.html` | overall 69, grade C |

**Timing caveat.** The Python suite was run at about 21:39 IST. At 21:41 another process edited
`src/services.py`, `src/acquisition/registry.py`, `tests/test_api_db.py` and
`tests/test_product_url_acquisition.py`, and the web UI was being redesigned. Re-run at 21:53 IST:
Python **243 passed**, frontend **47 passed**, TypeScript exit 0, but **ESLint reported 2 errors** in files
under active editing (`AnalyzeForm.tsx:275`, `AppShell.tsx:88`). Re-run `npm run lint` once that work is
finished.

Not run: PostgreSQL-backed Python tests (`TEST_DATABASE_URL`), `npm run build`, Docker Compose, the hosted
Vercel deployment, the live retailer audit (`python -m evaluation.retailer_audit`).

Earlier task reports gave 100 / 74 / 96 focused backend tests and 44 / 47 frontend tests for the
2A-6.x tasks, and 208 broader Python tests with two XLSX modules excluded. Those were subsets; the full
suite now has 242 tests across 22 files and the frontend 47 across 7 files.

## 2. Test inventory

| File | Tests | Covers |
| --- | ---: | --- |
| `test_fetch.py` | 32 | SSRF checks, redirects, robots.txt, size/timeout, error mapping |
| `test_api_db.py` | 25 | API + database routes, policy behaviour, compare, alternatives |
| `test_extraction.py` | 25 | JSON-LD, HTML table, normalisation |
| `test_scoring.py` | 22 | Sub-scores, weights, worked example, grades |
| `test_units.py` | 18 | Quantities, pack sizes, kJ/kcal, salt/sodium |
| `test_upload.py` | 16 | Photo and saved-page uploads, corrections |
| `test_product_url_acquisition.py` | 14 | Candidate service, provenance, image references, conflicts |
| `test_claims.py` | 13 | FSSAI claim rules |
| `test_acquisition_foundation.py` | 11 | Models, registry fail-closed, validation, dry run |
| `test_catalog_workbook_candidate.py` | 10 | Catalogue importer (needs openpyxl) |
| `test_ingredients.py` | 9 | Splitting, INS, matching, allergens |
| `test_dataset_consolidation.py` | 9 | Workbook consolidation (needs openpyxl) |
| `test_annotation_tools.py` | 7 | Validator and grouped splits |
| `test_evaluation.py` | 6 | Metric code |
| `test_product_url_api.py` | 6 | Candidate endpoint statuses |
| `test_label_ocr.py`, `test_llm_fallback.py`, `test_pipeline_api.py` | 4 each | OCR parsing, grounding rule, pipeline |
| `test_ingest.py` | 3 | OFF ingestion |
| `test_ocr_nlp_benchmark.py`, `test_pack_check.py` | 2 each | Benchmarks, pack-check scoring |
| `test_prices.py` | 1 | Price import |

Frontend: `ReportView` 14, `UploadForm` 8, `AnalyzeForm` 7, `CompareAndMethodology` 6, `LiveShapes` 4,
`AlternativesPanel` 3 (`it`/`test` blocks).

All tests use synthetic fixtures and mocked network calls; none make live product requests.

## 3. How to test each feature by hand

| Feature | Try |
| --- | --- |
| Source blocking | Preview a Blinkit URL → `unsupported_source` |
| Candidate preview | Preview an OFF product page → unverified panel, nothing saved (`/products` count unchanged) |
| Saved page | Upload a saved `.html` → report says user-supplied and unverified; extraction log shows "llm-fallback skipped: disabled for user-supplied saved pages" |
| Photo OCR | Upload a label photo → `transcript` step in the extraction log |
| Manual entry | Enter a product without nutrition → status *insufficient data*, no grade |
| Missing ≠ zero | Any OFF product with missing fibre shows "unknown" |
| Claims | A cereal named "High Protein" with 7 g protein → potential inconsistency |
| Alternatives | Switch preference; with no better product, the "no stored product … does better" message |
| Compare | Mixed categories → 422 "Compare products from one category" |

## 4. Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| "The analysis service (API) is not running" | API not started | `./run.sh api` |
| `database_unavailable` (503) / health shows `"database":"unavailable"` | PostgreSQL stopped or wrong `DATABASE_URL` | `/Library/PostgreSQL/18/bin/pg_isready`; check `.env`; `./run.sh migrate`; `./run.sh seed` |
| `psql: command not found` | EDB install not on PATH | Use `/Library/PostgreSQL/18/bin/psql -U postgres` |
| `ModuleNotFoundError: openpyxl` | Older environment without it | `./run.sh setup` (now in `requirements.txt`) or `.venv/bin/pip install openpyxl` |
| `photo_reader_missing` (503) | No Tesseract and no API key | `brew install tesseract`, restart the API |
| `unsupported_source` (403) | Host not authorized | Use upload or manual entry |
| `robots_disallowed` (403) | Site's robots.txt forbids the page | Use upload; never bypass |
| `source_fetch_failed` (502) | Network, timeout or non-HTML | Retry later or upload |
| `product_extraction_failed` (422) | Page has no product data | Upload label images or enter manually |
| `rate_limited` (429) | More than 10 analyses a minute | Wait a minute |
| `too_large` (413) / `length_required` (411) | Upload over 8 MB image / 5 MB page, or no Content-Length | Use a smaller file; use the web form |
| Port 8000 or 3000 already in use | A previous server still running | Close the old terminal, or `lsof -i :8000` to find it |
| Value-for-money always unknown on real products | OFF has no prices | Record prices in the price sheet and import |
