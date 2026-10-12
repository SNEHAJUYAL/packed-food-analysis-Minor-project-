"""Claim extraction and evidence checks (doc sections 6 and 8.4).

Outcomes are evidence statuses, not accusations. Conditions come only from
data/reference/fssai_claims.csv; while a threshold is TODO the outcome is
"cannot be verified from available information", with the derived facts shown.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

from core.config import claim_rules, scoring_config
from core.schema import Product
from score.category_rules import traffic_light

CONSISTENT = "consistent with available evidence"
CONTEXT = "requires context"
INCONSISTENT = "potential inconsistency for review"
UNVERIFIABLE = "cannot be verified from available information"

NATURAL_CONFLICT_GROUPS = {"synthetic_colour", "artificial_sweetener", "flavour_enhancer", "artificial_flavour"}


def extract_claims(texts: Iterable[str]) -> list[dict]:
    """Find claim phrases in listing text (name, description, bullet points)."""
    found: dict[str, dict] = {}
    for text in texts:
        if not text:
            continue
        for rule in claim_rules():
            m = re.search(rule["patterns"], text, re.IGNORECASE)
            if m and rule["claim_id"] not in found:
                found[rule["claim_id"]] = {"claim_id": rule["claim_id"], "matched_text": m.group(0).strip()}
    return list(found.values())


def _rule(claim_id: str, overrides: Optional[dict]) -> dict:
    rule = next(r for r in claim_rules() if r["claim_id"] == claim_id)
    if overrides and claim_id in overrides:
        rule = {**rule, **overrides[claim_id]}
    return rule


def check_claim(claim_id: str, product: Product, ingredient_groups: dict | None,
                overrides: Optional[dict] = None) -> dict:
    """Check one claim. ``overrides`` lets tests or a confirmed rule set supply thresholds."""
    rule = _rule(claim_id, overrides)
    liquid = product.is_liquid
    threshold = rule["threshold_liquid"] if liquid else rule["threshold_solid"]
    cite = f"{rule['regulation']}, clause {rule['clause']}"
    out = {"claim_id": claim_id, "claim": rule["claim_label"], "status": UNVERIFIABLE,
           "facts": [], "reason": "", "rule": cite, "rule_status": rule["status"]}
    nutrient = rule["nutrient"]
    cond = rule["condition"]

    if cond in ("max", "min"):
        v = product.nutrient(nutrient)
        if v is None:
            out["reason"] = f"{nutrient} is not declared."
            return out
        out["facts"].append(f"{nutrient} = {v:g} per 100 {'ml' if liquid else 'g'} (declared)")
        if threshold is None:
            out["reason"] = "FSSAI condition not yet copied into fssai_claims.csv (TODO)."
            return out
        ok = v <= threshold if cond == "max" else v >= threshold
        out["status"] = CONSISTENT if ok else INCONSISTENT
        out["reason"] = f"Condition: {nutrient} {'<=' if cond == 'max' else '>='} {threshold:g}."
        return out

    if cond == "energy_pct_min":
        p, e = product.nutrient("protein"), product.nutrient("energy")
        if p is None or e is None or e <= 0:
            out["reason"] = "Protein or energy is not declared."
            return out
        kcal_per_g = scoring_config()["energy_per_gram"]["protein"]
        pct = p * kcal_per_g / e * 100.0
        out["facts"].append(f"protein supplies {pct:.1f}% of energy "
                            f"({p:g} g × {kcal_per_g} kcal ÷ {e:g} kcal, derived)")
        if threshold is None:
            out["reason"] = "FSSAI condition not yet copied into fssai_claims.csv (TODO)."
            return out
        out["status"] = CONSISTENT if pct >= threshold else INCONSISTENT
        out["reason"] = f"Condition: at least {threshold:g}% of energy from protein."
        return out

    if cond == "no_added_ingredient_class":
        if ingredient_groups is None:
            out["reason"] = "Ingredient list not available."
            return out
        sugars = ingredient_groups.get("added_sugar", [])
        if sugars:
            out["status"] = INCONSISTENT
            out["facts"].append("sugar-class ingredient listed: " + ", ".join(sugars))
            out["reason"] = "Claim says no added sugar, but the ingredient list names a sugar."
            return out
        out["status"] = CONSISTENT
        out["reason"] = "No sugar-class ingredient found in the list."
        ts = product.nutrient("total_sugars")
        if ts is not None and product.nutrition_basis:
            light = traffic_light("total_sugars", ts, product.category.value, product.nutrition_basis)
            out["facts"].append(f"total sugars = {ts:g} g per 100 {'ml' if liquid else 'g'}")
            if light == "red":
                out["status"] = CONTEXT
                out["reason"] = "No sugar is added, but total sugars are high against the benchmark."
        return out

    if cond == "context":
        groups = set(ingredient_groups or {})
        conflicts = sorted(groups & NATURAL_CONFLICT_GROUPS)
        if conflicts:
            out["status"] = INCONSISTENT
            out["facts"].append("listed: " + ", ".join(c.replace("_", " ") for c in conflicts))
            out["reason"] = "'Natural' claim alongside synthetic or artificial additives."
        else:
            out["status"] = CONTEXT
            out["reason"] = "'Natural' has no numeric test in this MVP; read with the ingredient list."
        return out

    out["reason"] = f"Unknown condition type '{cond}'."
    return out


def analyse_claims(product: Product, ingredient_groups: dict | None,
                   overrides: Optional[dict] = None) -> dict:
    claims = extract_claims(product.claims_raw)
    results = []
    for c in claims:
        r = check_claim(c["claim_id"], product, ingredient_groups, overrides)
        r["matched_text"] = c["matched_text"]
        results.append(r)
    if not results:
        return {"claims": [], "score": None, "explanation": ["No front-of-pack claims found."]}
    scores = scoring_config()["claim_status_scores"]
    score = sum(scores[r["status"]] for r in results) / len(results)
    expl = [f"'{r['matched_text']}': {r['status']}. {r['reason']}" for r in results]
    return {"claims": results, "score": score, "explanation": expl}
