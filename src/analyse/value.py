"""Value for money V: price per 100 g/ml against the category median (doc 8.3)."""
from __future__ import annotations

import math
from statistics import median
from typing import Optional

from core.config import scoring_config
from core.schema import Product
from normalise.units import price_per_100


def unit_price(product: Product) -> Optional[float]:
    if not (product.price_inr.known and product.pack_size.known):
        return None
    return round(price_per_100(product.price_inr.value, product.pack_size.value), 2)


def value_score(unit: Optional[float], category_median: Optional[float]) -> Optional[float]:
    """50 at the median, 100 at half the median or less, 0 at twice the median or more."""
    if unit is None or not category_median:
        return None
    at_median = scoring_config()["value_curve"]["at_median"]
    s = at_median - at_median * math.log2(unit / category_median)
    return round(max(0.0, min(100.0, s)), 2)


def analyse_value(product: Product, peer_unit_prices: list[float] | None = None) -> dict:
    unit = unit_price(product)
    per = "100 ml" if product.is_liquid else "100 g"
    if unit is None:
        return {"price_per_100": None, "category_median": None, "score": None, "peer_count": 0,
                "explanation": ["Price or pack size missing, so price per unit is unknown."]}
    peers = [p for p in (peer_unit_prices or []) if p is not None]
    med = median(peers) if peers else None
    score = value_score(unit, med)
    why = [f"₹{unit:.2f} per {per} (derived: ₹{product.price_inr.value:g} ÷ "
           f"{product.pack_size.value:g} {product.pack_unit.value} × 100)."]
    if med is None:
        why.append("No comparison set yet, so value for money is not scored.")
    else:
        why.append(f"Category median ₹{med:.2f} per {per} across {len(peers)} product(s).")
    return {"price_per_100": unit, "category_median": med, "score": score, "peer_count": len(peers),
            "explanation": why}
