"""Save analyses to PostgreSQL (db/schema.sql). Optional: used only when DATABASE_URL is set."""
from __future__ import annotations

import json
import os
from typing import Optional

from core.schema import NUTRIENTS

try:
    import psycopg
except ImportError:  # pragma: no cover - persistence is optional
    psycopg = None


def database_url() -> Optional[str]:
    return os.environ.get("DATABASE_URL")


def connect(url: Optional[str] = None):
    url = url or database_url()
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    if psycopg is None:
        raise RuntimeError("psycopg is not installed: pip install 'psycopg[binary]'")
    return psycopg.connect(url)


def save_report(report: dict, url: Optional[str] = None) -> int:
    """Insert the product, its evidence-labelled values and the analysis. Returns product_id."""
    p = report["product"]
    d = report["dimensions"]
    o = report["overall"]
    with connect(url) as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO products (name, brand, category, category_label, source_url, collected_at,
                                     conflict_flag, conflicts)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING product_id""",
            (p["name"]["value"], p["brand"]["value"], p["category"]["value"], p["category"]["label"],
             p["source_url"], p["collected_at"], p["conflict_flag"], json.dumps(p["conflicts"])))
        pid = cur.fetchone()[0]
        if p["price_inr"]["value"] is not None or p["pack_size"]["value"] is not None:
            cur.execute(
                """INSERT INTO price_observations (product_id, price_inr, pack_size, pack_unit, evidence, source)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (pid, p["price_inr"]["value"], p["pack_size"]["value"], p["pack_unit"]["value"],
                 p["price_inr"]["label"], p["price_inr"]["source"]))
        if p["nutrition_basis"]:
            for k in NUTRIENTS:
                ev = p["nutrition"][k]
                cur.execute(
                    """INSERT INTO nutrient_values (product_id, nutrient, basis, value, evidence, source, note)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (pid, k, p["nutrition_basis"], ev["value"], ev["label"], ev["source"], ev["note"]))
        if p["ingredients_raw"]["value"]:
            cur.execute(
                """INSERT INTO ingredients (product_id, ingredients_raw, normalised, additives_ins, allergens,
                                            evidence, source)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (pid, p["ingredients_raw"]["value"], json.dumps(p["ingredients_normalised"]), p["additives_ins"],
                 p["allergens"], p["ingredients_raw"]["label"], p["ingredients_raw"]["source"]))
        for c in d["claims"]["claims"]:
            cur.execute(
                """INSERT INTO claims (product_id, claim_id, matched_text, status, facts, rule)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (pid, c["claim_id"], c["matched_text"], c["status"], json.dumps(c["facts"]), c["rule"]))
        version = report["disclaimer"].split("Methodology v")[1].split(" ")[0]
        cur.execute(
            """INSERT INTO analyses (product_id, methodology_version, nutrition, ingredients, transparency,
                                     claims, value, overall, grade, report)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (pid, version, d["nutrition"]["score"], d["ingredients"]["score"], d["transparency"]["score"],
             d["claims"]["score"], d["value"]["score"], o["score"], o["grade"], json.dumps(report, default=str)))
    return pid
