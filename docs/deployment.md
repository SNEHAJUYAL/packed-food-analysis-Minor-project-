# Setup and deployment

## Option A: Docker Compose (one command)

```bash
cp .env.example .env          # set POSTGRES_PASSWORD; ANTHROPIC_API_KEY is optional
docker compose up --build
```

* `db`: PostgreSQL 16 with a named volume.
* `migrate`: runs `alembic upgrade head`, loads the regulatory rules and, into an empty database only, the
  466 real Open Food Facts records and the 40 labelled synthetic ones.
* `api`: FastAPI on <http://localhost:8000> (OpenAPI docs at `/docs`).
* `web`: Next.js on <http://localhost:3000>; the browser calls `/api/*` on the same origin and Next.js
  forwards it to the API (`API_BASE_URL`, set at build time for the rewrite).

## Option B: local processes

Requirements: Python 3.11+, Node 20+ (tested with Node 22), PostgreSQL 14+ (or `./run.sh db` for Docker).

```bash
./run.sh setup                 # .venv + Python packages, and npm ci in web/
cp .env.example .env           # set DATABASE_URL
./run.sh db                    # optional: PostgreSQL in Docker
./run.sh migrate               # schema + regulatory rules
./run.sh seed                  # 466 real OFF records + 40 labelled synthetic ones, then scores everything
./run.sh api                   # http://localhost:8000/docs
./run.sh web                   # http://localhost:3000
```

`.env` is read by bash, so quote any value containing `&`, for example a socket URL:
`DATABASE_URL='postgresql://fdi@/fdi?host=/tmp&port=5433'`. Unquoted, the `&` silently drops the variable.

**Clean-install check (16 Oct 2026).** A fresh clone of the repository was set up by following the steps
above, on Python 3.13, Node 22 and PostgreSQL 16, with no Docker. These all worked:

* `setup`: 1 min 16 s;
* `migrate`: 18 rules loaded;
* `seed`: 506 records;
* `test`: 141 passed;
* `test-web`: 33 passed;
* the database tests on PostgreSQL: 18 passed.

`api` and `web` both started. `/api/health` reported 506 products, every page returned 200, the report
page rendered in Chromium, and a private address was refused with `blocked_destination`. The only failure
was the unquoted `&` above, which came from the check's own socket URL; the default URL has no `&`.
Option A was not run because Docker was not available.

Load real Open Food Facts data where the network allows it:

```bash
./run.sh off --per-category 200          # data/raw/off_india.jsonl, then ingests it
PYTHONPATH=src .venv/bin/python -m database.ingest --purge-synthetic   # optional: drop the demo records
```

Local URL demo without internet: `./run.sh demo-pages` serves the synthetic test pages on
`127.0.0.1:8090`. Start the API with `FETCH_DEV_ALLOW_HOSTS=127.0.0.1:8090` so that one host:port passes
the private-address check, then analyse `http://127.0.0.1:8090/cereal_jsonld.html` in the web app. Never
set `FETCH_DEV_ALLOW_HOSTS` on a shared deployment.

## Tests

```bash
./run.sh test                                   # Python tests (SQLite in memory for the DB tests)
TEST_DATABASE_URL=postgresql://... ./run.sh test tests/test_api_db.py   # same tests on PostgreSQL via Alembic
./run.sh test-web                               # frontend component tests
PYTHONPATH=src .venv/bin/python -m evaluation.run   # evaluation results -> reports/evaluation_results.json
```

## Production notes

* Secrets only in environment variables; `.env` is git-ignored.
* Put the API behind an egress firewall that blocks private address ranges (the fetcher checks DNS before
  connecting, which does not fully exclude DNS rebinding).
* The rate limiter is in-process; with several API workers use a shared limiter at the proxy.
* Run `python -m database.ingest --rescore` after changing `config/scoring.json` or a reference CSV, and
  bump `methodology_version` so stored results stay traceable to the method that produced them.
