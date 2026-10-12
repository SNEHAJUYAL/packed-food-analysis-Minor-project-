"""Plain-language reasons for each recommendation (doc gap 6: scores must explain themselves)."""
from __future__ import annotations


def _label(row: dict) -> str:
    name, brand = row.get("name"), row.get("brand")
    if not name:
        return f"product {row['index'] + 1}"
    return name if not brand or name.lower().startswith(brand.lower()) else f"{brand} {name}"


def explain_choice(kind: str, pick: dict, rows: list[dict]) -> str:
    others = [r for r in rows if r["index"] != pick["index"]]
    name = _label(pick)
    if kind == "lowest_price_per_100":
        priced = [r for r in others if r["price_per_100"] is not None]
        if not priced:
            return f"{name} is the only product with a known price per unit (₹{pick['price_per_100']:.2f})."
        nxt = min(priced, key=lambda r: r["price_per_100"])
        return (f"{name} costs ₹{pick['price_per_100']:.2f} per 100 g/ml, against "
                f"₹{nxt['price_per_100']:.2f} for the next cheapest ({_label(nxt)}).")
    if kind == "best_nutrition":
        return f"{name} has the highest nutrition score ({pick['nutrition']}/100) in this set."
    dims = pick["dimensions"]
    strong = sorted((k for k in dims if dims[k] is not None), key=lambda k: -dims[k])[:2]
    parts = ", ".join(f"{k} {dims[k]:.0f}" for k in strong)
    return (f"{name} scores highest for your priorities ({pick['priority_score']:.1f}/100); "
            f"strongest dimensions: {parts}.")
