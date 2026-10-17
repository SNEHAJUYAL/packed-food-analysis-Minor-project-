"""Alternatives and comparisons from stored records only (spec: recommendations).

1. Comparable products first: same category, same nutrition basis, an overall score.
2. Rule-based eligibility for the chosen preference (it must be better on that preference).
3. Multi-criteria ranking: preference score, then TF-IDF similarity as the tie-break.
4. Separate picks: best match, lowest unit price, best nutrition, each with a reason.
5. Scope: when the product came from a shop page (blinkit.com, zeptonow.com...), alternatives come from
   products already analysed from that same shop; if none qualifies, all stored products are used and the
   response says so. The shop's catalogue is never crawled.
Nothing is generated: every alternative is a database record with its source.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from core.config import scoring_config
from database import repository as repo
from database.models import AnalysisResult, ProductRow
from recommend.similarity import similar

PREFERENCES = ("balanced", "nutrition", "price", "transparency")
SCOPES = ("same_site", "all")
PER = {"per_100g": "100 g", "per_100ml": "100 ml"}
LOWER_BETTER = (("total_sugars", "sugar", "g"), ("saturated_fat", "saturated fat", "g"), ("sodium", "sodium", "mg"))
HIGHER_BETTER = (("fibre", "fibre", "g"), ("protein", "protein", "g"))


def _label(row: ProductRow) -> str:
    name, brand = row.name or f"product #{row.id}", row.brand
    return name if not brand or name.lower().startswith(brand.lower()) else f"{brand} {name}"


def _pref_value(res: AnalysisResult, preference: str) -> Optional[float]:
    if preference == "balanced":
        return res.overall_score
    if preference == "nutrition":
        return res.nutrition_score
    if preference == "transparency":
        return res.transparency_score
    return res.price_per_100  # price: lower is better


def _nutrient(res: AnalysisResult, key: str) -> Optional[float]:
    fact = res.report["dimensions"]["nutrition"]["facts"].get(key) or {}
    return fact.get("value")


def _classes(res: AnalysisResult) -> set[str]:
    return set(res.report["dimensions"]["ingredients"].get("groups") or {})


def matching_attributes(src: ProductRow, src_res: AnalysisResult, row: ProductRow, res: AnalysisResult) -> list[str]:
    out = [f"same category ({(row.category or '').replace('_', ' ')})", f"same basis (per {PER[row.nutrition_basis]})"]
    if src.pack_size and row.pack_size and 0.5 <= row.pack_size / src.pack_size <= 2:
        out.append(f"similar pack size ({row.pack_size:g} {row.pack_unit} vs {src.pack_size:g} {src.pack_unit})")
    shared = sorted(_classes(src_res) & _classes(res) - {"generic_additive"})
    if shared:
        out.append("shared ingredient types: " + ", ".join(c.replace("_", " ") for c in shared[:4]))
    return out


def rationale(src: ProductRow, src_res: AnalysisResult, row: ProductRow, res: AnalysisResult, preference: str) -> str:
    per = PER[row.nutrition_basis]
    parts = []
    if preference == "price":
        if src_res.price_per_100 is not None:
            parts.append(f"costs ₹{res.price_per_100:.2f} per {per} against ₹{src_res.price_per_100:.2f}")
        else:
            parts.append(f"costs ₹{res.price_per_100:.2f} per {per} (this product's price is unknown)")
    if preference == "nutrition" and res.nutrition_score is not None:
        parts.append(f"nutrition score {res.nutrition_score:.0f} against "
                     + (f"{src_res.nutrition_score:.0f}" if src_res.nutrition_score is not None else "not scored"))
    if preference == "transparency":
        parts.append(f"transparency score {res.transparency_score:.0f} against {src_res.transparency_score:.0f}")
    if res.overall_score is not None:
        parts.append(f"overall {res.overall_score} ({res.grade}) against "
                     + (f"{src_res.overall_score} ({src_res.grade})" if src_res.overall_score is not None
                        else "no overall score"))
    for key, label, unit in LOWER_BETTER:
        a, b = _nutrient(src_res, key), _nutrient(res, key)
        if a is not None and b is not None and b < a * 0.9:
            parts.append(f"less {label} ({b:g} {unit} vs {a:g} {unit} per {per})")
    for key, label, unit in HIGHER_BETTER:
        a, b = _nutrient(src_res, key), _nutrient(res, key)
        if a is not None and b is not None and b > a * 1.1:
            parts.append(f"more {label} ({b:g} {unit} vs {a:g} {unit} per {per})")
    return f"{_label(row)}: " + "; ".join(parts[:4]) + "."


def _site(row: ProductRow) -> Optional[str]:
    return row.sources[-1].site if row.sources else None


def _not_worse_overall(res: AnalysisResult, src_res: AnalysisResult) -> bool:
    return src_res.overall_score is None or res.overall_score >= src_res.overall_score


def _better(res: AnalysisResult, src_res: AnalysisResult, preference: str) -> bool:
    """Better on the chosen preference (for price: cheaper per unit and not worse overall)."""
    v, src_val = _pref_value(res, preference), _pref_value(src_res, preference)
    if v is None:
        return False
    if src_val is None:
        return True
    if preference == "price":
        return v < src_val and _not_worse_overall(res, src_res)
    return v > src_val


def alternatives(s: Session, product_id: int, preference: str = "balanced", limit: int = 5,
                 store: bool = True, scope: str = "same_site") -> Optional[dict]:
    if preference not in PREFERENCES:
        raise ValueError(f"preference must be one of {PREFERENCES}")
    if scope not in SCOPES:
        raise ValueError(f"scope must be one of {SCOPES}")
    src = repo.get_row(s, product_id)
    if src is None:
        return None
    src_res = repo.latest_analysis(s, product_id)
    version = scoring_config()["methodology_version"]
    base = {"source_product_id": product_id, "preference": preference, "methodology_version": version,
            "eligible_count": 0, "alternatives": [],
            "picks": {"best_match": None, "lowest_unit_price": None, "best_nutrition": None}, "message": None,
            "site": _site(src), "scope": "all"}
    if src_res is None:
        base["message"] = "This product has not been analysed yet."
        return base
    if not src.category or not src.nutrition_basis:
        base["message"] = ("The category or nutrition basis of this product is unknown, so comparable "
                           "products cannot be selected.")
        return base

    pool = [(r, a) for r, a in repo.latest_analyses(s, src.category)
            if r.id != src.id and r.nutrition_basis == src.nutrition_basis and a.overall_score is not None]
    if not pool:
        base["message"] = "No other stored product in this category has enough data to compare."
        return base
    notes = []
    if scope == "same_site" and base["site"]:
        same = [(r, a) for r, a in pool if _site(r) == base["site"]]
        if any(_better(a, src_res, preference) for _, a in same):
            pool, base["scope"] = same, "same_site"
        else:
            notes.append(f"No other product analysed from {base['site']} does better, so these come from all "
                         "stored products. Analyse more products from that site to compare within it.")
    base["eligible_count"] = len(pool)

    sims = dict(similar(repo.to_product(src), [repo.to_product(r) for r, _ in pool], k=len(pool),
                        same_category=False))

    def not_worse_overall(res: AnalysisResult) -> bool:
        return _not_worse_overall(res, src_res)

    eligible = [(i, r, a) for i, (r, a) in enumerate(pool) if _better(a, src_res, preference)]
    sign = 1 if preference == "price" else -1
    eligible.sort(key=lambda t: (sign * _pref_value(t[2], preference), -sims.get(t[0], 0.0)))

    out = []
    for rank, (i, r, a) in enumerate(eligible[:limit], start=1):
        out.append({"product_id": r.id, "rank": rank, "name": r.name, "brand": r.brand,
                    "is_synthetic": repo.is_synthetic(r), "overall": a.overall_score, "grade": a.grade,
                    "nutrition": a.nutrition_score, "transparency": a.transparency_score,
                    "price_per_100": a.price_per_100, "similarity": sims.get(i),
                    "preference_score": _pref_value(a, preference),
                    "matching_attributes": matching_attributes(src, src_res, r, a),
                    "rationale": rationale(src, src_res, r, a, preference),
                    "source_url": repo.source_info(r)["source_url"], "site": _site(r),
                    "collected_at": repo.source_info(r)["collected_at"]})
    base["alternatives"] = out
    if not out:
        what = {"balanced": "overall", "nutrition": "nutrition", "transparency": "transparency",
                "price": "price per unit without a lower overall score"}[preference]
        notes.append(f"No stored product in this category does better on {what} than this one.")
    base["message"] = " ".join(notes) or None

    def pick(cands, key, lowest=False, reason=""):
        cands = [(r, a) for r, a in cands if key(a) is not None]
        if not cands:
            return None
        r, a = (min if lowest else max)(cands, key=lambda t: key(t[1]))
        return {"product_id": r.id, "name": r.name, "brand": r.brand, "is_synthetic": repo.is_synthetic(r),
                "reason": reason.format(label=_label(r), v=key(a))}

    better_overall = [(r, a) for r, a in pool if not_worse_overall(a)]
    best = out[0] if out else None
    base["picks"] = {
        "best_match": ({"product_id": best["product_id"], "name": best["name"], "brand": best["brand"],
                        "is_synthetic": best["is_synthetic"], "reason": best["rationale"]} if best else None),
        "lowest_unit_price": pick([(r, a) for r, a in better_overall
                                   if src_res.price_per_100 is None or (a.price_per_100 or 1e9) < src_res.price_per_100],
                                  lambda a: a.price_per_100, lowest=True,
                                  reason="{label} has the lowest price per unit (₹{v:.2f}) among stored products "
                                         "with an overall score at least as high as this one."),
        "best_nutrition": pick([(r, a) for r, a in pool if src_res.nutrition_score is None
                                or (a.nutrition_score or 0) > src_res.nutrition_score],
                               lambda a: a.nutrition_score,
                               reason="{label} has the highest nutrition score ({v:.0f}) in this category."),
    }
    if store and out:
        repo.save_recommendations(s, product_id, preference, out)
    return base


def compare_stored(s: Session, product_ids: list[int], priorities: Optional[dict[str, float]] = None) -> dict:
    """Compare stored products on one basis. Raises ValueError for mixed categories or bases."""
    rows = []
    for pid in product_ids:
        row = repo.get_row(s, pid)
        if row is None:
            raise LookupError(f"product {pid} not found")
        res = repo.latest_analysis(s, pid)
        if res is None:
            from services import analyse_row
            analyse_row(s, row)
            res = repo.latest_analysis(s, pid)
        rows.append((row, res))
    cats = {r.category for r, _ in rows}
    bases = {r.nutrition_basis for r, _ in rows if r.nutrition_basis}
    if len(cats) > 1:
        raise ValueError("Compare products from one category: got " + ", ".join(sorted(str(c) for c in cats)))
    if len(bases) > 1:
        raise ValueError("These products use different nutrition bases (per 100 g and per 100 ml).")

    weights = priorities or scoring_config()["dimension_weights"]
    total = sum(weights.values()) or 1.0
    weights = {k: v / total for k, v in weights.items()}
    core = scoring_config()["transparency"]["core_fields"]

    products = []
    for row, res in rows:
        rep = res.report
        dims = {k: rep["dimensions"][k]["score"] for k in ("nutrition", "ingredients", "transparency", "claims", "value")}
        known = {k: v for k, v in dims.items() if v is not None and k in weights}
        wsum = sum(weights[k] for k in known)
        pref = round(sum(weights[k] * v for k, v in known.items()) / wsum, 1) if wsum else None
        missing = set(rep["missing_fields"])
        products.append({
            "product_id": row.id, "name": row.name, "brand": row.brand, "is_synthetic": repo.is_synthetic(row),
            "overall": res.overall_score, "grade": res.grade, "status": res.status, "dimensions": dims,
            "priority_score": pref,
            "nutrition": {k: {"value": v["value"], "label": v["evidence"], "unit": v["unit"]}
                          for k, v in rep["dimensions"]["nutrition"]["facts"].items()},
            "price_per_100": res.price_per_100,
            "completeness": round(sum(1 for f in core if f not in missing) / len(core), 2),
            "ingredient_classes": sorted(_classes(res)),
            "claims": [{"matched_text": c["matched_text"], "claim_id": c["claim_id"], "status": c["status"]}
                       for c in rep["dimensions"]["claims"]["claims"]],
            "source_url": repo.source_info(row)["source_url"], "collected_at": repo.source_info(row)["collected_at"],
        })

    all_classes = [set(p["ingredient_classes"]) for p in products]
    shared = set.intersection(*all_classes) if all_classes else set()
    diffs = {"shared_classes": sorted(shared),
             "only_in": {str(p["product_id"]): sorted(set(p["ingredient_classes"]) - shared) for p in products}}

    def best(key, lowest=False):
        c = [p for p in products if p[key] is not None]
        return (min if lowest else max)(c, key=lambda p: p[key]) if c else None

    def name(p):
        return p["name"] if not p["brand"] or (p["name"] or "").lower().startswith(p["brand"].lower()) \
            else f"{p['brand']} {p['name']}"

    per = PER.get(next(iter(bases), "per_100g"), "100 g")
    picks, rationale_lines = {}, []
    b = best("priority_score")
    picks["best_match"] = {"product_id": b["product_id"],
                           "reason": f"{name(b)} has the highest score for the chosen priorities "
                                     f"({b['priority_score']}/100)."} if b else None
    c = best("price_per_100", lowest=True)
    picks["lowest_price_per_100"] = {"product_id": c["product_id"],
                                     "reason": f"{name(c)} costs ₹{c['price_per_100']:.2f} per {per}, the lowest "
                                               "in this set."} if c else None
    nut = [p for p in products if p["dimensions"]["nutrition"] is not None]
    n = max(nut, key=lambda p: p["dimensions"]["nutrition"]) if nut else None
    picks["best_nutrition"] = {"product_id": n["product_id"],
                               "reason": f"{name(n)} has the highest nutrition score "
                                         f"({n['dimensions']['nutrition']:.0f}/100)."} if n else None
    for p in products:
        if p["status"] != "complete":
            rationale_lines.append(f"{name(p)}: data is {p['status'].replace('_', ' ')}; missing values are "
                                   "shown as unknown, not zero.")
    if not c:
        rationale_lines.append("No product in this set has a known price per unit.")
    return {"category": next(iter(cats)), "basis": next(iter(bases), None),
            "methodology_version": scoring_config()["methodology_version"], "priorities": weights,
            "products": products, "ingredient_differences": diffs, "picks": picks, "rationale": rationale_lines}
