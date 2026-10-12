# Food Decision Intelligence

**AI-Based Multimodal Packaged Food Analysis and Consumer Decision Support System**
Minor project, MSIT (GGSIPU), New Delhi. Idea originated by **Sneha Juyal**.
Team: Sneha Juyal, Radhika, Shinjini. Guides: Dr. Sudesh Pahal, Dr. Neeru Rathee.

A product URL goes in; an explainable report comes out: nutrients per 100 g with traffic lights,
ingredients grouped into meaningful classes, each front-of-pack claim with an evidence status,
dimension scores, an overall score and A–E grade, and price per 100 g compared with similar products.

> Status (12 Oct 2026): URL-first MVP (V1). Barcode, OCR and accuracy figures are not claimed:
> they do not exist yet. The score is a consumer decision-support assessment, not a medical score.

## Run it

```bash
python3.11 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest                                           # 80 tests
uvicorn api.main:app --app-dir src --reload      # API on :8000, docs at /docs
streamlit run web/streamlit_app.py               # demo UI on :8501
python scripts/fetch_off_india.py                # Open Food Facts India subset -> data/raw/
docker compose up                                # PostgreSQL + API + demo
```

API: `POST /analyse/url`, `POST /analyse/html`, `POST /analyse/product`, `POST /compare`,
`GET /methodology`.

## Never invent data

Every field carries one of five evidence labels: **declared**, **derived**, **interpreted**,
**verified**, **unknown**. Missing values stay missing, never zero. Conflicting sources are flagged,
not silently resolved. Thresholds and FSSAI conditions live in `data/reference/*.csv` with a source
column; values not yet copied from the official text are marked `TODO` and make the system answer
"cannot be verified" instead of guessing. See [docs/methodology.md](docs/methodology.md).

## Layout

```
config/scoring.json      dimension weights, grade bands, prototype curves
data/reference/          thresholds.csv, fssai_claims.csv, ins_codes.csv, fop_warning.csv, ...
data/verified/           evaluation-set template (source C)
db/schema.sql            PostgreSQL schema (doc section 7)
src/extract/             jsonld.py, html_parser.py, llm_fallback.py, fetch.py
src/normalise/           units.py, ingredients.py, matcher.py (Open Food Facts), build.py
src/analyse/             nutrition.py, ingredients.py, claims.py, transparency.py, value.py, fop_warning.py
src/score/               category_rules.py, scorer.py, grade.py
src/recommend/           similarity.py (TF-IDF + kNN), ranker.py, explain.py
src/api/                 FastAPI app
src/pipeline.py          URL -> report
web/streamlit_app.py     first demo UI (Next.js later)
tests/                   pytest, incl. the doc's worked example (58, grade C)
```

## Open items for the team

1. Copy exact FSSAI claim conditions and clause numbers into `data/reference/fssai_claims.csv`
   (Advertising and Claims Regulations 2018, gazette PDF on fssai.gov.in).
2. Replace the UK placeholder thresholds with FSSAI / ICMR-NIN / WHO values per category, and add
   protein and energy benchmarks (`thresholds.csv`).
3. Fill `fop_warning.csv` once the FSSAI front-of-pack rule text is final; recheck before the demo.
4. Verify `ins_codes.csv` and `allergens.csv` against Codex and FSSAI texts (status `seed_verify`).
5. Build the verified evaluation set (`data/verified/`), then measure the metrics in doc section 10.
6. Wire the LLM fallback and PostgreSQL persistence; build the Next.js frontend.

## Data and licence

Open Food Facts data is under the Open Database License (ODbL); credit it and share-alike any
derived database. A public product page is not permission to scrape: check each site's terms,
prefer structured metadata, and respect robots.txt (the fetcher does). The code licence is not
chosen yet (MIT or AGPL-3.0, doc section 13.7).
