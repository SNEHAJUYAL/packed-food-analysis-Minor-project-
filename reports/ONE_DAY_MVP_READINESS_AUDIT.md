# One-Day MVP Readiness Audit

**Audit date:** 2026-11-16  
**Scope:** Read-only repository and runtime audit. No application/data files were changed other than this report; no retailer pages or databases were accessed for data collection, and no dependencies were installed.

## Executive assessment

The repository already contains a usable product-analysis application: Next.js pages, FastAPI endpoints, deterministic extraction/normalization, explainable nutrition and ingredient scoring, stored-product comparison and recommendations, PostgreSQL models/migrations, and labelled demo data. Frontend tests and most Python tests pass.

The shortest credible demonstration is the existing seeded-data workflow with the **40 labelled synthetic products clearly disclosed**, plus a local synthetic saved-page/URL example if time permits. Do not present live retailer prices or retailer URL acquisition as implemented. There is no authorized retailer adapter, the verified price-entry CSV is currently just its header, and Open Food Facts has no prices. The new source-policy-gated candidate URL endpoint only permits the registered Open Food Facts product host and is not connected to the main frontend analysis flow.

**Current local run blockers:** Docker is not installed, PostgreSQL does not answer on `localhost:5432`, and the full Python suite cannot collect two workbook test modules because `openpyxl` is absent. Node 24.7.0 is within the frontend's declared engine range; Python is 3.14.3 while the project declares Python >=3.11 (the repository's previous clean-install note tested Python 3.13). Frontend lint, typecheck and tests pass in the current workspace.

## Feature readiness matrix

| Area | Status | Repository evidence and current limits |
|---|---|---|
| Frontend application/pages | **Implemented and tested** | Next.js App Router pages exist for landing/analyze, product browser/detail, compare, alternatives and methodology (`web/src/app/`). Component tests: 42 passed. TypeScript and ESLint pass. Current pages call the established analysis APIs; the newer policy-gated candidate URL endpoint has no frontend entry point. |
| Backend/API entry points | **Implemented and tested** | FastAPI app in `src/api/main.py`; includes URL analysis, upload, product list/detail, compare, alternatives, references/health and candidate URL extraction. API and pipeline tests are included in the Python suite. Database-dependent routes are unavailable until PostgreSQL is running and seeded. |
| Product URL extraction | **Partially implemented** | Existing `/api/analyze-url` uses safe HTTP(S)/destination checks, robots handling, JSON-LD, HTML and optional grounded LLM fallback, then normalizes, persists and scores. It does **not** use the acquisition authorization registry. The separate `/api/product-candidates/from-url` service checks source policy before fetching, preserves field evidence and does not persist; only Open Food Facts is currently enabled, and this endpoint is not wired into the UI. Dynamic JS-rendered pages and retailer adapters are absent. |
| Retailer product URL acquisition | **Blocked by authorization or data availability** | No retailer page adapters are enabled; the new candidate workflow allows only registered Open Food Facts pages. Do not demonstrate live retailer fetching until the source is authorized and policy-gated. |
| Ingredient analysis | **Implemented and tested** | Ingredient text normalization/matching and deterministic class-based analysis are in `src/normalise/ingredients.py` and `src/analyse/ingredients.py`; covered by ingredient and pipeline tests. This is a heuristic prototype, not a learned model or clinical/safety assessment. Missing or unrecognized text reduces coverage. |
| Nutrition analysis | **Implemented and tested** | Per-100 g/ml normalization, evidence labels, category thresholds, traffic lights and weighted scoring exist in `src/normalise/units.py`, `src/analyse/nutrition.py` and `src/score/`. Nutrition basis/coverage can leave a score unavailable. Current UK FSA high-nutrient bounds are placeholders; FSSAI FOP warning thresholds remain TODO and are not simulated as an official warning. |
| Claims/transparency/value analysis | **Partially implemented** | Deterministic claim checks, disclosure/transparency and value-per-unit logic are present. Rule inputs and methodology are documented, but claim-rule sources/statuses include unresolved/TODO items; these are prototype decision-support outputs, not authoritative determinations. Value analysis needs a usable price and pack size. |
| Scoring and grading | **Implemented and tested** | Weighted nutrition/dimension scoring and grades in `src/score/`, configured in `config/scoring.json`; scores preserve missing coverage. This is a hand-designed, unvalidated methodology, not an evaluated ML model. The repository explicitly disclaims medical/clinical use. |
| Product comparison | **Implemented and tested** | `/api/products/compare` and `src/recommend/alternatives.py` compare 2–6 stored products within one category and compatible nutrition basis. Requires a working seeded database. |
| Alternatives/recommendations | **Implemented and tested** | Stored-product alternatives with balanced/nutrition/price/transparency preferences, similarity and explanations exist. They operate only over products already stored, not live retailer catalogues; results may include synthetic demo rows and must be labelled accordingly. |
| Retailer price comparison | **Partially implemented** | The application computes unit prices and can compare stored price observations. `src/database/prices.py` accepts manually recorded, product-matched observations. There is no live retailer comparison/acquisition adapter. `data/verified/prices/price_entry_sheet.csv` has only its header; seed prices are synthetic. The candidate workbook's 75 populated prices are explicitly unverified and isolated from production. |
| PostgreSQL integration/schema | **Implemented; current runtime unverified** | SQLAlchemy models and Alembic migrations cover product identity, source, nutrients, ingredients, claims, prices, analysis and recommendations. Tests use SQLite unless `TEST_DATABASE_URL` targets PostgreSQL; the live PostgreSQL integration path was not run in this audit. `pg_isready -h localhost -p 5432` reports no response; Docker is unavailable here. No database was accessed or changed. |
| Candidate datasets and quality | **Partially implemented; not verified training data** | See dataset profile below. The 466-row OFF subset is crowdsourced reference data, not ground truth; 40 rows are explicitly synthetic. The 85 consolidated workbook candidates are unverified and lack package-label ground truth. The separate 25-product workbook release contains 25 listing candidates and 75 unverified price candidates, not production data. |
| Image/OCR workflow | **Partially implemented** | Image upload/OCR and optional Anthropic vision fallback exist; saved-page upload avoids fetching. OCR/photo accuracy has not been evaluated. Candidate URL extraction stores image references only and does not download or verify image MIME/reachability. |
| ML models | **Not implemented** | OCR/LLM integrations and heuristic matching are not task-trained or evaluated product models. Do not describe the current system as having a trained Indian-food classifier or recommendation model. |
| Tests and static checks | **Partially tested; collection blocker** | Frontend: 42 tests pass, typecheck passes, lint passes. Python: 208 pass when two XLSX-dependent test files are excluded. Full collection fails because `openpyxl` is not installed. No dependency was installed to resolve it. |

## Dataset profile and evidence status

| Dataset/release | Size | Readiness and limitations |
|---|---:|---|
| `data/sample/off_india_subset.jsonl` | 466 | Real Open Food Facts India records, selected for at least four of six nutrition fields in five project categories. Crowdsourced, no prices, not manually verified. Repository docs report roughly 85% of the broader India records in these categories cannot be graded due to missing fields. |
| `data/sample/synthetic_products.jsonl` | 40 | Synthetic demo products with made-up prices, clearly labelled as synthetic in app/API. Useful for an offline comparison/value demonstration only; never present as observed market data. |
| Consolidated annotation candidates | 85 | Separate research candidate records. Existing validation report shows 0 schema errors/warnings, but all records remain pending/unverified; identity/category needs review and package ingredients, nutrition, GTIN, pack details, images and source licenses are absent. 10 are unassigned in its taxonomy mapping. |
| Complete Product Catalog acquisition release | 100 acquisition records | Exactly 25 product/listing records plus 75 price records across three retailer columns, candidate/unverified. Source audit reports 24 numeric barcode cells requiring review, 14 unmapped categories, seven ranged pack sizes, and 50 absent Blinkit/Instamart product evidence URLs. Ingredients and nutrition text are provided but not package-verified; retailer prices are not confirmed. |
| Verified price-entry sheet | 0 data rows | CSV currently contains only the column header. No verified manual price observations are ready for an authentic retailer-price demonstration. |
| Verified pack/evaluation data | Not sufficient for model-quality claims | Templates and small evaluation artifacts exist, but no complete, representative, manually verified product set supports accuracy claims. Prior reports explicitly state extraction/photo accuracy has not been measured adequately. |

Candidate records must not be seeded as verified products or used to imply current prices. The 25/75 candidate release is separate from the application's sample seed files.

## Critical blockers to an honest end-to-end demo

1. **Runtime services are not ready in this environment:** Docker is absent and no PostgreSQL server responds on port 5432. The UI's principal analysis, browser, comparison and recommendations need the database.
2. **No authorized retailer URL collection:** Blinkit, Zepto, Instamart, Amazon India, BigBasket and JioMart are not enabled sources in the candidate acquisition registry. BigBasket is explicitly disabled/unknown. Do not test against retailer sites.
3. **Two URL pathways have different source controls:** the new candidate endpoint is policy-gated but Open Food Facts-only and not connected to the UI; the legacy analysis endpoint performs safe-fetch/robots checks but does not consult the source registry. Do not use the legacy URL route as evidence of retailer authorization.
4. **No verified retailer-price observations:** OFF sample data has no prices, manual price sheet is empty, and seed prices are synthetic. Candidate workbook values are unverified and must not be shown as live/current market comparisons.
5. **Data quality limits scoring:** incomplete nutrition/ingredients can produce partial or insufficient reports. Prototype weights/thresholds and unresolved claims/FOP rules limit the claims a demonstration should make.
6. **Full backend test collection is incomplete:** missing `openpyxl` prevents two test modules from collecting; installing it would alter dependencies/environment and was not done under this read-only audit.

## Shortest implementation/run sequence for today

Prioritize a reproducible **seeded demo**, not live retailer acquisition:

1. Start the existing Docker Compose stack on a machine with Docker available. It starts PostgreSQL, migrates, seeds 466 OFF reference records and 40 labelled synthetic demo records, then starts API and web.
2. Confirm `/api/health` reports `database: ok` and the expected seeded count; open the landing page, browse a clearly labelled synthetic item, open its report, and show compare/alternatives/methodology.
3. If URL extraction must be shown, use the bundled synthetic page fixture with the documented development host exception. This is a synthetic local extraction demonstration, not a retailer fetch. The regular candidate endpoint can instead be demonstrated as blocked for unregistered sources without making a network request.
4. State visibly that prices in the demo are synthetic and that no retailer price comparison is currently verified. Avoid claims of model accuracy or official FSSAI warning status.
5. Do not spend the day importing the candidate workbooks, integrating candidate prices, or adding retailer scrapers. The fastest path to an honest working presentation is bringing up the existing seeded app and rehearsing its actual evidence labels and limitations.

## Exact existing run commands

### Docker Compose (documented one-command path)

Run from the repository root on a host with Docker Compose:

```bash
cp -n .env.example .env   # only if .env does not already exist; set a local POSTGRES_PASSWORD if desired
docker compose up --build
```

Then open:

```text
Web:       http://localhost:3000
API docs:  http://localhost:8000/docs
Health:    http://localhost:8000/api/health
```

Compose will write to its local PostgreSQL volume, run migrations, and seed the two existing sample files. This audit did not run it. Docker is not installed in the audited environment.

### Existing local-process path with PostgreSQL already available

First-time setup (installs project dependencies; not run during this audit):

```bash
./run.sh setup
```

Set `DATABASE_URL` in the existing `.env` to a local PostgreSQL role/database, then:

```bash
./run.sh migrate
./run.sh seed
./run.sh api
```

In a second terminal:

```bash
./run.sh web
```

`./run.sh db` is available to start the Compose PostgreSQL service, but also requires Docker. If using the bundled local synthetic page fixture, start a third terminal with `./run.sh demo-pages`, and start the API with `FETCH_DEV_ALLOW_HOSTS=127.0.0.1:8090 ./run.sh api`; this development exception must not be used on a shared deployment.

### Existing checks

```bash
./run.sh test
./run.sh test-web
cd web && npm run typecheck && npm run lint
```

The full Python command currently stops at collection due to missing `openpyxl`; with those XLSX-specific files excluded, the inspected suite result is:

```bash
.venv/bin/python -m pytest -q \
  --ignore=tests/test_catalog_workbook_candidate.py \
  --ignore=tests/test_dataset_consolidation.py
```

## Commands/checks executed in this audit

- `.venv/bin/python -m pytest -q` — **failed collection**: missing `openpyxl` in `tests/test_catalog_workbook_candidate.py` and `tests/test_dataset_consolidation.py`.
- `.venv/bin/python -m pytest -q --ignore=tests/test_catalog_workbook_candidate.py --ignore=tests/test_dataset_consolidation.py` — **208 passed**.
- `cd web && npm test -- --run` — **42 passed** across 7 files.
- `cd web && npm run typecheck` — **passed**.
- `cd web && npm run lint` — **passed**.
- Runtime probes — Python 3.14.3, Node 24.7.0, npm 11.19.0; Docker command not found; PostgreSQL readiness check failed (no response at `localhost:5432`). `.env` exists but its contents were not read.

## Conclusion

The codebase is **demo-capable after runtime setup**, but not ready for an authentic live retailer-price or accuracy-validated ML demonstration. The current MVP can show explainable packaged-food analysis over seeded sample records, including clearly labelled synthetic examples, plus existing comparison and alternatives over the local stored catalogue. A working local database/container stack is the immediate operational blocker; authorization and verified price data are the blockers for retailer collection/comparison.
