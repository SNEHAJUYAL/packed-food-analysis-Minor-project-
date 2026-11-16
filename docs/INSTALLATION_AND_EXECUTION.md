# Installation and execution

Every command here exists in `run.sh`, `web/package.json`, `docker-compose.yml` or the module docstrings,
and was checked on 16 November 2026. Commands marked ✓ were run successfully during the consolidation.
Run them from the project folder (on the team Mac: `/Users/snehajuyal/Downloads/minor project`).

## 1. Requirements

* Python 3.11+ (tested with 3.13.9), Node 20+ (tested with 22), PostgreSQL 14+ (team Mac: EDB
  PostgreSQL 18 at `/Library/PostgreSQL/18`; Docker Compose uses PostgreSQL 16).
* Optional: Tesseract for photo OCR (`brew install tesseract`), Docker, an Anthropic API key.

## 2. Environment setup

Copy the example settings (never commit `.env`):

```bash
cp .env.example .env
```

Create the virtual environment, install Python packages and run `npm ci` in `web/`:

```bash
./run.sh setup
```

`requirements.txt` now lists `openpyxl` (it was missing although the workbook importers, the price and
pack-check sheet generators and two test modules need it).

## 3. PostgreSQL

Option A, the installed EDB PostgreSQL on the team Mac (psql is not on PATH, so use the full path).
Create the role and database once:

```bash
/Library/PostgreSQL/18/bin/psql -U postgres -c "CREATE ROLE fdi LOGIN PASSWORD 'change_me_locally';"
```

```bash
/Library/PostgreSQL/18/bin/psql -U postgres -c "CREATE DATABASE fdi OWNER fdi;"
```

Check it is running ✓:

```bash
/Library/PostgreSQL/18/bin/pg_isready
```

Option B, PostgreSQL in Docker (prints the `DATABASE_URL` to use):

```bash
./run.sh db
```

`.env` must contain `DATABASE_URL=postgresql://fdi:change_me_locally@localhost:5432/fdi` (the default in
`.env.example`).

## 4. Migrations ✓

Applies Alembic migrations and loads the 18 regulatory rules:

```bash
./run.sh migrate
```

Check the revision (should print `0002 (head)`) ✓ (the current revision was read with Alembic during
the consolidation; migrations were not re-applied):

```bash
.venv/bin/alembic current
```

## 5. Seed the data

Loads 466 Open Food Facts records and 40 labelled synthetic records, then scores everything:

```bash
./run.sh seed
```

Optional: rebuild the full OFF India extract from the official export (about 1.3 GB streamed):

```bash
./run.sh off-export
```

Optional: import hand-recorded prices, then rescore:

```bash
./run.sh prices data/verified/prices/price_entry_sheet.csv
```

## 6. Start the API (terminal 1) ✓ running during the check

```bash
./run.sh api
```

Health check ✓ (returned `"status":"ok","database":"ok"`):

```bash
curl http://localhost:8000/api/health
```

Interactive API docs: <http://localhost:8000/docs>.

## 7. Start the web app (terminal 2) ✓ running during the check

```bash
./run.sh web
```

Open <http://localhost:3000>.

## 8. Tests

Python tests ✓ (242 passed):

```bash
./run.sh test
```

Frontend tests ✓ (47 passed):

```bash
./run.sh test-web
```

TypeScript ✓:

```bash
cd web && npx tsc --noEmit
```

ESLint ✓:

```bash
cd web && npm run lint
```

Python tests against PostgreSQL instead of SQLite (use a separate, empty test database, never the
main one):

```bash
TEST_DATABASE_URL=postgresql://fdi:change_me_locally@localhost:5432/fdi_test ./run.sh test
```

## 9. Inference (analysis) from the terminal

Analyse one page or saved file without the web app ✓ (prints overall 69, grade C for this synthetic
fixture; nothing is saved unless `--save` is added):

```bash
./run.sh analyse tests/fixtures/cereal_jsonld.html
```

Same, as JSON ✓:

```bash
./run.sh analyse tests/fixtures/cereal_jsonld.html --json
```

Compare two or more saved pages of **one** category (replace the file names with your own saved pages;
the command refuses mixed categories, and the fixtures folder has only one page per category):

```bash
./run.sh compare first_page.html second_page.html --category breakfast_cereals
```

Serve the synthetic test pages for a local URL demo (then set `FETCH_DEV_ALLOW_HOSTS=127.0.0.1:8090` for
the API):

```bash
./run.sh demo-pages
```

Recompute all stored analyses:

```bash
./run.sh rescore
```

Run the evaluation and rewrite `reports/evaluation_results.json`:

```bash
PYTHONPATH=src .venv/bin/python -m evaluation.run
```

## 10. Training

**Not implemented.** No model is trained in this project, so there is no training command. See
[AI_ML_METHODOLOGY.md](AI_ML_METHODOLOGY.md).

## 11. Candidate data tools (research data)

Validate the annotation candidates (read-only):

```bash
PYTHONPATH=src .venv/bin/python scripts/validate_annotation_dataset.py data/annotation/imported_candidates/consolidated_annotation_candidates.jsonl
```

The consolidation (`scripts/consolidate_product_datasets.py --input … --out-dir …`) and catalogue import
(`scripts/import_product_catalog_candidate.py --input … --out-dir …`) scripts need the original workbooks
from `~/Downloads`; their inputs are read-only and they write only to the output folder you name, which
should be under `data/annotation/`.

## 12. Docker Compose (all services)

```bash
docker compose up --build
```

Not run during this consolidation.

## 13. Hosted

Vercel (web + separate API project) with a Neon database, described in [deployment.md](deployment.md).
Not re-verified during this consolidation.
