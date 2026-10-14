"""Nutrition analysis: traffic lights, sub-scores and the nutrition score N."""
from __future__ import annotations

from core.schema import NUTRIENTS, Product
from score.category_rules import subscore, traffic_light, weights_for
from score.scorer import nutrition_score

LIGHT_NUTRIENTS = ["total_sugars", "saturated_fat", "total_fat", "sodium", "fibre", "protein", "energy"]


def analyse_nutrition(product: Product) -> dict:
    category = product.category.value
    basis = product.nutrition_basis
    facts = {k: {"value": product.nutrient(k), "unit": NUTRIENTS[k],
                 "evidence": product.nutrition[k].label.value} for k in NUTRIENTS}
    if basis is None:
        return {
            "basis": None, "facts": facts, "traffic_lights": {}, "subscores": {},
            "score": None, "detail": None,
            "explanation": ["Nutrition basis (per 100 g / per 100 ml) is unknown, so nutrients "
                            "cannot be compared with benchmarks."],
        }

    lights = {}
    for k in LIGHT_NUTRIENTS:
        light = traffic_light(k, product.nutrient(k), category, basis)
        if light:
            lights[k] = light

    weights = weights_for(category)
    explanation = []
    if not weights:
        explanation.append(f"No category weights for '{category}'; nutrition score not computed. "
                           "Set a category from data/reference/category_weights.csv.")
        return {"basis": basis, "facts": facts, "traffic_lights": lights, "subscores": {},
                "score": None, "detail": None, "explanation": explanation}

    subs = {k: subscore(k, product.nutrient(k), category, basis) for k in weights}
    detail = nutrition_score({k: v["subscore"] for k, v in subs.items()}, weights)
    for k, s in subs.items():
        if s["subscore"] is None:
            explanation.append(f"{k}: left out ({s['reason']}).")
    if detail["score"] is None:
        explanation.append(f"Only {detail['coverage']:.0%} of the nutrition weight could be scored; "
                           "below the minimum, so N is unknown.")
    elif detail["missing"]:
        explanation.append(f"N uses {detail['coverage']:.0%} of the category weight; weights of the "
                           "scored nutrients were renormalised.")
    for k, light in lights.items():
        explanation.append(f"{k} {facts[k]['value']:g} {NUTRIENTS[k]} per 100 "
                           f"{'ml' if basis == 'per_100ml' else 'g'}: {light}.")
    return {"basis": basis, "facts": facts, "traffic_lights": lights,
            "subscores": {k: {"subscore": v["subscore"], "reason": v["reason"],
                              "benchmark_source": (v["benchmark"] or {}).get("source")}
                          for k, v in subs.items()},
            "score": detail["score"], "detail": detail, "explanation": explanation}
