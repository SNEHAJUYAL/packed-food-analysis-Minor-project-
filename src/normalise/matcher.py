"""Match a product to an Open Food Facts record (doc section 6, stage 3).

Open Food Facts is reference data, not ground truth (doc section 7): a match
adds a cross-check, it never overwrites the listing. Data is ODbL; credit it.
"""
from __future__ import annotations

from typing import Optional

import httpx
from rapidfuzz import fuzz

OFF_BASE = "https://world.openfoodfacts.org"
USER_AGENT = "FoodDecisionIntelligence/0.1 (academic project)"
MATCH_CUTOFF = 85


def by_barcode(code: str, client: Optional[httpx.Client] = None) -> Optional[dict]:
    client = client or httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20)
    r = client.get(f"{OFF_BASE}/api/v2/product/{code}.json")
    if r.status_code != 200:
        return None
    data = r.json()
    return data.get("product") if data.get("status") == 1 else None


def search(name: str, brand: Optional[str] = None, client: Optional[httpx.Client] = None,
           country: str = "india", page_size: int = 20) -> list[dict]:
    client = client or httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20)
    params = {"search_terms": " ".join(x for x in (brand, name) if x), "countries_tags_en": country,
              "page_size": page_size, "json": 1,
              "fields": "code,product_name,brands,quantity,nutriments,nutriscore_grade,ingredients_text,categories_tags"}
    r = client.get(f"{OFF_BASE}/cgi/search.pl", params=params)
    r.raise_for_status()
    return r.json().get("products", [])


def best_match(name: str, brand: Optional[str], candidates: list[dict]) -> Optional[dict]:
    """Highest token-set similarity on "brand name"; None below the cutoff."""
    target = f"{brand or ''} {name}".strip().lower()
    scored = []
    for c in candidates:
        label = f"{c.get('brands') or ''} {c.get('product_name') or ''}".strip().lower()
        scored.append((fuzz.token_set_ratio(target, label), c))
    if not scored:
        return None
    score, cand = max(scored, key=lambda x: x[0])
    if score < MATCH_CUTOFF:
        return None
    return {"score": score, "code": cand.get("code"), "product_name": cand.get("product_name"),
            "brands": cand.get("brands"), "nutriscore_grade": cand.get("nutriscore_grade"),
            "record": cand}
