"""Run every evaluation that the available labelled data allows, and say plainly what could not run.

    python -m evaluation.run            # prints JSON and writes reports/evaluation_results.json

Every result carries its sample size and data source. Targets from the build spec (100-200 verified
products) are listed as targets, never as results.
"""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz

from core.config import ROOT, scoring_config
from core.schema import Evidence, EvidenceLabel
from database.ingest import category_for, read_jsonl, to_extraction
from evaluation.metrics import binary_rates, field_scores, label_prf, spearman
from analyse.claims import INCONSISTENT, check_claim, extract_claims
from analyse.ingredients import analyse_ingredients
from normalise.build import build_product
from normalise.ingredients import normalise_ingredient, normalise_ingredients
from pipeline import analyse_product, extract_all
from score.scorer import overall_score

EVAL = ROOT / "data" / "verified" / "eval"
FIX = ROOT / "tests" / "fixtures"
SAMPLE = ROOT / "data" / "sample" / "synthetic_products.jsonl"
OFF_RAW = ROOT / "data" / "raw" / "off_india.jsonl"
FIELDS = ["name", "brand", "pack_size", "pack_unit", "price_inr", "energy", "protein", "carbohydrate",
          "total_sugars", "added_sugars", "total_fat", "saturated_fat", "trans_fat", "fibre", "sodium"]


def _pred_fields(p) -> dict:
    out = {}
    for f in FIELDS:
        ev = p.nutrition.get(f) if f in p.nutrition else getattr(p, f)
        out[f] = ev.value if ev is not None and ev.known else None
    return out


def evaluate_extraction() -> dict:
    gold = json.loads((EVAL / "extraction_gold.json").read_text())
    pairs, per_page, per_field = [], {}, {f: [] for f in FIELDS}
    for page, g in gold.items():
        if page.startswith("_"):
            continue
        html = (FIX / page).read_text(encoding="utf-8")
        p = build_product(extract_all(html, f"https://eval.example/{page}"), f"https://eval.example/{page}")
        pred = _pred_fields(p)
        page_pairs = [(g[f], pred[f]) for f in FIELDS]
        pairs += page_pairs
        per_page[page] = field_scores(page_pairs)
        for f in FIELDS:
            per_field[f].append((g[f], pred[f]))
    return {"data": "4 synthetic test pages (tests/fixtures), hand-labelled; deterministic extractors only (no LLM key)",
            "n_pages": len(per_page), "overall": field_scores(pairs), "per_page": per_page,
            "per_field": {f: field_scores(v) for f, v in per_field.items()}}


def _top_class(text: str) -> str:
    item = normalise_ingredient(text, 1)
    if item["status"] == "uncertain":
        return "uncertain"
    groups = item["classes"]
    return groups[0] if groups else "uncertain"


def evaluate_ingredients() -> dict:
    rows = list(csv.DictReader(open(EVAL / "ingredient_gold.csv", encoding="utf-8")))
    gold = [r["expected_class"] for r in rows]
    pred = [_top_class(r["text"]) for r in rows]
    errors = [{"text": r["text"], "expected": g, "predicted": p} for r, g, p in zip(rows, gold, pred) if g != p]
    uncertain_gold = [g == "uncertain" for g in gold]
    uncertain_pred = [p == "uncertain" for p in pred]
    return {"data": "team-labelled ingredient phrases (data/verified/eval/ingredient_gold.csv)",
            "n_items": len(rows), "classification": label_prf(gold, pred, "uncertain"),
            "uncertainty_flag": binary_rates(uncertain_gold, uncertain_pred), "errors": errors}


def _claim_product(row: dict):
    p = build_product([], url=None)
    p.nutrition_basis = "per_100ml" if row["liquid"] == "1" else "per_100g"
    for k in ("energy", "protein", "total_sugars", "total_fat", "saturated_fat", "trans_fat", "fibre", "sodium"):
        if row[k] != "":
            p.nutrition[k] = Evidence(value=float(row[k]), label=EvidenceLabel.DECLARED, source="eval")
    groups, count = None, None
    if row["ingredients"]:
        p.ingredients_raw = Evidence(value=row["ingredients"], label=EvidenceLabel.DECLARED, source="eval")
        norm = normalise_ingredients(row["ingredients"])
        groups, count = analyse_ingredients(norm)["groups"], len(norm["items"])
    return p, groups, count


def evaluate_claims() -> dict:
    rows = list(csv.DictReader(open(EVAL / "claim_gold.csv", encoding="utf-8")))
    gold, pred, wrong = [], [], []
    for r in rows:
        p, groups, count = _claim_product(r)
        found = extract_claims([r["claim_text"]])
        status = check_claim(found[0]["claim_id"], p, groups, ingredient_count=count)["status"] if found else "not detected"
        gold.append(r["expected_status"])
        pred.append(status)
        if status != r["expected_status"]:
            wrong.append({"case": r["case"], "claim": r["claim_text"], "expected": r["expected_status"],
                          "predicted": status})
    flag_gold = [g == INCONSISTENT for g in gold]
    flag_pred = [p == INCONSISTENT for p in pred]
    return {"data": "hand-worked cases from FSSAI Schedule I, reg. 6 and Schedule V (data/verified/eval/claim_gold.csv)",
            "n_cases": len(rows), "status_accuracy": sum(g == p for g, p in zip(gold, pred)) / len(rows),
            "inconsistency_detection": binary_rates(flag_gold, flag_pred), "disagreements": wrong}


def _sample_products() -> list:
    out = []
    for rec in read_jsonl(SAMPLE):
        p = build_product([to_extraction(rec)], url=None)
        p.category = Evidence(value=category_for(rec["categories_tags"]), label=EvidenceLabel.INTERPRETED)
        p.product_id = rec["code"]
        out.append(p)
    return out


def _match(name: str, brand: Optional[str], pool: list) -> Optional[str]:
    target = f"{brand or ''} {name}".strip().lower()
    best, best_score = None, 0.0
    for p in pool:
        s = fuzz.token_set_ratio(target, f"{p.brand.value or ''} {p.name.value or ''}".strip().lower())
        if s >= 85 and s > best_score:
            best, best_score = p.product_id, s
    return best


def evaluate_matching(seed: int = 7) -> dict:
    """Correct-match rate of the stored-record matcher on perturbed names (synthetic sample)."""
    rng = random.Random(seed)
    pool = _sample_products()
    cases = []
    for p in pool:
        name, brand = p.name.value, p.brand.value
        cases.append(("case and order", name.upper(), brand.lower(), p.product_id))
        i = rng.randrange(1, len(name) - 2)
        typo = name[:i] + name[i + 1] + name[i] + name[i + 2:]
        cases.append(("typo", typo, brand, p.product_id))
    for k in range(10):
        cases.append(("absent product", f"Unlisted Product {k}", "Nobody Foods", None))
    by_kind: dict = {}
    for kind, name, brand, expected in cases:
        same_cat = [q for q in pool if expected is None or q.category.value ==
                    next(x for x in pool if x.product_id == expected).category.value]
        got = _match(name, brand, same_cat)
        by_kind.setdefault(kind, []).append(got == expected)
    total = [x for v in by_kind.values() for x in v]
    return {"data": "40 synthetic sample records with generated name perturbations; near-identical names "
                    "('Sample Cereal A' vs 'B') make this a hard case",
            "n_queries": len(total), "correct_match_rate": sum(total) / len(total),
            "by_perturbation": {k: {"n": len(v), "correct_rate": sum(v) / len(v)} for k, v in by_kind.items()}}


def evaluate_nutriscore() -> dict:
    if not OFF_RAW.exists():
        return {"status": "not run", "reason": "needs Open Food Facts records with nutriscore_grade "
                                               "(data/raw/off_india.jsonl from ./run.sh off); the OFF API was "
                                               "not reachable from the build environment"}
    grades, ours = [], []
    order = {"a": 5, "b": 4, "c": 3, "d": 2, "e": 1}
    for rec in read_jsonl(OFF_RAW):
        g = (rec.get("nutriscore_grade") or "").lower()
        cat = category_for(rec.get("categories_tags") or [])
        if g not in order or not cat:
            continue
        p = build_product([to_extraction(rec)], url=None)
        p.category = Evidence(value=cat, label=EvidenceLabel.INTERPRETED)
        n = analyse_product(p)["dimensions"]["nutrition"]["score"]
        if n is not None:
            grades.append(order[g])
            ours.append(n)
    return {"status": "run", "data": str(OFF_RAW.relative_to(ROOT)), "n_products": len(ours),
            "spearman_nutrition_vs_nutriscore": spearman(ours, grades)}


def robustness_weights(products: list) -> dict:
    """Perturb each dimension weight by +/-20 % (renormalised) and count grade changes."""
    base_w = scoring_config()["dimension_weights"]
    reports = [analyse_product(p, [x for x in (_unit(q) for q in products if q.category.value == p.category.value)
                                   if x is not None]) for p in products]
    dims = [{k: r["dimensions"][k]["score"] for k in base_w} for r in reports]
    base = [overall_score(d) for d in dims]
    out = {}
    for k in base_w:
        for factor in (0.8, 1.2):
            w = dict(base_w)
            w[k] *= factor
            total = sum(w.values())
            w = {a: b / total for a, b in w.items()}
            changed, deltas = 0, []
            for d, b in zip(dims, base):
                o = overall_score(d, w)
                if b["score"] is None or o["score"] is None:
                    continue
                deltas.append(abs(o["score"] - b["score"]))
                changed += o["grade"] != b["grade"]
            out[f"{k} x{factor}"] = {"n": len(deltas), "grade_changed": changed,
                                     "mean_abs_score_change": round(sum(deltas) / len(deltas), 2) if deltas else None}
    return {"data": "40 synthetic sample records", "perturbations": out}


def _unit(p) -> Optional[float]:
    from analyse.value import unit_price
    return unit_price(p)


def robustness_missing(products: list) -> dict:
    """Remove one nutrient at a time and record the score change and how often scoring stops."""
    nutrients = ["total_sugars", "saturated_fat", "sodium", "fibre", "protein", "total_fat"]
    out = {}
    for key in nutrients:
        deltas, lost, n = [], 0, 0
        for p in products:
            if p.nutrient(key) is None:
                continue
            before = analyse_product(p)["overall"]["score"]
            q = p.model_copy(deep=True)
            q.nutrition[key] = Evidence()
            after = analyse_product(q)["overall"]["score"]
            if before is None:
                continue
            n += 1
            if after is None:
                lost += 1
            else:
                deltas.append(abs(after - before))
        out[key] = {"n": n, "overall_not_computed": lost,
                    "mean_abs_score_change": round(sum(deltas) / len(deltas), 2) if deltas else None}
    return {"data": "40 synthetic sample records; one nutrient removed at a time", "by_nutrient": out}


def robustness_conflicts() -> dict:
    """Two sources for the same page that disagree must be flagged, and agreeing ones must not."""
    html = (FIX / "cereal_jsonld.html").read_text(encoding="utf-8")
    base = extract_all(html, "https://eval.example/c")
    cases = []
    for key, factor in (("total_sugars", 1.0), ("total_sugars", 1.01), ("total_sugars", 1.2), ("sodium", 0.5),
                        ("protein", 1.5), ("total_fat", 0.99)):
        other = dict(base[0], source="second-source", nutrition=dict(base[0]["nutrition"]))
        raw = other["nutrition"].get(key)
        if raw is None:
            continue
        num = float(str(raw).split()[0])
        other["nutrition"][key] = f"{num * factor:g} {str(raw).split()[1]}"
        p = build_product([base[0], other], "https://eval.example/c")
        expected = abs(factor - 1.0) > 0.02
        cases.append((expected, p.conflict_flag))
    return {"data": "cereal test page with a second, modified source", "n_cases": len(cases),
            "detection": binary_rates([c[0] for c in cases], [c[1] for c in cases])}


def run_all(write: bool = True) -> dict:
    products = _sample_products()
    results = {
        "methodology_version": scoring_config()["methodology_version"],
        "extraction": evaluate_extraction(),
        "ingredients": evaluate_ingredients(),
        "claims": evaluate_claims(),
        "product_matching": evaluate_matching(),
        "scoring_vs_nutriscore": evaluate_nutriscore(),
        "expert_ranking": {"status": "not run", "reason": "no expert rankings collected yet"},
        "recommendations": {"status": "not run",
                            "reason": "Precision@3 and NDCG@5 need relevance judgements for alternatives; "
                                      "none collected yet (metric code: evaluation/metrics.py)"},
        "robustness": {"weights": robustness_weights(products), "missing_fields": robustness_missing(products),
                       "conflicting_sources": robustness_conflicts()},
        "targets_not_yet_met": ["verified evaluation set of 100-200 real products (build spec target)",
                                "500-1,000 Open Food Facts India records (needs ./run.sh off with network access)"],
    }
    if write:
        out = ROOT / "reports" / "evaluation_results.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    return results


if __name__ == "__main__":
    print(json.dumps(run_all(), indent=2, default=str))
