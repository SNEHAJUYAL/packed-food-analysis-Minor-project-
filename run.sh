#!/usr/bin/env bash
# One entry point for the project. Usage: ./run.sh <command> [args]
#   setup               create .venv and install Python requirements (Python 3.11+); web: npm ci in web/
#   db                  start PostgreSQL via Docker and print DATABASE_URL
#   migrate             apply the database migrations (Alembic) and load the regulatory rules
#   seed                load the real OFF India subset and the labelled synthetic sample, then score everything
#   off                 download the Open Food Facts India subset via the OFF API and load it
#   off-export          same, from the official OFF CSV export (1.3 GB stream, no API needed)
#   api                 FastAPI on http://localhost:8000 (OpenAPI docs at /docs)
#   web                 Next.js app on http://localhost:3000
#   demo-pages          serve the synthetic test pages on http://127.0.0.1:8090 for local URL demos
#   test                run the Python tests (TEST_DATABASE_URL=... also runs them on PostgreSQL)
#   test-web            run the frontend component tests
#   analyse <url|file>  analyse one product page in the terminal (add --json, --save, --category X)
#   compare <a> <b> ... --category X   compare saved pages in one category
#   prices <csv>        import hand-recorded prices (data/verified/prices/), then rescore
#   rescore             recompute every stored analysis
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] && set -a && . ./.env && set +a
PY=${PYTHON:-python3}
VENV=.venv
activate() { [ -d "$VENV" ] || "$0" setup; . "$VENV/bin/activate"; export PYTHONPATH="$PWD/src"; }

cmd=${1:-help}; shift || true
case "$cmd" in
  setup)   "$PY" -m venv "$VENV" && . "$VENV/bin/activate" && pip install -q --upgrade pip && pip install -q -r requirements.txt && echo "python ready"
           if command -v npm >/dev/null; then (cd web && npm ci --no-audit --no-fund) && echo "web ready"; fi ;;
  db)      docker compose up -d db && echo "export DATABASE_URL=postgresql://fdi:${POSTGRES_PASSWORD:-change_me_locally}@localhost:5432/fdi" ;;
  migrate) activate; alembic upgrade head && python -m database.ingest --rules-only ;;
  seed)    activate; python -m database.ingest data/sample/off_india_subset.jsonl data/sample/synthetic_products.jsonl "$@" ;;
  off)     activate; python scripts/fetch_off_india.py "$@" && python -m database.ingest data/raw/off_india.jsonl ;;
  off-export) activate; mkdir -p data/raw; curl -sS https://openfoodfacts-ds.s3.eu-west-3.amazonaws.com/en.openfoodfacts.org.products.csv.gz | gunzip | python scripts/off_export_to_jsonl.py > data/raw/off_india.jsonl && python -m database.ingest data/raw/off_india.jsonl ;;
  api)     activate; uvicorn api.main:app --app-dir src --reload "$@" ;;
  web)     cd web && npm run dev ;;
  demo-pages) activate; echo "set FETCH_DEV_ALLOW_HOSTS=127.0.0.1:8090 for the API, then analyse http://127.0.0.1:8090/cereal_jsonld.html"
           python -m http.server 8090 --bind 127.0.0.1 --directory tests/fixtures ;;
  test)    activate; python -m pytest -q "$@" ;;
  test-web) cd web && npm test ;;
  analyse|analyze) activate; python src/cli.py analyse "$@" ;;
  compare) activate; python src/cli.py compare "$@" ;;
  prices)  activate; python -m database.prices "$@" ;;
  rescore) activate; python -m database.ingest --rescore ;;
  *)       sed -n '2,17p' "$0" ;;
esac
