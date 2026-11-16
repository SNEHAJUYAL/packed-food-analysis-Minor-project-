# Food Decision Intelligence

**Understand. Evaluate. Compare. Decide.**

AI-Based Multimodal Packaged Food Analysis and Consumer Decision Support System.
Minor project, MSIT (GGSIPU), New Delhi. Idea originated by **Sneha Juyal**.
Team: Sneha Juyal, Radhika, Shinjini. Guides: Dr. Sudesh Pahal, Dr. Neeru Rathee.

Paste a packaged-food product page, or upload a pack photo, an app screenshot or a page saved from the
browser. The system reads it (fetching a URL safely, or reading the file with nothing fetched), extracts the listing, normalises every
value to per 100 g/ml with its evidence label and source, stores it in PostgreSQL, scores nutrition,
ingredients, transparency, claims and value with explanations, checks front-of-pack claims against FSSAI
conditions, and suggests alternatives from stored products only, from the same shop (for example Blinkit)
when the product came from one.

> Status (checked 16 Nov 2026): URL-first prototype with an unsaved **candidate preview**, photo and saved-page
> upload with user corrections, and manual entry. Product URLs pass a central source-authorization registry
> first; Open Food Facts is the only enabled external product source. **No machine-learning model has been
> trained**: scoring is rule-based and explainable, similarity is TF-IDF + kNN, photos use Tesseract OCR
> ([docs/AI_ML_METHODOLOGY.md](docs/AI_ML_METHODOLOGY.md)). Tests on 16 Nov 2026: 242 Python and 47 frontend
> tests passed, TypeScript and ESLint clean. Earlier status (17 Oct 2026): URL-first V1 with photo and saved-page upload. Consumer decision support, not a
> medical or clinical score. Photos are read offline with free Tesseract OCR (`brew install tesseract`),
> or by Claude's vision model when `ANTHROPIC_API_KEY` is set (then values are kept only if they appear in
> its transcript of the label). Photo-reading accuracy has not been measured. Barcode scanning, cross-source validation, personalisation, basket optimisation and lab
> evidence are future work and are not implemented. No accuracy figures are claimed; see [docs/nutriscore_comparison.md](docs/nutriscore_comparison.md) and
> [reports/final_report.md](reports/final_report.md) for what was measured and on how much data.

![Product report](docs/screenshots/03_report.png)

## Quick start

```bash
cp .env.example .env
docker compose up --build        # web http://localhost:3000, API docs http://localhost:8000/docs
```

Without Docker (create the `fdi` role and database first, see [docs/deployment.md](docs/deployment.md#option-b-local-processes)): `./run.sh setup && ./run.sh migrate && ./run.sh seed`, then `./run.sh api` and
`./run.sh web`. Details, the offline URL demo and production notes: [docs/deployment.md](docs/deployment.md).

**About the sample data.** Seeding loads 466 **real Open Food Facts India records** (ODbL, no prices,
`data/sample/off_india_subset.jsonl`) plus 40 **synthetic** demo products with made-up prices so
value-for-money can be shown; the synthetic ones are labelled in the database, API and UI. The full India
extract (2,692 records) is reproducible with `./run.sh off-export`. See [data/sample/README.md](data/sample/README.md).

## What it does

| Page | |
| --- | --- |
| Landing (`/`) | URL input, photo / screenshot / saved-page upload with the shop it came from, how it works, an illustrative sample (labelled synthetic), evidence standards, limitations |
| Product report (`/products/{id}`) | Score and grade, dimension explanations, nutrition per 100 g/ml with traffic lights, printed vs normalised values, ingredient explorer, claim panel, missing and conflicting fields, extraction log, alternatives |
| Compare (`/compare`) | 2–6 stored products in one category on one basis, picks with reasons, ingredient differences |
| Alternatives | Balanced, nutrition, lower unit price or transparency; stored records only, from the same shop when known (falls back to all stored products and says so); says so when none qualify |
| Methodology (`/methodology`) | Weights, thresholds and claim rules with sources, missing-data rules, limitations, data licences |

Upload and manual entry also live on the landing page: **Preview candidate (not saved)** shows an
unverified, unscored candidate with field provenance; the upload form accepts corrections (brand, variant,
pack size, ingredients, nutrition); **Enter product details manually** saves an unverified manual record.

API: `POST /api/product-candidates/from-url`, `POST /api/analyze-url`, `POST /api/analyze-upload`,
`POST /api/analyze-manual`, `GET /api/products`, `GET /api/products/{id}`, `POST /api/products/compare`,
`GET /api/products/{id}/alternatives`, `GET /api/reference/categories`, `GET /api/reference/methodology`,
`GET /api/health`. See [docs/api.md](docs/api.md).

## Documentation

Start with [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md). Then:
[architecture](docs/SYSTEM_ARCHITECTURE.md) ·
[AI/ML status](docs/AI_ML_METHODOLOGY.md) ·
[datasets](docs/DATASET_AND_DATA_ENGINEERING.md) ·
[data acquisition](docs/PRODUCT_DATA_ACQUISITION.md) ·
[scoring](docs/FOOD_INTELLIGENCE_AND_SCORING.md) ·
[comparison and recommendations](docs/PRODUCT_COMPARISON_AND_RECOMMENDATIONS.md) ·
[database and API](docs/DATABASE_AND_API.md) ·
[user guide](docs/USER_INTERFACE_AND_USER_GUIDE.md) ·
[installation](docs/INSTALLATION_AND_EXECUTION.md) ·
[demo script](docs/END_TO_END_DEMONSTRATION.md) ·
[testing](docs/TESTING_AND_TROUBLESHOOTING.md) ·
[status and future scope](docs/PROJECT_STATUS_AND_FUTURE_SCOPE.md) ·
[resource register](docs/RESEARCH_RESOURCES_AND_DATA_SOURCES.md).
Reports: [consolidation](reports/COMPLETE_REPOSITORY_CONSOLIDATION_REPORT.md) ·
[documentation audit](reports/COMPLETE_DOCUMENTATION_AUDIT.md) ·
[readiness](reports/FINAL_PROJECT_READINESS_REPORT.md).

## Never invent data

Every field carries one of five evidence labels: **declared**, **derived**, **interpreted**, **verified**,
**unknown**. Missing values stay missing (the database rejects a zero for an unknown nutrient).
Conflicting sources are flagged, not resolved silently. Thresholds and FSSAI conditions live in
`data/reference/*.csv` with their sources; values not yet published are `TODO` and make the system say
"cannot be verified" instead of guessing. The optional LLM fallback (`ANTHROPIC_API_KEY`) can only locate
values that appear verbatim on the page, and is never the authority on a claim.

## Layout

```
config/scoring.json        weights, grade bands, curves (methodology v0.1.0)
data/reference/            thresholds, FSSAI claim rules, INS codes, ingredient terms and classes, OFF category map
data/sample/               OFF India subset + synthetic demo records   data/verified/  evaluation labels, pack-check and price sheets
data/annotation/           annotation schema and unverified candidate records (not loaded into the database)
migrations/                Alembic migrations                         scripts/        OFF download, sample generator
src/acquisition/           source registry, provenance models, validation, URL candidates, workbook importer
src/extract/               SSRF-safe fetch, JSON-LD, HTML, OCR, LLM fallback
src/normalise/             units, ingredients, product builder        src/analyse/    the five dimensions
src/score/                 scoring and grades                         src/recommend/  similarity, alternatives, compare
src/database/              models, repository, ingestion              src/api/        FastAPI app
src/evaluation/            metrics and evaluation runner              src/services.py URL -> stored, scored record
web/                       Next.js + TypeScript + Tailwind + Recharts
notebooks/evaluation.ipynb evaluation with real sample sizes          tests/          pytest (Python), web/src/__tests__ (Vitest)
docs/                      architecture, methodology, data sources, regulatory rules, API, deployment, screenshots
```

## Open items for the team

1. **Protein RDA reference:** claims use 54 g/day (ICMR-NIN 2020, sedentary adult man). Confirm with the guides.
2. **Verified set:** fill the pack-checking sheet (`data/verified/pack_check/`, 150 real products plus
   reserves) from real packs, then run `python -m evaluation.pack_check`. OFF is crowdsourced and 85 % of its
   India records in these categories cannot be graded.
3. **Front-of-pack warning thresholds** (`fop_warning.csv`) stay TODO until FSSAI publishes them; the red
   bounds in `thresholds.csv` are UK FSA 2016 placeholders.
4. Verify `ins_codes.csv` (64 codes) and `allergens.csv` (status `seed_verify`), and the FSSAI regulation's
   commencement date (blank in `fssai_claims.csv`).
5. Code licence not chosen yet (MIT or AGPL-3.0, doc section 13.7).

## Data and licence

Open Food Facts data is under the Open Database License (ODbL); credit it and share-alike any derived
database. A public product page is not permission to scrape: the fetcher respects robots.txt and rate
limits, and the cache is git-ignored. See [docs/data_sources.md](docs/data_sources.md).
