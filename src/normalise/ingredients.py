"""Ingredient list parsing and normalisation (doc section 6, stage 3).

Baseline NLP from the doc's stack: dictionary lookup, then RapidFuzz fuzzy
matching for spelling variants. INS codes map to name and functional class,
e.g. "Emulsifier (INS 322)" -> lecithins -> emulsifier.
"""
from __future__ import annotations

import re
from typing import Optional

from rapidfuzz import fuzz, process

from core.config import allergens as allergen_table
from core.config import ingredient_terms, ins_codes

FUZZY_CUTOFF = 90

_PERCENT_RE = re.compile(r"\(?\s*\d+(?:\.\d+)?\s*%\s*\)?")
# INS 322, INS322(i), E322, E 150d, bare codes inside an additive bracket like (322, 471)
_INS_RE = re.compile(r"\b(?:INS|E)\s*[-.]?\s*(\d{3,4}[a-f]?)(?:\s*\((?:i{1,3}|iv|v)\))?", re.IGNORECASE)
_BARE_CODE_RE = re.compile(r"^\s*(\d{3,4}[a-f]?)(?:\s*\((?:i{1,3}|iv|v)\))?\s*$", re.IGNORECASE)
_LEAD_RE = re.compile(r"^\s*(?:ingredients?\s*[:\-]\s*)", re.IGNORECASE)


def split_top_level(text: str) -> list[str]:
    """Split on commas/semicolons that are not inside brackets."""
    parts, depth, buf = [], 0, []
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        if ch in ",;" and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip(" .\n\t") for p in parts if p.strip(" .\n\t")]


def _split_parent_children(item: str) -> tuple[str, list[str]]:
    m = re.match(r"^([^(\[]*)[(\[](.*)[)\]]\s*$", item)
    if not m:
        return item.strip(), []
    return m.group(1).strip(), split_top_level(m.group(2))


def _clean(text: str) -> str:
    text = _PERCENT_RE.sub(" ", text)
    text = re.sub(r"[^\w\s'\-]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _lookup_term(text: str) -> tuple[Optional[str], list[str], str]:
    """Return (matched term, classes, method) for a cleaned ingredient name."""
    terms = ingredient_terms()
    if not text:
        return None, [], "none"
    if text in terms:
        return text, terms[text], "exact"
    # Longest dictionary term contained as whole words ("refined palmolein oil").
    for term in sorted(terms, key=len, reverse=True):
        if re.search(rf"\b{re.escape(term)}\b", text):
            return term, terms[term], "contains"
    hit = process.extractOne(text, list(terms), scorer=fuzz.ratio, score_cutoff=FUZZY_CUTOFF)
    if hit:
        return hit[0], terms[hit[0]], f"fuzzy:{hit[1]:.0f}"
    return None, [], "none"


def extract_ins(text: str) -> list[str]:
    codes = [c.lower() for c in _INS_RE.findall(text)]
    return list(dict.fromkeys(codes))


def lookup_ins(code: str) -> Optional[dict]:
    table = ins_codes()
    code = code.lower()
    if code in table:
        return table[code]
    base = re.match(r"\d+", code)
    return table.get(base.group(0)) if base else None


def normalise_ingredient(item: str, position: int) -> dict:
    parent, children = _split_parent_children(item)
    name = _clean(parent)
    term, classes, method = _lookup_term(name)
    classes = list(classes)

    # Compound ingredients ("Masala Tastemaker (Spices, Sugar, ...)") are normalised recursively.
    sub = [normalise_ingredient(child, position) for child in children
           if not (_BARE_CODE_RE.match(child) or _INS_RE.fullmatch(child.strip()))]

    additives = []
    codes = extract_ins(item)
    for child in children:
        bare = _BARE_CODE_RE.match(child)
        if bare:
            codes.append(bare.group(1).lower())
    for s_item in sub:
        codes.extend(a["ins"] for a in s_item["additives"])
    for code in dict.fromkeys(codes):
        info = lookup_ins(code)
        additives.append({
            "ins": code,
            "name": info["name"] if info else None,
            "functional_class": info["functional_class"] if info else None,
            "group": info["group"] if info else None,
            "known": info is not None,
        })


    # "Edible vegetable oil (palmolein)" discloses the oil in brackets.
    child_classes = {c for s in sub for c in s["classes"]}
    if "oil_unspecified" in classes and child_classes & {"oil_palm", "oil_specified", "hydrogenated_fat"}:
        classes.remove("oil_unspecified")
    # "Emulsifier (INS 322)" names the additive, so it is not a generic declaration.
    if "generic_additive" in classes and additives:
        classes.remove("generic_additive")
    for c in child_classes:
        if c not in classes:
            classes.append(c)
    for a in additives:
        if a["group"] and a["group"] not in classes:
            classes.append(a["group"])

    return {
        "position": position,
        "text": item,
        "name": name,
        "term": term,
        "match": method,
        "classes": classes,
        "additives": additives,
        "sub_ingredients": sub,
    }


def detect_allergens(text: str) -> list[str]:
    low = text.lower()
    found = []
    for allergen, words in allergen_table().items():
        if any(re.search(rf"\b{re.escape(w)}\b", low) for w in words):
            found.append(allergen)
    return found


def normalise_ingredients(raw: str) -> dict:
    """Parse a raw ingredient string into normalised entries, INS codes and allergens."""
    text = _LEAD_RE.sub("", raw or "")
    # Strip trailing allergen advisories so "may contain nuts" does not count as an ingredient.
    advisory = None
    m = re.search(r"\b(?:allergen (?:information|advice|declaration)|contains|may contain)\b.*$",
                  text, re.IGNORECASE | re.DOTALL)
    if m and m.start() > 0:
        advisory = m.group(0).strip()
        text = text[: m.start()]
    items = [normalise_ingredient(it, i + 1) for i, it in enumerate(split_top_level(text))]
    ins = list(dict.fromkeys(a["ins"] for it in items for a in it["additives"]))
    return {
        "items": items,
        "additives_ins": ins,
        "allergens": detect_allergens(text),
        "allergen_advisory": advisory,
        "advisory_allergens": detect_allergens(advisory) if advisory else [],
        "unmatched": [it["text"] for it in items if it["term"] is None and not it["additives"]],
    }
