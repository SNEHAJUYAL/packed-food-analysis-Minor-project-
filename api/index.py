"""Vercel entry point for the FastAPI app (a second Vercel project with this repository's root as its root).

Vercel's filesystem is read-only apart from /tmp, and there is no step that runs before the function
starts, so the first cold start applies the migrations and loads the sample data into an empty database.
"""
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("FETCH_CACHE_DIR", "/tmp/fdi-cache")

log = logging.getLogger("fdi.vercel")


def _prepare_database() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        return
    from alembic import command
    from alembic.config import Config

    # Migrations go over the direct (unpooled) connection when Neon provides one
    direct = os.environ.get("DATABASE_URL_UNPOOLED") or url
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    os.environ["DATABASE_URL"] = direct
    try:
        command.upgrade(cfg, "head")
    finally:
        os.environ["DATABASE_URL"] = url
    from database import ingest
    sample = ROOT / "data" / "sample"
    ingest.main([str(sample / "off_india_subset.jsonl"), str(sample / "synthetic_products.jsonl"), "--if-empty"])


try:
    _prepare_database()
except Exception:  # the API still starts; /api/health then reports the database problem
    log.exception("database preparation failed")

# Loaded by path: this file's own folder is also called "api", so `import api.main` would be ambiguous
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("fdi_api_main", ROOT / "src" / "api" / "main.py")
_main = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _main  # pydantic resolves the models' annotations through sys.modules
_spec.loader.exec_module(_main)
app = _main.app
