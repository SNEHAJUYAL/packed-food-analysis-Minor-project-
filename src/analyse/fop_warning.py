"""Simulate the proposed FSSAI front-of-pack warning (doc section 13.1).

The rule is a draft under Supreme Court supervision, so thresholds live in
data/reference/fop_warning.csv and stay TODO until the final text is copied in.
"""
from __future__ import annotations

from core.config import fop_warning_rules
from core.schema import Product


def simulate_fop_warning(product: Product) -> dict:
    basis = product.nutrition_basis
    if basis is None:
        return {"status": "not simulated", "triggers": [], "reason": "nutrition basis unknown"}
    rules = [r for r in fop_warning_rules() if r["basis"] == basis]
    pending = [r["nutrient"] for r in rules if r["high_threshold"] is None]
    triggers, unknown = [], []
    for r in rules:
        if r["high_threshold"] is None:
            continue
        v = product.nutrient(r["nutrient"])
        if v is None:
            unknown.append(r["nutrient"])
        elif v > r["high_threshold"]:
            triggers.append({"nutrient": r["nutrient"], "value": v, "threshold": r["high_threshold"],
                             "unit": r["unit"], "source": r["source"]})
    if pending and len(pending) == len(rules):
        return {"status": "not simulated", "triggers": [], "reason":
                "Draft FSSAI thresholds not yet copied into fop_warning.csv (TODO)."}
    return {"status": "warning" if triggers else "no warning", "triggers": triggers,
            "unknown": unknown, "pending_rules": pending,
            "reason": "Simulation of a draft rule, not a regulatory finding."}
