"""Generate the SYNTHETIC demo dataset in data/sample/synthetic_products.jsonl.

These are not real products. Names use "Sample ..." and brands "Demo Brand ...",
barcodes start with "SYN-", and every record carries "_synthetic": true so the
API and UI label it. Values are drawn with a fixed seed from broad ranges per
category so that comparison, ranking and missing-data handling can be shown
offline. They must never be presented as measurements of real food.

The format mirrors the Open Food Facts product JSON, so the same ingestion code
(src/database/ingest.py) loads this file and a real OFF download.

    python scripts/make_synthetic_sample.py      # deterministic (seed 20261012)
"""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sample" / "synthetic_products.jsonl"
SEED = 20261012
PER_CATEGORY = 8

# name stem, OFF-style category tag, liquid?, pack sizes, price per 100 (INR) range,
# nutrient ranges per 100 g/ml, ingredient list templates, possible label claims
CATEGORIES = {
    "breakfast_cereals": dict(
        stem="Sample Cereal", tag="en:breakfast-cereals", liquid=False, packs=[250, 300, 375, 500, 700],
        price=(25, 70), energy=(340, 420), protein=(6, 14), carbohydrate=(60, 80), sugars=(1, 32), fat=(1, 12),
        sat=(0.2, 6), fibre=(2, 12), sodium=(5, 600),
        ingredients=["Whole Grain Wheat (60%), Sugar, Cocoa Solids, Edible Vegetable Oil (Palmolein), Iodised Salt, "
                     "Emulsifier (INS 322), Flavouring",
                     "Rolled Oats (100%)",
                     "Corn Grits, Sugar, Malt Extract, Iodised Salt, Antioxidant (INS 320)",
                     "Whole Grain Oats (55%), Ragi, Jaggery, Rice Bran Oil, Salt",
                     "Wheat Flakes (Refined Wheat Flour, Sugar, Salt), Honey, Liquid Glucose, Flavour Enhancer (INS 627)"],
        claims=["High protein", "High fibre", "No added sugar", "Low fat", "Source of fibre", "Made from natural ingredients"]),
    "biscuits_cookies": dict(
        stem="Sample Biscuit", tag="en:biscuits", liquid=False, packs=[75, 100, 150, 200, 250],
        price=(18, 60), energy=(430, 520), protein=(5, 9), carbohydrate=(60, 75), sugars=(8, 35), fat=(12, 26),
        sat=(5, 14), fibre=(1, 8), sodium=(150, 550),
        ingredients=["Refined Wheat Flour (Maida), Sugar, Edible Vegetable Oil (Palm), Invert Sugar Syrup, "
                     "Raising Agents (INS 500(ii), 503(ii)), Iodised Salt, Emulsifier (INS 322), Artificial Flavour",
                     "Whole Wheat Flour (Atta) (52%), Sugar, Palm Oil, Milk Solids, Raising Agent (INS 500(ii)), Salt",
                     "Refined Wheat Flour, Hydrogenated Vegetable Oil, Sugar, Cocoa Powder, Glucose, Colour (INS 150d)",
                     "Oats (30%), Whole Wheat Flour, Butter, Brown Sugar, Honey, Salt, Raising Agent (INS 500(ii))",
                     "Refined Wheat Flour, Sugar, Interesterified Vegetable Fat, Liquid Glucose, Salt, Flavouring"],
        claims=["Source of fibre", "No added sugar", "Trans fat free", "High fibre"]),
    "instant_noodles": dict(
        stem="Sample Noodles", tag="en:instant-noodles", liquid=False, packs=[70, 140, 280, 420],
        price=(15, 45), energy=(380, 480), protein=(7, 13), carbohydrate=(55, 70), sugars=(1, 6), fat=(10, 22),
        sat=(4, 10), fibre=(1, 7), sodium=(700, 1900),
        ingredients=["Noodles (Refined Wheat Flour (Maida), Palm Oil, Iodised Salt, Thickener (INS 508, 412)), "
                     "Masala Tastemaker (Spices, Sugar, Salt, Flavour Enhancer (INS 627, 631), Acidity Regulator (INS 330))",
                     "Whole Wheat Flour (Atta) (70%), Rice Bran Oil, Salt, Spices, Dehydrated Vegetables",
                     "Refined Wheat Flour, Palmolein, Salt, Sugar, Flavour Enhancer (INS 621), Colour (INS 150d)",
                     "Millet Flour (Ragi, Jowar), Whole Wheat Flour, Sunflower Oil, Salt, Spices"],
        claims=["Source of protein", "High fibre", "Low fat"]),
    "beverages": dict(
        stem="Sample Drink", tag="en:beverages", liquid=True, packs=[200, 250, 330, 600, 1000],
        price=(5, 25), energy=(0, 70), protein=(0, 3.5), carbohydrate=(0, 17), sugars=(0, 15), fat=(0, 3),
        sat=(0, 2), fibre=None, sodium=(0, 60),
        ingredients=["Carbonated Water, Sugar, Acidity Regulator (INS 338), Caffeine, Colour (INS 150d), Flavouring",
                     "Water, Mango Pulp (19%), Sugar, Acidity Regulator (INS 330), Antioxidant (INS 300)",
                     "Toned Milk, Sugar, Cocoa Powder, Stabiliser (INS 407)",
                     "Carbonated Water, Acidity Regulator (INS 330), Sweetener (INS 955), Preservative (INS 211)",
                     "Water, Orange Juice Concentrate (12%), Sugar, Colour (INS 110), Preservative (INS 211)"],
        claims=["Sugar free", "Low sugar", "No added sugar", "Low calorie", "Natural"]),
    "namkeen_chips": dict(
        stem="Sample Chips", tag="en:chips-and-fries", liquid=False, packs=[30, 52, 90, 150, 200],
        price=(25, 80), energy=(480, 580), protein=(4, 16), carbohydrate=(40, 60), sugars=(0.5, 6), fat=(25, 40),
        sat=(8, 18), fibre=(2, 8), sodium=(400, 1100),
        ingredients=["Potato, Edible Vegetable Oil (Palmolein), Iodised Salt, Spices and Condiments, "
                     "Flavour Enhancer (INS 627, 631)",
                     "Gram Flour (Besan), Edible Vegetable Oil, Moth Bean Flour, Salt, Spices",
                     "Potato, Rice Bran Oil, Salt",
                     "Corn Meal, Palm Oil, Seasoning (Sugar, Salt, Flavour Enhancer (INS 621), Colour (INS 102))"],
        claims=["Trans fat free", "Low fat", "Made from natural ingredients"]),
}


def r(rng: random.Random, lo_hi, nd=1):
    lo, hi = lo_hi
    return round(rng.uniform(lo, hi), nd)


def make(rng: random.Random, cat: str, cfg: dict, i: int) -> dict:
    unit = "ml" if cfg["liquid"] else "g"
    pack = rng.choice(cfg["packs"])
    per100 = r(rng, cfg["price"], 2)
    price = round(per100 * pack / 100.0)
    sugars = r(rng, cfg["sugars"])
    carbs = max(sugars, r(rng, cfg["carbohydrate"]))
    fat = r(rng, cfg["fat"])
    sat = min(fat, r(rng, cfg["sat"]))
    nutr = {
        "energy-kcal_100g": round(rng.uniform(*cfg["energy"])),
        "proteins_100g": r(rng, cfg["protein"]),
        "carbohydrates_100g": carbs,
        "sugars_100g": sugars,
        "fat_100g": fat,
        "saturated-fat_100g": sat,
        "sodium_100g": round(rng.uniform(*cfg["sodium"]) / 1000.0, 3),  # OFF stores sodium in g
    }
    if cfg["fibre"]:
        nutr["fiber_100g"] = r(rng, cfg["fibre"])
    if rng.random() < 0.5:
        nutr["trans-fat_100g"] = round(rng.uniform(0, 0.3), 2)
    # Missing-data cases: some records lack a value, a price or the ingredient list.
    gap = rng.random()
    if gap < 0.15:
        nutr.pop(rng.choice(["fiber_100g", "saturated-fat_100g", "sugars_100g"]), None)
    rec = {
        "_synthetic": True,
        "_note": "Synthetic demo record generated by scripts/make_synthetic_sample.py. Not a real product.",
        "code": f"SYN-{cat[:3].upper()}-{i:03d}",
        "product_name": f"{cfg['stem']} {chr(65 + i)}",
        "brands": f"Demo Brand {rng.choice('PQRS')}",
        "quantity": f"{pack} {unit}",
        "categories_tags": [cfg["tag"]],
        "countries_tags": ["en:india"],
        "nutrition_data_per": "100g",
        "nutriments": nutr,
        "ingredients_text": rng.choice(cfg["ingredients"]) if gap > 0.08 else None,
        "labels": ", ".join(rng.sample(cfg["claims"], k=rng.choice([0, 1, 1, 2]))),
        "_price_inr": price if gap < 0.9 else None,
    }
    return rec


def main() -> int:
    rng = random.Random(SEED)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(OUT, "w", encoding="utf-8") as fh:
        for cat, cfg in CATEGORIES.items():
            for i in range(PER_CATEGORY):
                fh.write(json.dumps(make(rng, cat, cfg, i), ensure_ascii=False) + "\n")
                n += 1
    print(f"wrote {n} synthetic records to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
