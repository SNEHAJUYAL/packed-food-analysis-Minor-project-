"""Build a normalised ``Product`` from raw extractions (doc section 6, stage 3).

- Units convert to per 100 g / 100 ml; a per-serving panel with a stated serving
  size is scaled and labelled DERIVED.
- Missing values stay missing, never zero.
- When two sources disagree by more than 2 %, the product is flagged
  (conflict_flag) and the disagreement is listed, not silently resolved.
- Total sugars and added sugars are never filled from each other.
"""
from __future__ import annotations

import re
from typing import Optional

from core.config import read_csv
from core.schema import NUTRIENTS, Evidence, EvidenceLabel, Product
from normalise.ingredients import normalise_ingredients
from normalise.units import nutrient_to_unit, parse_pack_size, parse_quantity, salt_g_to_sodium_mg, to_base

CONFLICT_TOLERANCE = 0.02  # doc section 10: values within +/-2 % count as matching


def _price(text: Optional[str]) -> Optional[float]:
    if text is None:
        return None
    m = re.search(r"\d[\d,]*(?:\.\d+)?", str(text))
    return float(m.group(0).replace(",", "")) if m else None


def _basis(text: Optional[str]) -> tuple[Optional[str], Optional[float]]:
    """Return (basis, reference amount in g/ml) from a servingSize-like text."""
    if not text:
        return None, None
    q = parse_quantity(text)
    if not q:
        return None, None
    base = to_base(*q)
    if not base:
        return None, None
    amount, unit = base
    return ("per_100ml" if unit == "ml" else "per_100g"), amount


def _nutrient_value(key: str, raw: str) -> Optional[float]:
    """Parse "28 g", "400mg", "410 kcal", "1720 kJ" into the schema unit."""
    target = "g" if key == "salt" else NUTRIENTS[key]
    q = parse_quantity(raw)
    if q:
        return nutrient_to_unit(q[0], q[1], target)
    m = re.search(r"\d+(?:[.,]\d+)?", str(raw))
    if not m:
        return None
    # A bare number is read in the schema unit only for g and kcal; a bare sodium
    # figure could be mg or g, so it stays unknown.
    return float(m.group(0).replace(",", ".")) if target in ("g", "kcal") else None


def categorise(*texts: Optional[str]) -> Optional[str]:
    blob = " ".join(t for t in texts if t).lower()
    best, best_hits = None, 0
    for row in read_csv("category_keywords.csv"):
        hits = sum(1 for k in row["keywords"].split("|") if re.search(rf"\b{re.escape(k)}\b", blob))
        if hits > best_hits:
            best, best_hits = row["category"], hits
    return best


def _differs(a: float, b: float) -> bool:
    if a == b:
        return False
    return abs(a - b) > CONFLICT_TOLERANCE * max(abs(a), abs(b))


def _nutrition_from(ex: dict) -> tuple[Optional[str], dict[str, float], list[str]]:
    """Per-100 nutrient values from one extraction, with notes."""
    notes = []
    basis, amount = _basis(ex.get("nutrition_basis_text"))
    if not ex.get("nutrition"):
        return basis, {}, notes
    if basis is None:
        notes.append(f"{ex['source']}: nutrition panel found but its basis (per 100 g / per serving "
                     "size) is not stated; values not used.")
        return None, {}, notes
    values: dict[str, float] = {}
    for key, raw in ex["nutrition"].items():
        v = _nutrient_value(key, raw)
        if v is None:
            notes.append(f"{ex['source']}: could not parse {key} '{raw}'.")
            continue
        if amount and abs(amount - 100.0) > 1e-9:
            v = v * 100.0 / amount
        values[key] = v
    if "salt" in values:
        salt = values.pop("salt")
        if "sodium" not in values:
            values["sodium"] = salt_g_to_sodium_mg(salt)
            notes.append(f"{ex['source']}: sodium derived from salt ({salt:g} g ÷ 2.5).")
    return basis, values, notes


def build_product(extractions: list[dict], url: Optional[str] = None,
                  category_override: Optional[str] = None) -> Product:
    """Merge extractions in priority order (first wins) and flag disagreements."""
    p = Product(source_url=url)
    extractions = [e for e in extractions if e]

    def take(field: str, key: str, parse=lambda x: x, compare_numeric=False):
        chosen = None
        for ex in extractions:
            raw = ex.get(key)
            if raw in (None, ""):
                continue
            val = parse(raw)
            if val is None:
                continue
            if chosen is None:
                chosen = (val, ex["source"])
            elif compare_numeric and _differs(chosen[0], val):
                p.conflict_flag = True
                p.conflicts.append(f"{field}: {chosen[1]} says {chosen[0]:g}, {ex['source']} says {val:g}")
        if chosen:
            setattr(p, field, Evidence.declared(chosen[0], chosen[1]))

    take("name", "name")
    take("brand", "brand")
    take("price_inr", "price", _price, compare_numeric=True)
    take("ingredients_raw", "ingredients_text")
    for ex in extractions:
        if ex.get("currency") and ex["currency"].upper() != "INR":
            p.warnings.append(f"{ex['source']}: price currency is {ex['currency']}, not INR.")

    # Pack size (converted to g or ml is a unit change, still the declared quantity).
    sizes = [(parse_pack_size(ex["pack_size_text"]), ex["source"]) for ex in extractions if ex.get("pack_size_text")]
    sizes = [(s, src) for s, src in sizes if s]
    if sizes:
        (size, unit), src = sizes[0]
        p.pack_size = Evidence.declared(size, src)
        p.pack_unit = Evidence.declared(unit, src)
        for (s2, u2), src2 in sizes[1:]:
            if u2 != unit or _differs(size, s2):
                p.conflict_flag = True
                p.conflicts.append(f"pack_size: {src} says {size:g} {unit}, {src2} says {s2:g} {u2}")

    # Nutrition.
    chosen_basis = None
    for ex in extractions:
        basis, values, notes = _nutrition_from(ex)
        p.warnings.extend(notes)
        if not values:
            continue
        derived = abs((_basis(ex.get("nutrition_basis_text"))[1] or 100.0) - 100.0) > 1e-9
        if chosen_basis is None:
            chosen_basis = basis
        elif basis != chosen_basis:
            p.conflict_flag = True
            p.conflicts.append(f"nutrition basis: {basis} from {ex['source']} vs {chosen_basis}")
            continue
        for key, v in values.items():
            current = p.nutrition[key]
            if not current.known:
                if derived:
                    p.nutrition[key] = Evidence.derived(round(v, 3), ex["source"], "scaled from per-serving panel")
                elif key == "sodium" and "salt" in ex.get("nutrition", {}) and "sodium" not in ex["nutrition"]:
                    p.nutrition[key] = Evidence.derived(round(v, 3), ex["source"], "sodium = salt ÷ 2.5")
                else:
                    p.nutrition[key] = Evidence.declared(round(v, 3), ex["source"])
            elif _differs(current.value, v):
                p.conflict_flag = True
                p.conflicts.append(f"{key}: {current.source} says {current.value:g}, {ex['source']} says {v:g}")
    p.nutrition_basis = chosen_basis
    if chosen_basis is None and p.pack_unit.known:
        p.warnings.append("No usable nutrition panel.")

    # Ingredients.
    if p.ingredients_raw.known:
        norm = normalise_ingredients(p.ingredients_raw.value)
        p.ingredients_normalised = norm["items"]
        p.additives_ins = norm["additives_ins"]
        p.allergens = sorted(set(norm["allergens"]) | set(norm["advisory_allergens"]))

    # Claims text.
    claims: list[str] = []
    for ex in extractions:
        for c in ex.get("claims_text") or []:
            if c and c not in claims:
                claims.append(c)
    p.claims_raw = claims

    # Category: user override (declared by the user) or keyword baseline (interpreted).
    if category_override:
        p.category = Evidence.declared(category_override, "user")
    else:
        hints = [ex.get("category_hint") for ex in extractions] + [p.name.value]
        cat = categorise(*hints)
        if cat:
            p.category = Evidence(value=cat, label=EvidenceLabel.INTERPRETED, source="category_keywords.csv",
                                  note="keyword baseline from name/category text")
    return p
