"""Load Open Food Facts product records (or the synthetic sample in the same format) into the database.

    python -m database.ingest data/raw/off_india.jsonl            # real OFF download (scripts/fetch_off_india.py)
    python -m database.ingest data/sample/synthetic_products.jsonl  # offline demo records, labelled synthetic

Each record goes through the same normalisation as a URL (build_product), so units,
evidence labels and missing values are handled once. OFF data is ODbL: credit it.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import read_csv
from core.schema import Evidence, EvidenceLabel
from database import repository as repo
from database.models import ProductRow, ProductSource
from database.session import session_scope
from normalise.build import build_product

log = logging.getLogger("fdi.ingest")
OFF_PRODUCT_URL = "https://world.openfoodfacts.org/product/{code}"

# OFF nutriment key -> (extraction key, unit as stored by OFF)
NUTRIMENTS = {
    "energy-kcal_100g": ("energy", "kcal"), "proteins_100g": ("protein", "g"),
    "carbohydrates_100g": ("carbohydrate", "g"), "sugars_100g": ("total_sugars", "g"),
    "added-sugars_100g": ("added_sugars", "g"), "fat_100g": ("total_fat", "g"),
    "saturated-fat_100g": ("saturated_fat", "g"), "trans-fat_100g": ("trans_fat", "g"),
    "fiber_100g": ("fibre", "g"), "sodium_100g": ("sodium", "g"),
}


def category_map() -> dict[str, str]:
    return {r["off_tag"]: r["category"] for r in read_csv("off_category_map.csv")}


def category_for(tags: Iterable[str]) -> Optional[str]:
    m = category_map()
    for t in tags or []:
        if t in m:
            return m[t]
    return None


def to_extraction(p: dict) -> dict:
    """Map one OFF product JSON to the extractor output format used by build_product."""
    synthetic = bool(p.get("_synthetic"))
    nm = p.get("nutriments") or {}
    nutrition = {}
    for off_key, (key, unit) in NUTRIMENTS.items():
        v = nm.get(off_key)
        if v not in (None, ""):
            nutrition[key] = f"{v} {unit}"
    if "energy" not in nutrition and nm.get("energy_100g") not in (None, ""):
        nutrition["energy"] = f"{nm['energy_100g']} kJ"
    if "sodium" not in nutrition and nm.get("salt_100g") not in (None, ""):
        nutrition["salt"] = f"{nm['salt_100g']} g"
    qty = p.get("quantity") or ""
    liquid = qty.strip().lower().endswith(("ml", "l", "cl"))
    claims = [c.strip() for c in (p.get("labels") or "").split(",") if c.strip()]
    return {
        "source": "synthetic-sample" if synthetic else "open-food-facts",
        "name": p.get("product_name") or None, "brand": (p.get("brands") or "").split(",")[0].strip() or None,
        "description": None, "category_hint": " ".join(p.get("categories_tags") or []),
        "price": p.get("_price_inr"), "currency": "INR" if p.get("_price_inr") else None,
        "pack_size_text": qty or None, "ingredients_text": p.get("ingredients_text") or None,
        "nutrition": nutrition,
        "nutrition_basis_text": ("100 ml" if liquid else "100 g") if nutrition else None,
        "claims_text": [p.get("product_name") or ""] + claims, "gtin": p.get("code"),
    }


def ingest_records(s: Session, records: Iterable[dict], rescore: bool = True) -> dict:
    stats = {"loaded": 0, "skipped_no_category": 0, "skipped_no_name": 0}
    for p in records:
        cat = category_for(p.get("categories_tags") or [])
        if cat is None:
            stats["skipped_no_category"] += 1
            continue
        if not p.get("product_name"):
            stats["skipped_no_name"] += 1
            continue
        synthetic = bool(p.get("_synthetic"))
        code = str(p.get("code"))
        url = None if synthetic else OFF_PRODUCT_URL.format(code=code)
        product = build_product([to_extraction(p)], url=url, category_override=None)
        product.category = Evidence(value=cat, label=EvidenceLabel.INTERPRETED, source="off_category_map.csv",
                                    note="mapped from Open Food Facts categories_tags")
        if p.get("last_modified_t"):
            product.collected_at = datetime.fromtimestamp(int(p["last_modified_t"]), timezone.utc).isoformat()
        repo.save_product(
            s, product, source_type="synthetic_sample" if synthetic else "open_food_facts",
            external_id=("sample:" if synthetic else "off:") + code, barcode=None if synthetic else code,
            extraction_method="off-json" if not synthetic else "synthetic-json",
            extraction_log=[{"step": "ingest", "outcome": "ok",
                             "detail": "synthetic demo record (not a real product)" if synthetic
                             else "Open Food Facts record (ODbL), crowdsourced reference data"}])
        stats["loaded"] += 1
    s.flush()
    repo.seed_rules(s)
    if rescore:
        from services import rescore_all
        stats["analysed"] = rescore_all(s)
    return stats


def read_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def purge_synthetic(s: Session) -> int:
    ids = set(s.scalars(select(ProductSource.product_id).where(ProductSource.source_type == "synthetic_sample")))
    for pid in ids:
        s.delete(s.get(ProductRow, pid))
    s.flush()
    return len(ids)


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", nargs="?", type=Path)
    ap.add_argument("--purge-synthetic", action="store_true", help="delete the synthetic demo records first")
    ap.add_argument("--rules-only", action="store_true", help="only load regulatory rules")
    ap.add_argument("--rescore", action="store_true", help="only recompute every stored analysis")
    ap.add_argument("--if-empty", action="store_true", help="skip loading when products already exist")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    with session_scope() as s:
        if args.purge_synthetic:
            print(f"removed {purge_synthetic(s)} synthetic records")
        if args.rescore:
            from services import rescore_all
            print(f"rescored {rescore_all(s)} products")
            return 0
        if args.if_empty and repo.count_products(s):
            print(f"{repo.count_products(s)} products already stored; nothing loaded")
            repo.seed_rules(s)
            return 0
        if args.rules_only or args.path is None:
            print(f"loaded {repo.seed_rules(s)} regulatory rules")
            return 0
        stats = ingest_records(s, read_jsonl(args.path))
    print(json.dumps(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
