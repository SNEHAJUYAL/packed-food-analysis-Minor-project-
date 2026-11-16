# Complete repository consolidation report

**Project:** AI-Based Multimodal Packaged Food Analysis and Consumer Decision Support System
**Repository:** <https://github.com/SNEHAJUYAL/packed-food-analysis-Minor-project->
**Local folder:** `/Users/snehajuyal/Downloads/minor project` (branch `main`, remote `origin` → the
repository above; last commit `133f6b3`)
**Date:** 16 November 2026. Nothing was committed, pushed, merged or deployed.

## 1. Which folder is the main repository

Three copies exist on the Mac. Only `Downloads/minor project` has the git remote for this repository and
all the recent task work (`src/acquisition/`, the 2A-5 to 2A-6.3 changes, 28 modified and about 60
untracked files). `~/packed-food-analysis-Minor-project-` is an older clone at the same commit without that
work. `Downloads/packed-food-analysis-Minor-project--main` is a download snapshot from 21 October whose
enclosing git repository points at a different project. All consolidation work was done in
`Downloads/minor project`.

## 2. Development consolidated

| Stream | Where it lives | Status |
| --- | --- | --- |
| URL-first V1: fetch, extract, normalise, score, store, alternatives, Next.js UI | committed (`133f6b3` and earlier) | Implemented and tested |
| Photo and saved-page upload, Tesseract OCR, hosted deployment | committed | Implemented; photo accuracy unmeasured |
| Dataset research, audits, roadmap (Task 2, 2A) | `reports/DATA_*`, `INDIA_FOOD_DATA_ACQUISITION_ROADMAP.md`, `DATASET_*` | Documents (untracked) |
| Annotation schema, guidelines, validator, grouped splits | `data/annotation/`, `docs/annotation_*`, `scripts/validate_annotation_dataset.py`, `scripts/create_grouped_splits.py` | Implemented and tested (untracked) |
| Workbook consolidation: 85 candidates | `scripts/consolidate_product_datasets.py`, `data/annotation/imported_candidates/` | Implemented and tested; data unverified |
| Acquisition foundation (2A-5.x): models, adapters, registry, validation, dry run | `src/acquisition/` | Implemented and tested (untracked) |
| Catalogue workbook importer: 25 records + 75 price observations + 125 image refs | `src/acquisition/catalog_workbook.py`, `scripts/import_product_catalog_candidate.py`, `data/annotation/candidate_sources/` | Implemented and tested; data unverified |
| 2A-6.1 Product URL candidate | `src/acquisition/product_url.py`, `POST /api/product-candidates/from-url` | Implemented and tested |
| 2A-6.2 Central source policy + "Preview candidate (not saved)" UI | registry, `services.py`, `AnalyzeForm.tsx` | Implemented and tested; see §6 for a later change |
| 2A-6.3 Error codes, offline saved page, corrections, manual entry | `extract/fetch.py`, `services.py`, `UploadForm.tsx`, `POST /api/analyze-manual` | Implemented and tested |
| 2A-6.3.1 API documentation | `docs/api.md` | Verified; two small corrections made |
| OCR/NLP benchmark, retailer audit | `src/evaluation/ocr_nlp.py`, `retailer_audit.py` | Implemented; OCR harness only on a rendered image |

## 3. Architecture and modules

See [docs/SYSTEM_ARCHITECTURE.md](../docs/SYSTEM_ARCHITECTURE.md). Python ~8,000 lines across
`acquisition`, `extract`, `normalise`, `analyse`, `score`, `recommend`, `database`, `api`, `evaluation`;
Next.js app with 6 page routes at the start of the check (landing, products, product report,
alternatives, compare, methodology).

## 4. Documentation produced

14 documents in `docs/` and 3 reports in `reports/` (list in
[COMPLETE_DOCUMENTATION_AUDIT.md](COMPLETE_DOCUMENTATION_AUDIT.md)); README, `docs/api.md`,
`docs/data_sources.md` and `docs/methodology.md` corrected. Resource register:
[docs/RESEARCH_RESOURCES_AND_DATA_SOURCES.md](../docs/RESEARCH_RESOURCES_AND_DATA_SOURCES.md) (44 entries
plus the IFID lead; 42 unique URLs checked).

## 5. Current application capabilities

Analyse an authorized product URL (saved and scored); preview an authorized URL as an unverified candidate
(not saved); upload a saved page (local parsing only) or a pack photo (OCR) with corrections; enter a
product manually; read an explainable report (five dimensions, grade, evidence labels, claims, missing
data, extraction log); browse stored products; compare 2–6 products; get alternatives by preference;
read the methodology.

## 6. Source authorization status

Open Food Facts is the only enabled external product source. The candidate preview blocks every other
host before DNS/HTTP (verified live with a Blinkit URL: 403 `unsupported_source`).

**Open issue.** At 21:41 IST on 16 Nov 2026, during this consolidation, another session changed
`src/services.py`, `src/acquisition/registry.py`, `tests/test_api_db.py` and
`tests/test_product_url_acquisition.py`. Since then the saved `POST /api/analyze-url` fetches an
**unregistered** public host once as a user-submitted page (SSRF, robots.txt, limits still apply), while
registered-but-unauthorized hosts stay blocked. This contradicts the Task 2A-6.2 report and the earlier
`docs/api.md` text. The new documents describe the current code and flag the difference; the team must
decide which behaviour is intended.

## 7. Candidate dataset status

| Set | Count | Status |
| --- | --- | --- |
| OFF India subset | 466 | real, ODbL, seeded |
| Synthetic | 40 | synthetic, labelled, made-up prices |
| Annotation candidates | 85 | pending review, unverified, 37 possible duplicate groups |
| Catalogue candidates | 25 listings, 75 price observations | unverified, isolated |
| Pack-check | 200 rows | empty |
| Price entry | 300 rows | empty |

No candidate was promoted to verified data. No synthetic price is presented as a retailer price.

## 8. AI/ML status

No independently trained model. Pretrained: Tesseract OCR; optional Claude (off without a key). Classic
methods: TF-IDF + cosine kNN. Everything else is deterministic rules. Evidence: Nutri-Score agreement
ρ = 0.763 (n = 339), claim rules 22/22, ingredient classes 53/53, extraction recall 0.81 on 4 synthetic
pages; no real-photo or recommendation-relevance evaluation. See
[docs/AI_ML_METHODOLOGY.md](../docs/AI_ML_METHODOLOGY.md).

## 9. Frontend, backend, database and runtime

| Item | State on 16 Nov 2026 |
| --- | --- |
| API (`./run.sh api`) | running on `127.0.0.1:8000`, health `ok`, database `ok`, 11 routes |
| Web (`./run.sh web`) | running on `127.0.0.1:3000`; `/`, `/products`, `/compare`, `/methodology` returned 200 |
| Database | EDB PostgreSQL accepting connections; `alembic current` = `0002 (head)`; 507 products (466 OFF, 40 synthetic, 1 URL); 35 synthetic price observations; 18 rules |
| Hosted (Vercel + Neon) | not re-verified |

## 10. Test results

See §13 for the final re-run. First run (≈ 21:39 IST): Python **242 passed**, frontend **47 passed**,
TypeScript and ESLint exit 0, `git diff --check` clean.

## 11. Outstanding blockers

1. Decide the `analyze-url` behaviour for unregistered hosts.
2. Fill the pack-check sheet (verified set) and the price sheet (real prices).
3. Final FSSAI thresholds; energy benchmark; verify INS and allergen lists.
4. No retailer authorization for automated access.
5. Confirm three IEEE paper titles and the IFID dataset link.

## 12. Future scope

See [docs/PROJECT_STATUS_AND_FUTURE_SCOPE.md](../docs/PROJECT_STATUS_AND_FUTURE_SCOPE.md).

## 13. Final verification

Re-run at 21:53 IST, after the other session's backend edits and while it was still editing the web UI:

| Check | Result |
| --- | --- |
| Python tests | **243 passed** (one test added by the other session) |
| Frontend tests | **47 passed**, 7 files |
| TypeScript (`npx tsc --noEmit`) | exit 0 |
| ESLint (`npm run lint`) | **2 errors** in files being edited by the other session: `AnalyzeForm.tsx:275` (variable used before declaration) and the new `AppShell.tsx:88` (setState inside an effect). At the first run (≈ 21:39) lint was clean |
| `git diff --check` | clean |
| Internal Markdown links (64 files) | all resolve, including heading anchors |

New, untracked web files from the other session at this time: `web/src/app/analyze/`,
`web/src/app/dashboard/`, `web/src/app/insights/`, `AnalyzeWorkspace.tsx`, `AppShell.tsx`, `Brand.tsx`,
`DashboardView.tsx`, `InsightsView.tsx`, `charts.tsx`, `icons.tsx`, `lib/catalog.ts`. They are not
described in `docs/USER_INTERFACE_AND_USER_GUIDE.md`, which documents the six routes that existed at the
start of the check. Re-run the frontend checks and update that guide when the redesign is finished.

## 14. Exact startup instructions

Each command on its own; run from `/Users/snehajuyal/Downloads/minor project`. Full detail in
[docs/INSTALLATION_AND_EXECUTION.md](../docs/INSTALLATION_AND_EXECUTION.md).

```bash
cd "/Users/snehajuyal/Downloads/minor project"
```

```bash
./run.sh setup
```

```bash
./run.sh migrate
```

```bash
./run.sh seed
```

```bash
./run.sh api
```

In a second terminal:

```bash
./run.sh web
```

Then open <http://localhost:3000>.

## 15. Git state and commands for after approval

* **Branch:** `main`. **Remote:** `origin` → `https://github.com/SNEHAJUYAL/packed-food-analysis-Minor-project-.git`.
  Last commit `133f6b3`. Nothing committed, pushed, merged or deployed.
* **Changed by this consolidation:** `README.md`, `docs/api.md`, `docs/data_sources.md`,
  `docs/methodology.md`, `requirements.txt` (added `openpyxl>=3.1`).
* **New from this consolidation:** the 14 `docs/*.md` files listed in the documentation audit (13 new plus
  the resource register) and `reports/COMPLETE_REPOSITORY_CONSOLIDATION_REPORT.md`,
  `reports/COMPLETE_DOCUMENTATION_AUDIT.md`, `reports/FINAL_PROJECT_READINESS_REPORT.md`.
* **Earlier task work still uncommitted (preserved, not modified):** 23 modified source/test/web files
  from Tasks 2A-6.x, plus untracked `src/acquisition/`, `data/annotation/`, 4 scripts, 7 test files,
  3 source modules, 6 docs and about 35 reports.
* **Being edited by another session during the check:** `src/services.py`, `src/acquisition/registry.py`,
  `tests/test_api_db.py`, `tests/test_product_url_acquisition.py` and the web UI files listed in §13.
* **Intentionally left unchanged:** all application code and tests, all data files, `.env`, migrations,
  existing task reports, `docs/master_project_doc.md`, `docs/architecture.md`, `docs/deployment.md`,
  screenshots. `data/.DS_Store` should not be committed.
* **Ready for review:** the documentation is ready to review. The code is **not** ready to commit until the
  other session finishes and ESLint is clean again.

After you approve, and after the UI work is finished and `npm run lint` passes, these commands commit and
push everything on `main` (run one at a time from the project folder):

```bash
cd "/Users/snehajuyal/Downloads/minor project"
```

```bash
git status
```

```bash
git add -A -- . ':!data/.DS_Store' ':!.DS_Store'
```

```bash
git commit -m "Consolidate acquisition, candidate preview, offline upload and documentation"
```

```bash
git push origin main
```

To commit only this consolidation's documentation first, replace the `git add` line with:

```bash
git add README.md requirements.txt docs reports
```
