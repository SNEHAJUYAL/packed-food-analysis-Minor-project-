"""Score a filled pack-checking sheet (data/verified/pack_check/pack_check_sheet.csv) against the system.

    python -m evaluation.pack_check data/verified/pack_check/pack_check_sheet.csv

Only rows with pack_found = yes are compared. Every number carries its n; rows without a checker value
are left out of that field's count rather than counted as agreement.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

from evaluation.metrics import values_match

NUTRIENTS = ["energy_kcal", "protein_g", "carbohydrate_g", "total_sugars_g", "added_sugars_g", "total_fat_g",
             "saturated_fat_g", "trans_fat_g", "fibre_g", "sodium_mg"]
# Printed panels round values; 2 % (metrics.NUMERIC_TOLERANCE) is strict for small numbers, so a second,
# label-rounding tolerance is reported alongside it: within 5 % or 0.5 units, whichever is larger.
ROUNDING_ABS = 0.5
ROUNDING_REL = 0.05


def _num(v: str) -> Optional[float]:
    v = (v or "").strip()
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _rate(k: int, n: int) -> Optional[float]:
    return None if n == 0 else round(k / n, 3)


def score(rows: list[dict]) -> dict:
    # Main rows and any reserve rows used in their place: whatever a checker marked pack_found on.
    attempted = [r for r in rows if (r.get("pack_found") or "").strip()]
    found = [r for r in attempted if r["pack_found"].strip() == "yes"]
    out: dict = {"rows": len(rows), "attempted": len(attempted),
                 "pack_found": dict(Counter(r["pack_found"].strip() for r in attempted)), "compared": len(found)}

    cat = [r["category_correct"].strip() for r in found if (r.get("category_correct") or "").strip()]
    out["category_correct"] = {"n": len(cat), "rate": _rate(cat.count("yes"), len(cat))}

    nut = {}
    for key in NUTRIENTS:
        pairs = [(_num(r.get(f"label_{key}")), _num(r.get(f"sys_{key}"))) for r in found
                 if (r.get("label_basis") or "").strip() in ("per_100g", "per_100ml")]
        printed = [(g, p) for g, p in pairs if g is not None]
        both = [(g, p) for g, p in printed if p is not None]
        strict = sum(values_match(g, p) for g, p in both)
        rounding = sum(abs(g - p) <= max(ROUNDING_ABS, ROUNDING_REL * abs(g)) for g, p in both)
        nut[key] = {"printed_on_pack": len(printed), "system_missing": len(printed) - len(both),
                    "compared": len(both), "within_2pct": _rate(strict, len(both)),
                    "within_label_rounding": _rate(rounding, len(both)),
                    "mean_abs_error": round(sum(abs(g - p) for g, p in both) / len(both), 3) if both else None,
                    "system_value_not_on_pack": sum(1 for g, p in pairs if g is None and p is not None)}
    out["nutrition"] = nut

    for col in ("ingredients_match", "claims_assessment"):
        vals = [r[col].strip() for r in found if (r.get(col) or "").strip()]
        out[col] = {"n": len(vals), "counts": dict(Counter(vals))}

    recs = {}
    relevant_top3 = []
    for i in (1, 2, 3):
        vals = [_num(r.get(f"rec_alt_{i}_quality")) for r in found if (r.get(f"sys_alt_{i}") or "").strip()]
        vals = [v for v in vals if v is not None]
        recs[f"alt_{i}"] = {"n": len(vals), "mean": round(sum(vals) / len(vals), 2) if vals else None,
                            "share_4_or_5": _rate(sum(v >= 4 for v in vals), len(vals))}
    for r in found:
        ratings = [_num(r.get(f"rec_alt_{i}_quality")) for i in (1, 2, 3) if (r.get(f"sys_alt_{i}") or "").strip()]
        ratings = [v for v in ratings if v is not None]
        if ratings:
            relevant_top3.append(sum(v >= 4 for v in ratings) / len(ratings))
    recs["precision_at_3_rating_4plus"] = {"n_products": len(relevant_top3),
                                           "value": round(sum(relevant_top3) / len(relevant_top3), 3)
                                           if relevant_top3 else None}
    out["recommendations"] = recs
    return out


def main(path: str) -> dict:
    with Path(path).open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return score(rows)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m evaluation.pack_check <filled sheet .csv>")
    print(json.dumps(main(sys.argv[1]), indent=2))
