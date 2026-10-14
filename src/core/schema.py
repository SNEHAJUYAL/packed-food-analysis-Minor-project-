"""Product schema (master doc section 7) and evidence labels (section 6).

Every field is an ``Evidence`` value: the value itself plus where it came from.
Missing values stay ``None`` with label UNKNOWN; they are never filled with zero.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class EvidenceLabel(str, Enum):
    DECLARED = "declared"        # stated by the listing or package
    DERIVED = "derived"          # calculated from declared data
    INTERPRETED = "interpreted"  # judged against a defined benchmark
    VERIFIED = "verified"        # checked against an authoritative source
    UNKNOWN = "unknown"          # cannot be established from available evidence


class Evidence(BaseModel):
    value: Any = None
    label: EvidenceLabel = EvidenceLabel.UNKNOWN
    source: Optional[str] = None
    note: Optional[str] = None

    @property
    def known(self) -> bool:
        return self.value is not None and self.label != EvidenceLabel.UNKNOWN

    @classmethod
    def declared(cls, value: Any, source: str, note: str | None = None) -> "Evidence":
        return cls(value=value, label=EvidenceLabel.DECLARED, source=source, note=note)

    @classmethod
    def derived(cls, value: Any, source: str, note: str | None = None) -> "Evidence":
        return cls(value=value, label=EvidenceLabel.DERIVED, source=source, note=note)

    @classmethod
    def unknown(cls, note: str | None = None) -> "Evidence":
        return cls(note=note)


# Nutrients stored per 100 g (solids) or per 100 ml (liquids).
# Units: energy kcal, sodium mg, everything else g.
NUTRIENTS: dict[str, str] = {
    "energy": "kcal",
    "protein": "g",
    "carbohydrate": "g",
    "total_sugars": "g",
    "added_sugars": "g",
    "total_fat": "g",
    "saturated_fat": "g",
    "trans_fat": "g",
    "fibre": "g",
    "sodium": "mg",
}

CATEGORIES = [
    "biscuits_cookies",
    "breakfast_cereals",
    "instant_noodles",
    "beverages",
    "namkeen_chips",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _unknown() -> Evidence:
    return Evidence()


class Product(BaseModel):
    product_id: Optional[str] = None
    name: Evidence = Field(default_factory=_unknown)
    brand: Evidence = Field(default_factory=_unknown)
    category: Evidence = Field(default_factory=_unknown)
    variant: Evidence = Field(default_factory=_unknown)

    pack_size: Evidence = Field(default_factory=_unknown)   # number, in pack_unit
    pack_unit: Evidence = Field(default_factory=_unknown)   # "g" or "ml"
    price_inr: Evidence = Field(default_factory=_unknown)

    # "per_100g" or "per_100ml"; None until a basis is established.
    nutrition_basis: Optional[str] = None
    nutrition: dict[str, Evidence] = Field(
        default_factory=lambda: {k: Evidence() for k in NUTRIENTS}
    )

    # Values as printed before normalisation: {nutrient or "salt": {value, basis_text, source}}.
    nutrition_original: dict[str, dict] = Field(default_factory=dict)

    ingredients_raw: Evidence = Field(default_factory=_unknown)
    ingredients_normalised: list[dict] = Field(default_factory=list)
    additives_ins: list[str] = Field(default_factory=list)
    allergens: list[str] = Field(default_factory=list)
    claims_raw: list[str] = Field(default_factory=list)

    source_url: Optional[str] = None
    collected_at: str = Field(default_factory=_now)
    last_verified_at: Optional[str] = None
    conflict_flag: bool = False
    conflicts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("nutrition")
    @classmethod
    def _all_nutrients(cls, v: dict[str, Evidence]) -> dict[str, Evidence]:
        unknown = set(v) - set(NUTRIENTS)
        if unknown:
            raise ValueError(f"unknown nutrients: {sorted(unknown)}")
        return {k: v.get(k, Evidence()) for k in NUTRIENTS}

    def nutrient(self, key: str) -> Optional[float]:
        ev = self.nutrition.get(key)
        return ev.value if ev is not None and ev.known else None

    @property
    def is_liquid(self) -> bool:
        return self.nutrition_basis == "per_100ml" or self.pack_unit.value == "ml"
