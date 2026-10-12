"""Download the Open Food Facts India subset for the five starting categories (doc section 7, source A).

    python scripts/fetch_off_india.py --per-category 200

Writes data/raw/off_india.csv (git-ignored). Open Food Facts data is under the
Open Database License: credit it and share-alike any derived database. It is
reference data, not ground truth.
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "off_india.csv"
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
NUTRIMENTS = {
    "energy": "energy-kcal_100g", "protein": "proteins_100g", "carbohydrate": "carbohydrates_100g",
    "total_sugars": "sugars_100g", "added_sugars": "added-sugars_100g", "total_fat": "fat_100g",
    "saturated_fat": "saturated-fat_100g", "trans_fat": "trans-fat_100g", "fibre": "fiber_100g",
    "sodium_g": "sodium_100g", "salt_g": "salt_100g",
}
FIELDS = ["code", "product_name", "brands", "quantity", "categories_tags", "ingredients_text",
          "additives_tags", "allergens_tags", "nutriscore_grade", "nutriments", "last_modified_t"]


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
    cols = ["category", "code", "product_name", "brands", "quantity", "ingredients_text", "additives",
            "allergens", "nutriscore_grade", *NUTRIMENTS, "last_modified_t"]
    n = 0
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60) as client, \
            open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for cat, tag in CATEGORIES.items():
            rows = fetch_category(client, tag, args.per_category)
            for p in rows:
                nm = p.get("nutriments") or {}
                w.writerow({
                    "category": cat, "code": p.get("code"), "product_name": p.get("product_name"),
                    "brands": p.get("brands"), "quantity": p.get("quantity"),
                    "ingredients_text": p.get("ingredients_text"),
                    "additives": "|".join(p.get("additives_tags") or []),
                    "allergens": "|".join(p.get("allergens_tags") or []),
                    "nutriscore_grade": p.get("nutriscore_grade"),
                    # Missing stays empty, never 0.
                    **{k: nm.get(v, "") for k, v in NUTRIMENTS.items()},
                    "last_modified_t": p.get("last_modified_t"),
                })
            n += len(rows)
            print(f"{cat}: {len(rows)} products", file=sys.stderr)
    print(f"wrote {n} rows to {OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
