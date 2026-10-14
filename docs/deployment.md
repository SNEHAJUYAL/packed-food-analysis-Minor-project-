# Setup and deployment

## Option A: Docker Compose (one command)

```bash
cp .env.example .env          # set POSTGRES_PASSWORD; ANTHROPIC_API_KEY is optional
docker compose up --build
```

* `db`: PostgreSQL 16 with a named volume.
* `migrate`: runs `alembic upgrade head`, loads the regulatory rules and, into an empty database only, the
  labelled synthetic sample.
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
./run.sh seed                  # synthetic demo records (labelled), then scores everything
./run.sh api                   # http://localhost:8000/docs
./run.sh web                   # http://localhost:3000
```

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
