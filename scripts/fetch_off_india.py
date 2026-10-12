"""Download the Open Food Facts India subset for the five starting categories (doc section 7, source A).

    python scripts/fetch_off_india.py --per-category 200

Writes data/raw/off_india.jsonl (git-ignored), loaded by `python -m database.ingest`. Open Food Facts data is under the
Open Database License: credit it and share-alike any derived database. It is
reference data, not ground truth.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "off_india.jsonl"
API = "https://world.openfoodfacts.org/api/v2/search"
USER_AGENT = "FoodDecisionIntelligence/0.1 (academic project, MSIT GGSIPU)"

# OFF category tags for the doc's starting categories.
CATEGORIES = {
    "biscuits_cookies": "en:biscuits",
    "breakfast_cereals": "en:breakfast-cereals",
    "instant_noodles": "en:instant-noodles",
    "beverages": "en:beverages",
    "namkeen_chips": "en:chips-and-fries",
}
FIELDS = ["code", "product_name", "brands", "quantity", "categories_tags", "countries_tags", "ingredients_text",
          "labels", "nutriments", "nutrition_data_per", "nutriscore_grade", "last_modified_t"]


def fetch_category(client: httpx.Client, tag: str, limit: int) -> list[dict]:
    out, page = [], 1
    while len(out) < limit:
        r = client.get(API, params={"countries_tags": "en:india", "categories_tags": tag,
                                    "fields": ",".join(FIELDS), "page_size": 100, "page": page})
        r.raise_for_status()
        products = r.json().get("products", [])
        if not products:
            break
        out.extend(products)
        page += 1
        time.sleep(1.0)  # be polite to the public API
    return out[:limit]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-category", type=int, default=200)
    args = ap.parse_args()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60) as client, \
            open(OUT, "w", encoding="utf-8") as fh:
        for cat, tag in CATEGORIES.items():
            rows = fetch_category(client, tag, args.per_category)
            for p in rows:
                # Raw OFF JSON, one product per line; missing values stay missing (never 0).
                fh.write(json.dumps(p, ensure_ascii=False) + "\n")
            n += len(rows)
            print(f"{cat}: {len(rows)} products", file=sys.stderr)
    print(f"wrote {n} products to {OUT} (load with: python -m database.ingest {OUT})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
