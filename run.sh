#!/usr/bin/env bash
# One entry point for the project. Usage: ./run.sh <command> [args]
#   setup               create .venv and install requirements (Python 3.11+)
#   test                run the test suite
#   demo                Streamlit demo UI on http://localhost:8501
#   api                 FastAPI on http://localhost:8000 (docs at /docs)
#   analyse <url|file>  analyse one product page in the terminal (add --json, --save, --category X)
#   compare <a> <b> ... --category X   compare products in one category
#   db                  start PostgreSQL with the schema via Docker and print DATABASE_URL
#   off                 download the Open Food Facts India subset to data/raw/
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
VENV=.venv
activate() { [ -d "$VENV" ] || "$0" setup; . "$VENV/bin/activate"; export PYTHONPATH="$PWD/src"; }

cmd=${1:-help}; shift || true
case "$cmd" in
  setup)   "$PY" -m venv "$VENV" && . "$VENV/bin/activate" && pip install -q --upgrade pip && pip install -q -r requirements.txt && echo "ready" ;;
  test)    activate; python -m pytest -q "$@" ;;
  demo)    activate; streamlit run web/streamlit_app.py "$@" ;;
  api)     activate; uvicorn api.main:app --app-dir src --reload "$@" ;;
  analyse|analyze) activate; python src/cli.py analyse "$@" ;;
  compare) activate; python src/cli.py compare "$@" ;;
  db)      docker compose up -d db && echo "export DATABASE_URL=postgresql://fdi:fdi_local_only@localhost:5432/fdi" ;;
  off)     activate; python scripts/fetch_off_india.py "$@" ;;
  *)       sed -n '2,11p' "$0" ;;
esac
