"""Nutrition score N and Food Intelligence score S (doc sections 8.2-8.4).

    N = sum_i w_i * s_i,  sum_i w_i = 1
    S = 0.40 N + 0.25 I + 0.15 T + 0.10 C + 0.10 V

Dimension scores are rounded half-up to integers before they are combined,
which is how the worked example gets N = 52.5 -> 53 and S = 57.75 -> 58 (C).

When an input is unknown it is left out and the remaining weights are
renormalised; the result records the coverage so the gap stays visible.
"""
from __future__ import annotations

from typing import Optional

from core.config import scoring_config
from score.grade import grade, round_half_up


def weighted(parts: dict[str, Optional[float]], weights: dict[str, float],
             min_coverage: float = 0.0) -> dict:
    """Weighted sum with renormalisation over known parts.

    Returns raw (unrounded), score (half-up int), coverage (share of weight known),
    rows (per-part contribution) and missing (unknown parts).
    """
    total_w = sum(weights.values())
    if abs(total_w - 1.0) > 1e-6:
        raise ValueError(f"weights must sum to 1, got {total_w}")
    known = {k: v for k, v in parts.items() if k in weights and v is not None}
    missing = [k for k in weights if parts.get(k) is None]
    coverage = sum(weights[k] for k in known)
    rows = []
    for k, w in weights.items():
        s = parts.get(k)
        eff_w = w / coverage if s is not None and coverage > 0 else 0.0
        rows.append({
            "name": k,
            "score": s,
            "weight": w,
            "effective_weight": round(eff_w, 4),
            "contribution": round(s * eff_w, 4) if s is not None else None,
        })
    result = {"raw": None, "score": None, "coverage": round(coverage, 4), "rows": rows, "missing": missing}
    if coverage == 0 or coverage + 1e-9 < min_coverage:
        return result
    raw = sum(parts[k] * weights[k] for k in known) / coverage
    result["raw"] = round(raw, 4)
    result["score"] = round_half_up(raw)
    return result


def nutrition_score(subscores: dict[str, Optional[float]], weights: dict[str, float]) -> dict:
    return weighted(subscores, weights, scoring_config()["min_nutrition_coverage"])


def overall_score(dimensions: dict[str, Optional[float]],
                  weights: Optional[dict[str, float]] = None) -> dict:
    """Combine dimension scores (each 0-100) into the overall score and grade.

    Dimension scores are rounded half-up first, as in the worked example.
    """
    weights = weights or scoring_config()["dimension_weights"]
    rounded = {k: (round_half_up(v) if v is not None else None) for k, v in dimensions.items()}
    result = weighted(rounded, weights)
    if rounded.get("nutrition") is None:
        # Nutrition carries the largest weight; without it an overall grade would mislead.
        result["raw"] = result["score"] = None
    result["grade"] = grade(result["score"]) if result["score"] is not None else None
    return result
