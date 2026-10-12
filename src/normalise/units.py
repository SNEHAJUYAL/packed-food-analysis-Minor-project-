"""Unit parsing and conversion. Deterministic arithmetic only (doc section 8.5)."""
from __future__ import annotations

import re
from typing import Optional

KJ_PER_KCAL = 4.184
SALT_TO_SODIUM = 2.5  # sodium = salt / 2.5 (doc section 7)

_MASS_TO_G = {"g": 1.0, "gm": 1.0, "gms": 1.0, "gram": 1.0, "grams": 1.0, "gr": 1.0,
              "kg": 1000.0, "kgs": 1000.0, "kilogram": 1000.0, "kilograms": 1000.0,
              "mg": 0.001, "mcg": 1e-6, "µg": 1e-6, "ug": 1e-6}
_VOLUME_TO_ML = {"ml": 1.0, "millilitre": 1.0, "milliliter": 1.0,
                 "l": 1000.0, "ltr": 1000.0, "litre": 1000.0, "liter": 1000.0,
                 "litres": 1000.0, "liters": 1000.0, "cl": 10.0}

_QTY_RE = re.compile(
    r"(?P<num>\d+(?:[.,]\d+)?)\s*(?P<unit>kcal|kj|kgs?|kilograms?|grams?|gms?|gr|g|mg|mcg|µg|ug|"
    r"ml|millilit(?:re|er)s?|lit(?:re|er)s?|ltr|cl|l)\b",
    re.IGNORECASE,
)
_MULTIPACK_RE = re.compile(r"(\d+)\s*[x×]\s*(\d+(?:\.\d+)?)\s*(g|ml|kg|l)\b", re.IGNORECASE)


def _num(s: str) -> float:
    return float(s.replace(",", "."))


def parse_quantity(text: str) -> Optional[tuple[float, str]]:
    """Return (value, unit) for the first quantity in text, unit lower-cased.

    "200 g" -> (200.0, "g"); "1.2kg" -> (1.2, "kg"); "Energy 1720 kJ" -> (1720.0, "kj").
    """
    if text is None:
        return None
    m = _QTY_RE.search(str(text))
    if not m:
        return None
    return _num(m.group("num")), m.group("unit").lower()


def to_base(value: float, unit: str) -> Optional[tuple[float, str]]:
    """Convert a mass to grams or a volume to millilitres."""
    unit = unit.lower()
    if unit in _MASS_TO_G:
        return value * _MASS_TO_G[unit], "g"
    if unit in _VOLUME_TO_ML:
        return value * _VOLUME_TO_ML[unit], "ml"
    return None


def parse_pack_size(text: str) -> Optional[tuple[float, str]]:
    """Pack size in g or ml. Handles multipacks such as "4 x 70 g" -> (280, "g")."""
    if not text:
        return None
    m = _MULTIPACK_RE.search(text)
    if m:
        base = to_base(float(m.group(2)), m.group(3))
        if base:
            return round(int(m.group(1)) * base[0], 6), base[1]
    q = parse_quantity(text)
    if not q or q[1] in ("kcal", "kj"):
        return None
    return to_base(*q)


def kj_to_kcal(kj: float) -> float:
    return kj / KJ_PER_KCAL


def salt_g_to_sodium_mg(salt_g: float) -> float:
    return salt_g / SALT_TO_SODIUM * 1000.0


def sodium_mg_to_salt_g(sodium_mg: float) -> float:
    return sodium_mg * SALT_TO_SODIUM / 1000.0


def nutrient_to_unit(value: float, unit: Optional[str], target: str) -> Optional[float]:
    """Convert a nutrient amount to the schema unit (g, mg or kcal).

    Returns None when the conversion is not defined (e.g. a mass given for energy).
    """
    unit = (unit or target).lower()
    if target == "kcal":
        if unit == "kcal" or unit == "cal":
            return value
        if unit == "kj":
            return kj_to_kcal(value)
        return None
    if unit not in _MASS_TO_G:
        return None
    grams = value * _MASS_TO_G[unit]
    if target == "g":
        return grams
    if target == "mg":
        return grams * 1000.0
    return None


def scale_to_100(value: float, reference_amount: float) -> float:
    """Scale a per-serving value to per 100 g/ml. reference_amount is the serving in g/ml."""
    if reference_amount <= 0:
        raise ValueError("reference amount must be positive")
    return value * 100.0 / reference_amount


def price_per_100(price: float, pack_size: float) -> float:
    """Price per 100 g or 100 ml."""
    if pack_size <= 0:
        raise ValueError("pack size must be positive")
    return price * 100.0 / pack_size
