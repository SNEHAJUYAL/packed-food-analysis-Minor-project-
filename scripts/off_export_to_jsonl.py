"""Filter the official Open Food Facts CSV export down to India records in the five categories.

Alternative to scripts/fetch_off_india.py when the OFF API is not reachable. The export is published
by Open Food Facts on AWS Open Data (ODbL). Stream it, so the 13 GB file never lands on disk:

    curl -sS https://openfoodfacts-ds.s3.eu-west-3.amazonaws.com/en.openfoodfacts.org.products.csv.gz \
      | gunzip | python scripts/off_export_to_jsonl.py > data/raw/off_india.jsonl

Output: one OFF-style product JSON per line (the same shape the API returns), loaded with
`python -m database.ingest data/raw/off_india.jsonl`. Empty cells stay absent, never 0.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
csv.field_size_limit(sys.maxsize)

NUTRIMENTS = ["energy-kcal_100g", "energy_100g", "proteins_100g", "carbohydrates_100g", "sugars_100g",
              "added-sugars_100g", "fat_100g", "saturated-fat_100g", "trans-fat_100g", "fiber_100g",
              "salt_100g", "sodium_100g"]


def wanted_tags() -> set[str]:
    with open(ROOT / "data" / "reference" / "off_category_map.csv", encoding="utf-8") as fh:
        return {r["off_tag"] for r in csv.DictReader(fh)}


def num(cell: str):
    try:
        return float(cell) if cell not in ("", None) else None
    except ValueError:
        return None


def main() -> int:
    tags = wanted_tags()
    reader = csv.DictReader(sys.stdin, delimiter="\t", quoting=csv.QUOTE_NONE)
    seen = kept = 0
    for row in reader:
        seen += 1
        if "en:india" not in (row.get("countries_tags") or "").split(","):
            continue
        cats = [t for t in (row.get("categories_tags") or "").split(",") if t]
        if not tags.intersection(cats) or not row.get("product_name"):
            continue
        nutriments = {k: v for k in NUTRIMENTS if (v := num(row.get(k))) is not None}
        rec = {
            "code": row["code"], "product_name": row["product_name"], "brands": row.get("brands") or None,
            "quantity": row.get("quantity") or None, "categories_tags": cats,
            "countries_tags": (row.get("countries_tags") or "").split(","),
            "ingredients_text": row.get("ingredients_text") or None, "labels": row.get("labels_en") or None,
            "nutriscore_grade": row.get("nutriscore_grade") or None, "nutriments": nutriments,
            "last_modified_t": int(row["last_modified_t"]) if (row.get("last_modified_t") or "").isdigit() else None,
            "_export": "en.openfoodfacts.org.products.csv",
        }
        sys.stdout.write(json.dumps(rec, ensure_ascii=False) + "\n")
        kept += 1
        if kept % 100 == 0:
            print(f"kept {kept} of {seen} rows read", file=sys.stderr, flush=True)
    print(f"done: kept {kept} of {seen} rows", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
