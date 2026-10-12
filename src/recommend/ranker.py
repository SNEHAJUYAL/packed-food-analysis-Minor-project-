"""Compare products in one category and pick alternatives (doc section 6, stage 7).

Returns three separate answers, each with a reason: the best match for the
user's priorities, the lowest price per 100 g/ml, and the best nutrition.
"""
from __future__ import annotations

from typing import Optional

from analyse.value import unit_price
from core.config import scoring_config
from core.schema import Product
from pipeline import analyse_product
from recommend.explain import explain_choice
from score.scorer import weighted


def compare(products: list[Product], priorities: Optional[dict[str, float]] = None) -> dict:
    cats = {p.category.value for p in products}
    if len(cats) > 1:
        raise ValueError(f"compare products within one category, got {sorted(map(str, cats))}")
    unit_prices = [unit_price(p) for p in products]
    peers = [u for u in unit_prices if u is not None]
    reports = [analyse_product(p, peers) for p in products]

    weights = priorities or scoring_config()["dimension_weights"]
    total = sum(weights.values())
    weights = {k: v / total for k, v in weights.items()}

    rows = []
    for i, (p, r) in enumerate(zip(products, reports)):
        dims = {k: r["dimensions"][k]["score"] for k in weights}
        pref = weighted(dims, weights) if any(v is not None for v in dims.values()) else {"raw": None}
        rows.append({
            "index": i,
            "name": p.name.value,
            "brand": p.brand.value,
            "overall": r["overall"]["score"],
            "grade": r["overall"]["grade"],
            "priority_score": pref["raw"],
            "nutrition": r["dimensions"]["nutrition"]["score"],
            "price_per_100": unit_prices[i],
            "dimensions": {k: r["dimensions"][k]["score"] for k in r["dimensions"]},
        })

    def best(key: str, lowest: bool = False) -> Optional[dict]:
        cand = [x for x in rows if x[key] is not None]
        if not cand:
            return None
        return (min if lowest else max)(cand, key=lambda x: x[key])

    picks = {
        "best_match": best("priority_score"),
        "lowest_price_per_100": best("price_per_100", lowest=True),
        "best_nutrition": best("nutrition"),
    }
    ranked = sorted(rows, key=lambda x: (x["priority_score"] is None, -(x["priority_score"] or 0)))
    return {
        "category": next(iter(cats)),
        "priorities": weights,
        "ranking": ranked,
        "picks": {k: ({**v, "reason": explain_choice(k, v, rows)} if v else None) for k, v in picks.items()},
        "reports": reports,
    }
