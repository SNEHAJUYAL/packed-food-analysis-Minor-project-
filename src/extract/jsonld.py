"""Structured-metadata extraction: JSON-LD and microdata via extruct (doc section 6, stage 2).

Returns a raw ``Extracted`` dict. Values are kept as the page states them;
unit conversion happens in normalise/.
"""
from __future__ import annotations

from typing import Any, Optional

import extruct

# schema.org NutritionInformation property -> schema nutrient key
SCHEMA_NUTRITION = {
    "calories": "energy",
    "proteinContent": "protein",
    "carbohydrateContent": "carbohydrate",
    "sugarContent": "total_sugars",
    "fatContent": "total_fat",
    "saturatedFatContent": "saturated_fat",
    "transFatContent": "trans_fat",
    "fiberContent": "fibre",
    "sodiumContent": "sodium",
    "saltContent": "salt",  # not schema.org, but seen in the wild
}
UNIT_CODES = {"GRM": "g", "KGM": "kg", "MGM": "mg", "MLT": "ml", "LTR": "l", "CLT": "cl"}


def empty_extracted(source: str) -> dict:
    return {"source": source, "name": None, "brand": None, "description": None, "category_hint": None,
            "price": None, "currency": None, "pack_size_text": None, "ingredients_text": None,
            "nutrition": {}, "nutrition_basis_text": None, "claims_text": [], "gtin": None}


def _types(item: dict) -> list[str]:
    t = item.get("@type") or item.get("type") or []
    t = t if isinstance(t, list) else [t]
    return [str(x).rsplit("/", 1)[-1] for x in t]


def _walk(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _text(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, dict):
        return _text(v.get("name") or v.get("@value") or v.get("value"))
    if isinstance(v, list):
        return _text(v[0]) if v else None
    s = str(v).strip()
    return s or None


def _quantity_text(v: Any) -> Optional[str]:
    """QuantitativeValue {value, unitCode} or plain text -> "200 g"."""
    if isinstance(v, dict):
        val = v.get("value")
        unit = v.get("unitCode") or v.get("unitText") or ""
        unit = UNIT_CODES.get(str(unit).upper(), unit)
        return f"{val} {unit}".strip() if val is not None else None
    return _text(v)


def _offer(offers: Any) -> tuple[Optional[str], Optional[str]]:
    if isinstance(offers, list):
        offers = offers[0] if offers else None
    if not isinstance(offers, dict):
        return None, None
    price = offers.get("price") or offers.get("lowPrice")
    if price is None and isinstance(offers.get("priceSpecification"), dict):
        price = offers["priceSpecification"].get("price")
    return (_text(price), _text(offers.get("priceCurrency")))


def find_products(html: str, url: str) -> list[dict]:
    data = extruct.extract(html, base_url=url, syntaxes=["json-ld", "microdata"], uniform=True, errors="ignore")
    products = []
    for syntax in ("json-ld", "microdata"):
        for item in _walk(data.get(syntax, [])):
            if "Product" in _types(item) or "Food" in _types(item):
                products.append(item)
    return products


def parse_product(item: dict) -> dict:
    out = empty_extracted("json-ld")
    out["name"] = _text(item.get("name"))
    out["brand"] = _text(item.get("brand"))
    out["description"] = _text(item.get("description"))
    out["category_hint"] = _text(item.get("category"))
    out["gtin"] = _text(item.get("gtin13") or item.get("gtin") or item.get("gtin8"))
    out["price"], out["currency"] = _offer(item.get("offers"))
    out["pack_size_text"] = _quantity_text(item.get("weight") or item.get("size"))
    out["ingredients_text"] = _text(item.get("ingredients") or item.get("hasIngredient"))

    for prop in item.get("additionalProperty") or []:
        if not isinstance(prop, dict):
            continue
        name = (_text(prop.get("name")) or "").lower()
        value = _text(prop.get("value"))
        if not value:
            continue
        if "ingredient" in name and not out["ingredients_text"]:
            out["ingredients_text"] = value
        elif any(k in name for k in ("net weight", "net quantity", "net qty", "net wt", "weight")) \
                and not out["pack_size_text"]:
            out["pack_size_text"] = value
        elif "claim" in name or "feature" in name or "highlight" in name:
            out["claims_text"].append(value)

    nut = item.get("nutrition")
    if isinstance(nut, list):
        nut = nut[0] if nut else None
    if isinstance(nut, dict):
        out["nutrition_basis_text"] = _text(nut.get("servingSize"))
        for prop, key in SCHEMA_NUTRITION.items():
            raw = _text(nut.get(prop))
            if raw is not None:
                out["nutrition"][key] = raw
    if out["name"]:
        out["claims_text"].append(out["name"])
    if out["description"]:
        out["claims_text"].append(out["description"])
    return out


def extract_jsonld(html: str, url: str) -> Optional[dict]:
    """Best Product entity on the page (the one with the most fields), or None."""
    products = [parse_product(p) for p in find_products(html, url)]
    if not products:
        return None

    def richness(p: dict) -> int:
        return sum(1 for k, v in p.items() if v and k not in ("source", "claims_text")) + len(p["nutrition"])

    return max(products, key=richness)
