"""Ingredient profile score I: what the ingredient list says about the product.

Deductions are prototype weights from config/scoring.json. They describe
processing and disclosure signals; they are not safety judgements.
"""
from __future__ import annotations

from core.config import scoring_config

ADDITIVE_GROUPS = ["artificial_sweetener", "synthetic_colour", "flavour_enhancer",
                   "synthetic_antioxidant", "preservative"]


def analyse_ingredients(normalised: dict | None) -> dict:
    if not normalised or not normalised["items"]:
        return {"score": None, "groups": {}, "explanation": ["Ingredient list not available."]}

    d = scoring_config()["ingredient_deductions"]
    items = normalised["items"]
    groups: dict[str, list[str]] = {}
    for it in items:
        for c in it["classes"]:
            groups.setdefault(c, []).append(it["text"])

    score = 100.0
    why = []
    sugar_pos = [it["position"] for it in items if "added_sugar" in it["classes"]]
    if sugar_pos:
        if min(sugar_pos) <= 3:
            score -= d["added_sugar_in_top3"]
            why.append(f"Added sugar appears at ingredient #{min(sugar_pos)} (top three): -{d['added_sugar_in_top3']}.")
        else:
            score -= d["added_sugar_present"]
            why.append(f"Added sugar listed (#{min(sugar_pos)}): -{d['added_sugar_present']}.")
    for cls, label in [("oil_palm", "Palm oil"), ("hydrogenated_fat", "Hydrogenated fat"),
                       ("artificial_flavour", "Artificial flavouring")]:
        if cls in groups:
            score -= d[cls]
            why.append(f"{label} listed: -{d[cls]}.")
    for g in ADDITIVE_GROUPS:
        if g in groups:
            score -= d[g]
            why.append(f"{g.replace('_', ' ').capitalize()} listed: -{d[g]}.")
    first = items[0]["classes"]
    if "refined_flour" in first:
        score -= d["refined_flour_first"]
        why.append(f"Refined flour is the first ingredient: -{d['refined_flour_first']}.")
    if "whole_grain" in first:
        score += d["whole_grain_first_bonus"]
        why.append(f"Whole grain is the first ingredient: +{d['whole_grain_first_bonus']}.")
    score = max(0.0, min(100.0, score))
    if not why:
        why.append("No flagged ingredient classes found.")
    if normalised["unmatched"]:
        why.append(f"{len(normalised['unmatched'])} ingredient(s) not in the dictionary yet: "
                   + ", ".join(normalised["unmatched"][:5]))
    return {"score": score, "groups": groups, "explanation": why}
