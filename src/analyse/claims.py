"""Claim extraction and evidence checks (doc sections 6 and 8.4).

Outcomes are evidence statuses, not accusations. Conditions come only from
data/reference/fssai_claims.csv (FSSAI Advertising and Claims Regulations 2018,
Schedule I, reg. 6 and Schedule V); a missing condition gives "cannot be verified
from available information", with the derived facts shown.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

from core.config import claim_rules, scoring_config
from core.schema import Product

CONSISTENT = "consistent with available evidence"
CONTEXT = "requires context"
INCONSISTENT = "potential inconsistency for review"
UNVERIFIABLE = "cannot be verified from available information"

NATURAL_CONFLICT_GROUPS = {"synthetic_colour", "artificial_sweetener", "flavour_enhancer", "artificial_flavour"}


def extract_claims(texts: Iterable[str]) -> list[dict]:
    """Find claim phrases in listing text (name, description, bullet points).

    A match inside a longer match is dropped, so "very low sodium" is not also
    "low sodium" and "saturated fat free" is not also "fat free".
    """
    found: dict[str, dict] = {}
    for text in texts:
        if not text:
            continue
        spans = []
        for rule in claim_rules():
            m = re.search(rule["patterns"], text, re.IGNORECASE)
            if m:
                spans.append((m.start(), m.end(), rule["claim_id"], m.group(0).strip()))
        for a in spans:
            inside = any(b is not a and b[0] <= a[0] and a[1] <= b[1] and (b[1] - b[0]) > (a[1] - a[0])
                         for b in spans)
            if not inside and a[2] not in found:
                found[a[2]] = {"claim_id": a[2], "matched_text": a[3]}
    return list(found.values())


def _rule(claim_id: str, overrides: Optional[dict]) -> dict:
    rule = next(r for r in claim_rules() if r["claim_id"] == claim_id)
    if overrides and claim_id in overrides:
        rule = {**rule, **overrides[claim_id]}
    return rule


def _per(liquid: bool) -> str:
    return "100 ml" if liquid else "100 g"


def check_claim(claim_id: str, product: Product, ingredient_groups: dict | None,
                overrides: Optional[dict] = None, ingredient_count: Optional[int] = None) -> dict:
    """Check one claim against its FSSAI condition. ``overrides`` replaces rule fields (tests, rule updates)."""
    rule = _rule(claim_id, overrides)
    liquid = product.is_liquid
    threshold = rule["threshold_liquid"] if liquid else rule["threshold_solid"]
    out = {"claim_id": claim_id, "claim": rule["claim_label"], "status": UNVERIFIABLE,
           "facts": [], "reason": "", "rule": f"{rule['regulation']}, {rule['clause']}",
           "rule_status": rule["status"], "source_url": rule.get("source_url") or None,
           "jurisdiction": rule.get("jurisdiction") or None, "missing_information": []}
    nutrient, cond = rule["nutrient"], rule["condition"]

    if cond in ("max", "min", "lt"):
        v = product.nutrient(nutrient)
        if v is None:
            out["reason"] = f"{nutrient} is not declared."
            out["missing_information"].append(f"{nutrient} per 100 g/ml")
            return out
        if product.nutrition_basis is None:
            out["reason"] = "Nutrition basis is unknown."
            out["missing_information"].append("nutrition basis (per 100 g / 100 ml)")
            return out
        unit = "mg" if nutrient == "sodium" else ("kcal" if nutrient == "energy" else "g")
        out["facts"].append(f"{nutrient} = {v:g} {unit} per {_per(liquid)} (declared)")
        energy = product.nutrient("energy")
        if nutrient == "protein" and energy:
            kcal = scoring_config()["energy_per_gram"]["protein"]
            out["facts"].append(f"protein supplies {v * kcal / energy * 100:.1f}% of energy "
                                f"({v:g} g × {kcal} kcal ÷ {energy:g} kcal, derived)")
        if threshold is None:
            out["reason"] = "No condition recorded for this claim in fssai_claims.csv."
            out["missing_information"].append("regulatory condition for this claim")
            return out
        if cond == "min":
            ok = v >= threshold
            why = f"needs at least {threshold:g} {unit} per {_per(liquid)}"
            per_kcal = rule.get("threshold_per_100kcal")
            if not ok and per_kcal is not None and energy:
                v_kcal = v / energy * 100.0
                out["facts"].append(f"{v_kcal:.2f} {unit} per 100 kcal (derived)")
                ok = v_kcal >= per_kcal
                why += f" or {per_kcal:g} {unit} per 100 kcal"
        elif cond == "lt":
            ok, why = v < threshold, f"needs less than {threshold:g} {unit} per {_per(liquid)}"
        else:
            ok, why = v <= threshold, f"allows at most {threshold:g} {unit} per {_per(liquid)}"
        pct_max = rule.get("energy_pct_max")
        if ok and pct_max is not None:
            if energy:
                kcal = scoring_config()["energy_per_gram"]["fat"]
                pct = v * kcal / energy * 100.0
                out["facts"].append(f"{nutrient} supplies {pct:.1f}% of energy (derived)")
                ok = pct <= pct_max
                why += f" and at most {pct_max:g}% of energy"
            else:
                out["reason"] = "Condition also limits % of energy, but energy is not declared."
                out["missing_information"].append("energy (kcal) per 100 g/ml")
                return out
        out["status"] = CONSISTENT if ok else INCONSISTENT
        out["reason"] = f"FSSAI condition {why}."
        if not ok and rule["claim_id"] in ("high_protein", "source_of_protein"):
            out["reason"] += " A per-serving route also exists and was not checked (serving size unknown)."
            out["missing_information"].append("serving size (for the per-serving route)")
        return out

    if cond == "no_added_ingredient_class":
        if ingredient_groups is None:
            out["reason"] = "Ingredient list not available."
            out["missing_information"].append("ingredient list")
            return out
        sugars = ingredient_groups.get("added_sugar", [])
        if sugars:
            out["status"] = INCONSISTENT
            out["facts"].append("sugar-type ingredient listed: " + ", ".join(sugars))
            out["reason"] = "Reg. 6(1)(a)(i): no sugars of any type may be added, but the ingredient list names one."
            return out
        out["status"] = CONSISTENT
        out["reason"] = "No sugar-type ingredient found in the list (only 6(1)(a)(i) can be checked from a listing)."
        out["missing_information"].append("conditions 6(1)(a)(ii)-(iv), which need manufacturer information")
        ts = product.nutrient("total_sugars")
        if ts is not None and product.nutrition_basis:
            out["facts"].append(f"total sugars = {ts:g} g per {_per(liquid)}")
            if ts > 0.5:
                out["status"] = CONTEXT
                out["reason"] = ("No sugar is added, but the product contains sugars; reg. 6(1)(b) requires "
                                 "'CONTAINS NATURALLY OCCURRING SUGARS' on the label.")
        return out

    if cond in ("natural", "natural_ingredients"):
        groups = set(ingredient_groups or {})
        conflicts = sorted(groups & NATURAL_CONFLICT_GROUPS)
        if conflicts:
            out["status"] = INCONSISTENT
            out["facts"].append("listed: " + ", ".join(c.replace("_", " ") for c in conflicts))
            out["reason"] = "Schedule V: a 'natural' food has nothing added; synthetic or artificial additives are listed."
            return out
        if cond == "natural" and ingredient_count and ingredient_count > 1:
            out["status"] = INCONSISTENT
            out["facts"].append(f"{ingredient_count} ingredients listed")
            out["reason"] = ("Schedule V: composite foods may not be called 'natural'; "
                             "'made from natural ingredients' is the permitted wording.")
            return out
        if ingredient_groups is None:
            out["reason"] = "Ingredient list not available."
            out["missing_information"].append("ingredient list")
            return out
        out["status"] = CONTEXT
        out["reason"] = "No synthetic additives found; Schedule V criteria for each ingredient cannot be fully checked from a listing."
        out["missing_information"].append("processing details for each ingredient (Schedule V)")
        return out

    out["reason"] = f"Unknown condition type '{cond}'."
    return out


def analyse_claims(product: Product, ingredient_groups: dict | None,
                   overrides: Optional[dict] = None, ingredient_count: Optional[int] = None) -> dict:
    claims = extract_claims(product.claims_raw)
    results = []
    for c in claims:
        r = check_claim(c["claim_id"], product, ingredient_groups, overrides, ingredient_count)
        r["matched_text"] = c["matched_text"]
        results.append(r)
    if not results:
        return {"claims": [], "score": None, "explanation": ["No front-of-pack claims found."]}
    scores = scoring_config()["claim_status_scores"]
    score = sum(scores[r["status"]] for r in results) / len(results)
    expl = [f"'{r['matched_text']}': {r['status']}. {r['reason']}" for r in results]
    return {"claims": results, "score": score, "explanation": expl}
