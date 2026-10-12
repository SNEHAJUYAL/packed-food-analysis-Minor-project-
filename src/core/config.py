"""Loads reference data (data/reference/*.csv) and scoring config (config/scoring.json).

Cells marked TODO (or left blank) load as ``None``: the rule exists but its value
has not been copied from the official source yet, so the system must report
"cannot be verified" rather than guess.
"""
from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIR = ROOT / "data" / "reference"
CONFIG_DIR = ROOT / "config"


def to_number(cell: Optional[str]) -> Optional[float]:
    if cell is None:
        return None
    cell = cell.strip()
    if not cell or cell.upper() == "TODO":
        return None
    return float(cell)


def read_csv(name: str) -> list[dict[str, str]]:
    with open(REFERENCE_DIR / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@lru_cache(maxsize=None)
def scoring_config() -> dict:
    with open(CONFIG_DIR / "scoring.json", encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=None)
def thresholds() -> list[dict]:
    rows = []
    for r in read_csv("thresholds.csv"):
        r = dict(r)
        r["green_bound"] = to_number(r["green_bound"])
        r["red_bound"] = to_number(r["red_bound"])
        rows.append(r)
    return rows


@lru_cache(maxsize=None)
def claim_rules() -> list[dict]:
    rows = []
    for r in read_csv("fssai_claims.csv"):
        r = dict(r)
        r["threshold_solid"] = to_number(r["threshold_solid"])
        r["threshold_liquid"] = to_number(r["threshold_liquid"])
        rows.append(r)
    return rows


@lru_cache(maxsize=None)
def category_weights() -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for r in read_csv("category_weights.csv"):
        out.setdefault(r["category"], {})[r["nutrient"]] = float(r["weight"])
    return out


@lru_cache(maxsize=None)
def ins_codes() -> dict[str, dict]:
    return {r["ins"].lower(): dict(r) for r in read_csv("ins_codes.csv")}


@lru_cache(maxsize=None)
def ingredient_terms() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for r in read_csv("ingredient_terms.csv"):
        out.setdefault(r["term"].strip().lower(), []).append(r["class"])
    return out


@lru_cache(maxsize=None)
def allergens() -> dict[str, list[str]]:
    return {r["allergen"]: r["keywords"].split("|") for r in read_csv("allergens.csv")}


@lru_cache(maxsize=None)
def fop_warning_rules() -> list[dict]:
    rows = []
    for r in read_csv("fop_warning.csv"):
        r = dict(r)
        r["high_threshold"] = to_number(r["high_threshold"])
        rows.append(r)
    return rows
