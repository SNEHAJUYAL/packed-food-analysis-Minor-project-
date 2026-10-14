"""Category-aware nutrient benchmarks (doc section 8.2, Keyhole principle).

Thresholds come only from data/reference/thresholds.csv. A category-specific row
overrides the generic all_foods / all_drinks row for the same parameter and basis.
"""
from __future__ import annotations

from typing import Optional

from core.config import category_weights, scoring_config, thresholds
from normalise.units import sodium_mg_to_salt_g


def _generic_category(basis: str) -> str:
    return "all_drinks" if basis == "per_100ml" else "all_foods"


def benchmark_for(nutrient: str, category: Optional[str], basis: str) -> Optional[dict]:
    """Threshold row for a nutrient. Sodium is looked up as salt, because the
    sourced thresholds are for salt; see ``convert_for_benchmark``."""
    parameter = "salt" if nutrient == "sodium" else nutrient
    rows = [r for r in thresholds() if r["parameter"] == parameter and r["basis"] == basis]
    specific = [r for r in rows if r["category"] == category]
    generic = [r for r in rows if r["category"] == _generic_category(basis)]
    return (specific or generic or [None])[0]


def convert_for_benchmark(nutrient: str, value: float) -> float:
    return sodium_mg_to_salt_g(value) if nutrient == "sodium" else value


def subscore(nutrient: str, value: Optional[float], category: Optional[str], basis: str) -> dict:
    """0-100 sub-score, higher is better. Unknown when value or benchmark is missing."""
    row = benchmark_for(nutrient, category, basis)
    out = {"nutrient": nutrient, "value": value, "subscore": None, "benchmark": row, "reason": None}
    if value is None:
        out["reason"] = "value not declared"
        return out
    if row is None or row["green_bound"] is None:
        out["reason"] = "no sourced benchmark yet (TODO in thresholds.csv)"
        return out
    curve = scoring_config()["subscore_curve"]
    v = convert_for_benchmark(nutrient, value)
    g, r = row["green_bound"], row["red_bound"]
    if row["direction"] == "higher_better":
        s = min(100.0, 100.0 * max(v, 0.0) / g) if g > 0 else 100.0
    else:
        if r is None:
            out["reason"] = "no sourced red bound yet (TODO in thresholds.csv)"
            return out
        floor, zm = curve["amber_floor"], curve["zero_multiple"]
        if v <= g:
            s = 100.0
        elif v <= r:
            s = 100.0 - (100.0 - floor) * (v - g) / (r - g)
        else:
            s = max(0.0, floor * (1.0 - (v - r) / (r * zm - r)))
    out["subscore"] = round(s, 2)
    return out


def traffic_light(nutrient: str, value: Optional[float], category: Optional[str], basis: str) -> Optional[str]:
    """green / yellow / red against the sourced benchmark, or None when unknown."""
    row = benchmark_for(nutrient, category, basis)
    if value is None or row is None or row["green_bound"] is None:
        return None
    v = convert_for_benchmark(nutrient, value)
    g, r = row["green_bound"], row["red_bound"]
    if row["direction"] == "higher_better":
        if v >= g:
            return "green"
        if r is not None and v < r:
            return "red"
        return "yellow"
    if v <= g:
        return "green"
    if r is not None and v > r:
        return "red"
    return "yellow" if r is not None else None


def weights_for(category: Optional[str]) -> Optional[dict[str, float]]:
    return category_weights().get(category or "")
