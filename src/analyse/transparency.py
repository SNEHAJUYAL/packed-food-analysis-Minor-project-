"""Transparency score T: how completely the product is disclosed.

Kept separate from nutrition: a complete label can describe a poor product (doc 8.3).
"""
from __future__ import annotations

from core.config import scoring_config
from core.schema import NUTRIENTS, Product


def _present(product: Product, field: str) -> bool:
    if field in NUTRIENTS:
        return product.nutrient(field) is not None
    return getattr(product, field).known


def analyse_transparency(product: Product, normalised: dict | None) -> dict:
    cfg = scoring_config()["transparency"]
    core = cfg["core_fields"]
    present = [f for f in core if _present(product, f)]
    missing = [f for f in core if f not in present]
    score = 100.0 * len(present) / len(core)
    why = [f"{len(present)}/{len(core)} core fields disclosed."]
    if missing:
        why.append("Missing: " + ", ".join(missing) + ".")
    bonus = [f for f in cfg["bonus_fields"] if _present(product, f)]
    if bonus:
        score += cfg["bonus_field_points"] * len(bonus)
        why.append("Also discloses " + ", ".join(bonus) + f": +{cfg['bonus_field_points']} each.")

    deduction = 0.0
    if normalised:
        generic = [it["text"] for it in normalised["items"] if "generic_additive" in it["classes"]]
        unspecified_oil = [it["text"] for it in normalised["items"] if "oil_unspecified" in it["classes"]]
        if generic:
            deduction += cfg["deduction_per_generic_declaration"] * len(generic)
            why.append(f"Additive class named without INS code ({', '.join(generic)}): "
                       f"-{cfg['deduction_per_generic_declaration']} each.")
        if unspecified_oil:
            deduction += cfg["deduction_unspecified_oil"]
            why.append(f"Oil source not disclosed ({', '.join(unspecified_oil)}): -{cfg['deduction_unspecified_oil']}.")
    score -= min(deduction, cfg["max_deduction"])
    return {"score": max(0.0, min(100.0, score)), "missing": missing, "explanation": why}
