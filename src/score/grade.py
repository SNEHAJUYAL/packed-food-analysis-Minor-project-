"""A-E grade bands (doc section 8.3) and half-up rounding used throughout scoring."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from core.config import scoring_config


def round_half_up(x: float) -> int:
    """52.5 -> 53 and 57.75 -> 58, as in the worked example (Python's round() gives 52)."""
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def grade(score: float) -> str:
    for band in scoring_config()["grade_bands"]:
        if score >= band["min"]:
            return band["grade"]
    return scoring_config()["grade_bands"][-1]["grade"]
