"""Compare the nutrition score N with the Open Food Facts Nutri-Score grade, with the detail a write-up needs.

    python -m evaluation.nutriscore     # prints a summary and writes reports/nutriscore_comparison.json

Reports the selection funnel (how many records were dropped and why), Spearman and Kendall rank
correlations with a bootstrap interval, per-category results, N by Nutri-Score grade, band agreement
and the largest disagreements. Nutri-Score is a reference point, not ground truth: OFF computes it from
the same crowdsourced nutrient values, so data errors are shared by both scores.
"""
from __future__ import annotations

import json
import random
import statistics
from collections import Counter
from typing import Optional

from core.config import ROOT, scoring_config
from core.schema import Evidence, EvidenceLabel
from database.ingest import category_for, read_jsonl, to_extraction
from evaluation.metrics import kendall_tau_b, spearman
from evaluation.run import OFF_RAW
from normalise.build import build_product
from pipeline import analyse_product

GRADES = ["a", "b", "c", "d", "e"]
ORDER = {"a": 5, "b": 4, "c": 3, "d": 2, "e": 1}
OUT = ROOT / "reports" / "nutriscore_comparison.json"


def _band(n: float) -> str:
    """Map N onto the A-E bands of config/scoring.json (those bands are for the overall score; used here only to compare)."""
    for b in scoring_config()["grade_bands"]:
        if n >= b["min"]:
            return b["grade"].lower()
    return "e"


def _bootstrap(x: list, y: list, stat, reps: int = 2000, seed: int = 7) -> Optional[list]:
    if len(x) < 10:
        return None
    rng = random.Random(seed)
    idx = range(len(x))
    vals = []
    for _ in range(reps):
        s = [rng.choice(idx) for _ in idx]
        v = stat([x[i] for i in s], [y[i] for i in s])
        if v is not None:
            vals.append(v)
    vals.sort()
    return [round(vals[int(0.025 * len(vals))], 3), round(vals[int(0.975 * len(vals)) - 1], 3)]


def _quartiles(v: list) -> dict:
    if len(v) < 4:
        return {"n": len(v), "median": round(statistics.median(v), 1) if v else None}
    q = statistics.quantiles(v, n=4)
    return {"n": len(v), "q1": round(q[0], 1), "median": round(q[1], 1), "q3": round(q[2], 1)}


def collect(path=OFF_RAW) -> tuple[dict, list]:
    funnel = Counter()
    rows = []
    for rec in read_jsonl(path):
        funnel["records"] += 1
        g = (rec.get("nutriscore_grade") or "").lower()
        if g not in ORDER:
            funnel["no_nutriscore_grade"] += 1
            continue
        cat = category_for(rec.get("categories_tags") or [])
        if not cat:
            funnel["outside_five_categories"] += 1
            continue
        p = build_product([to_extraction(rec)], url=None)
        p.category = Evidence(value=cat, label=EvidenceLabel.INTERPRETED)
        nut = analyse_product(p)["dimensions"]["nutrition"]
        if nut["score"] is None:
            funnel["nutrition_score_unknown"] += 1
            continue
        funnel["compared"] += 1
        rows.append({"code": rec.get("code"), "name": rec.get("product_name"), "brand": rec.get("brands"),
                     "category": cat, "nutriscore": g, "n": round(nut["score"], 1),
                     "coverage": round(nut["detail"]["coverage"], 2),
                     "missing": nut["detail"]["missing"],
                     "subscores": {k: v["subscore"] for k, v in nut["subscores"].items()}})
    return dict(funnel), rows


def compare(rows: list) -> dict:
    ours = [r["n"] for r in rows]
    ref = [ORDER[r["nutriscore"]] for r in rows]
    by_cat = {}
    for cat in sorted({r["category"] for r in rows}):
        sub = [r for r in rows if r["category"] == cat]
        x, y = [r["n"] for r in sub], [ORDER[r["nutriscore"]] for r in sub]
        by_cat[cat] = {"n": len(sub), "spearman": _r(spearman(x, y)), "spearman_95ci": _bootstrap(x, y, spearman),
                       "nutriscore_grades": dict(sorted(Counter(r["nutriscore"] for r in sub).items()))}
    bands = [_band(r["n"]) for r in rows]
    exact = sum(b == r["nutriscore"] for b, r in zip(bands, rows))
    within1 = sum(abs(GRADES.index(b) - GRADES.index(r["nutriscore"])) <= 1 for b, r in zip(bands, rows))
    crosstab = {g: {b: sum(1 for bb, r in zip(bands, rows) if r["nutriscore"] == g and bb == b) for b in GRADES}
                for g in GRADES}
    # Largest disagreements: rank gap between N and Nutri-Score, expressed in percentile points.
    n = len(rows)
    rank_n = _pct_ranks(ours)
    rank_ref = _pct_ranks(ref)
    gaps = sorted(((rank_n[i] - rank_ref[i], i) for i in range(n)), key=lambda t: -abs(t[0]))[:12]
    # Energy has no benchmark yet (data/reference/thresholds.csv), so it is never scored; "complete" means
    # every other weighted nutrient was present.
    complete = [r for r in rows if not set(r["missing"]) - {"energy"}]
    return {
        "n_products": n,
        "spearman": _r(spearman(ours, ref)), "spearman_95ci": _bootstrap(ours, ref, spearman),
        "kendall_tau_b": _r(kendall_tau_b(ours, ref)), "kendall_95ci": _bootstrap(ours, ref, kendall_tau_b, reps=500),
        "complete_products": len(complete),
        "spearman_complete_only": _r(spearman([r["n"] for r in complete], [ORDER[r["nutriscore"]] for r in complete])),
        "n_at_100": sum(1 for r in rows if r["n"] >= 100),
        "by_category": by_cat,
        "n_by_nutriscore_grade": {g: _quartiles([r["n"] for r in rows if r["nutriscore"] == g]) for g in GRADES},
        "band_agreement": {"exact": exact, "within_one_grade": within1, "n": n,
                           "exact_rate": _r(exact / n), "within_one_rate": _r(within1 / n),
                           "rows_nutriscore_cols_n_band": crosstab},
        "largest_disagreements": [
            {k: rows[i][k] for k in ("name", "brand", "category", "nutriscore", "n", "missing", "subscores")}
            | {"direction": "N higher than Nutri-Score" if gap > 0 else "N lower than Nutri-Score",
               "percentile_gap": round(gap)}
            for gap, i in gaps],
    }


def _pct_ranks(v: list) -> list:
    order = sorted(range(len(v)), key=lambda i: v[i])
    ranks = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = 100 * ((i + j) / 2) / max(len(v) - 1, 1)
        i = j + 1
    return ranks


def _r(v: Optional[float]) -> Optional[float]:
    return None if v is None else round(v, 3)


def main() -> dict:
    funnel, rows = collect()
    result = {"data": str(OFF_RAW.relative_to(ROOT)), "funnel": funnel,
              "note": "Nutri-Score grades come from Open Food Facts and are computed from the same nutrient "
                      "values; this measures agreement with a reference scheme, not accuracy.",
              **compare(rows)}
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


if __name__ == "__main__":
    r = main()
    print(json.dumps({k: r[k] for k in ("funnel", "n_products", "spearman", "spearman_95ci", "kendall_tau_b",
                                        "kendall_95ci", "band_agreement")}, indent=2))
