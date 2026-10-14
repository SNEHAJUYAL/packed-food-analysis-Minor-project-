"""Read and write the normalised schema. Converts between the domain ``Product`` and table rows."""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from typing import Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from core.config import claim_rules, ingredient_classes, scoring_config
from core.schema import NUTRIENTS, Evidence, EvidenceLabel, Product
from database.models import (AnalysisResult, Ingredient, NutrientValue, PriceObservation, ProductClaim,
                             ProductIngredient, ProductRow, ProductSource, Recommendation, RegulatoryRule)
from normalise.units import price_per_100

SCALAR_FIELDS = ("name", "brand", "category", "variant", "pack_size", "pack_unit", "ingredients_raw")
RELIABILITY = {"url": "brand_or_retailer_page", "open_food_facts": "open_food_facts_crowdsourced",
               "synthetic_sample": "synthetic", "manual": "manual_entry"}


def external_id_for_url(url: str) -> str:
    return "url:" + hashlib.sha256(url.strip().encode()).hexdigest()[:32]


def _dt(text: Optional[str]) -> Optional[datetime]:
    if not text:
        return None
    try:
        d = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _iso(d: Optional[datetime]) -> Optional[str]:
    if d is None:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.isoformat(timespec="seconds")


# ---------------------------------------------------------------- regulatory layer

def seed_rules(s: Session) -> int:
    """Load data/reference/fssai_claims.csv into regulatory_rule (insert or update by rule_key)."""
    n = 0
    for r in claim_rules():
        row = s.scalar(select(RegulatoryRule).where(RegulatoryRule.rule_key == r["claim_id"]))
        if row is None:
            row = RegulatoryRule(rule_key=r["claim_id"])
            s.add(row)
        needs = ["ingredient list"] if r["condition"].startswith(("no_added", "natural")) else \
            [f"{r['nutrient']} per 100 g/ml", "nutrition basis"]
        if r.get("threshold_per_100kcal") is not None or r.get("energy_pct_max") is not None:
            needs.append("energy (kcal) per 100 g/ml")
        row.jurisdiction = r.get("jurisdiction") or "IN"
        row.rule_name = r["claim_label"]
        row.claim_type = r["claim_id"]
        row.criteria = {k: r.get(k) for k in ("nutrient", "condition", "threshold_solid", "threshold_liquid",
                                              "threshold_per_100kcal", "energy_pct_max", "unit", "patterns")}
        row.required_fields = needs
        row.verification_logic = (f"condition '{r['condition']}' evaluated by analyse/claims.py check_claim; "
                                  "a missing input gives 'cannot be verified from available information'")
        row.regulation = r["regulation"]
        row.clause = r["clause"]
        row.source_url = r.get("source_url") or None
        row.effective_date = date.fromisoformat(r["effective_date"]) if r.get("effective_date") else None
        row.last_checked_at = date.fromisoformat(r["date_checked"]) if r.get("date_checked") else None
        row.status = r["status"]
        n += 1
    s.flush()
    return n


def _ingredient_row(s: Session, canonical: str, classes: list[str], cache: dict) -> Ingredient:
    if canonical in cache:
        return cache[canonical]
    row = s.scalar(select(Ingredient).where(Ingredient.canonical_name == canonical))
    if row is None:
        table = ingredient_classes()
        info = next((table[c] for c in classes if c in table), None)
        row = Ingredient(canonical_name=canonical,
                         functional_category=info["functional_category"] if info else None,
                         description=info["explanation"] if info else None,
                         reference_source=info["reference_source"] if info else None)
        s.add(row)
        s.flush()
    cache[canonical] = row
    return row


# ---------------------------------------------------------------- products

def save_product(s: Session, p: Product, *, source_type: str, external_id: Optional[str] = None,
                 barcode: Optional[str] = None, extraction_method: Optional[str] = None,
                 extraction_log: Optional[list] = None, reliability: Optional[str] = None) -> ProductRow:
    """Insert or replace a product by external id. Prices and sources accumulate as observations."""
    external_id = external_id or (external_id_for_url(p.source_url) if p.source_url else None)
    if external_id is None:
        raise ValueError("a product needs a source URL or an external id")
    row = s.scalar(select(ProductRow).where(ProductRow.external_product_id == external_id))
    if row is None:
        row = ProductRow(external_product_id=external_id)
        s.add(row)
    else:  # values are replaced by the latest extraction; history stays in sources and prices
        row.nutrients.clear()
        row.ingredients.clear()
        row.claims.clear()
        s.flush()
    row.barcode = barcode
    row.name, row.brand, row.category, row.variant = (p.name.value, p.brand.value, p.category.value,
                                                      p.variant.value)
    row.pack_size, row.pack_unit = p.pack_size.value, p.pack_unit.value
    row.nutrition_basis = p.nutrition_basis
    row.ingredients_text = p.ingredients_raw.value
    row.field_evidence = {f: {"label": getattr(p, f).label.value, "source": getattr(p, f).source,
                              "note": getattr(p, f).note} for f in SCALAR_FIELDS + ("price_inr",)}
    row.additives_ins, row.allergens, row.claims_text = list(p.additives_ins), list(p.allergens), list(p.claims_raw)
    row.conflicts, row.warnings = list(p.conflicts), list(p.warnings)
    row.updated_at = datetime.now(timezone.utc)

    if p.nutrition_basis:
        for key, unit in NUTRIENTS.items():
            ev = p.nutrition[key]
            orig = p.nutrition_original.get(key) or (p.nutrition_original.get("salt") if key == "sodium" else None)
            row.nutrients.append(NutrientValue(
                nutrient_name=key, normalized_value=ev.value if ev.known else None, normalized_unit=unit,
                basis=p.nutrition_basis, evidence_status=ev.label.value if ev.known else "unknown",
                original_value=orig["value"] if orig else None, original_unit=orig.get("basis_text") if orig else None,
                source=ev.source, note=ev.note))
        if "salt" in p.nutrition_original:  # salt kept distinct from sodium, as printed
            o = p.nutrition_original["salt"]
            row.nutrients.append(NutrientValue(nutrient_name="salt", normalized_value=None, normalized_unit="g",
                                               basis=p.nutrition_basis, evidence_status="unknown",
                                               original_value=o["value"], original_unit=o.get("basis_text"),
                                               source=o.get("source"),
                                               note="as printed; sodium row holds the normalised value"))

    cache: dict = {}
    for item in p.ingredients_normalised:
        ing = _ingredient_row(s, item["term"] or item["name"], item["classes"], cache) \
            if item.get("status") != "uncertain" and (item.get("term") or item.get("name")) else None
        row.ingredients.append(ProductIngredient(
            sequence=item["position"], ingredient=ing, original_label_text=item["text"],
            declared_percent=item.get("percent"), match_status=item.get("status", "uncertain"),
            evidence_status=p.ingredients_raw.label.value if item.get("status") != "uncertain" else "unknown",
            detail=item))

    if p.price_inr.known:
        unit = price_per_100(p.price_inr.value, p.pack_size.value) if p.pack_size.known else None
        row.prices.append(PriceObservation(
            price_inr=p.price_inr.value, pack_size=p.pack_size.value, pack_unit=p.pack_unit.value,
            price_per_100g_or_ml=round(unit, 2) if unit else None, source_url=p.source_url,
            source=p.price_inr.source, evidence_status=p.price_inr.label.value,
            observed_at=_dt(p.collected_at) or datetime.now(timezone.utc)))

    row.sources.append(ProductSource(
        source_type=source_type, source_url=p.source_url, collected_at=_dt(p.collected_at) or datetime.now(timezone.utc),
        last_verified_at=_dt(p.last_verified_at), source_reliability=reliability or RELIABILITY[source_type],
        extraction_method=extraction_method, extraction_log=extraction_log or []))
    s.flush()
    return row


def save_claims(s: Session, row: ProductRow, claims: Iterable[dict]) -> None:
    rules = {r.rule_key: r.id for r in s.scalars(select(RegulatoryRule))}
    row.claims.clear()
    for c in claims:
        row.claims.append(ProductClaim(
            original_claim=c["matched_text"], claim_type=c["claim_id"], applicable_rule_id=rules.get(c["claim_id"]),
            verification_status=c["status"], explanation=c["reason"], facts=c.get("facts", []),
            missing_information=c.get("missing_information", [])))
    s.flush()


def get_row(s: Session, product_id: int) -> Optional[ProductRow]:
    return s.get(ProductRow, product_id, options=[selectinload(ProductRow.nutrients),
                                                  selectinload(ProductRow.ingredients),
                                                  selectinload(ProductRow.sources),
                                                  selectinload(ProductRow.prices)])


def to_product(row: ProductRow) -> Product:
    """Rebuild the domain Product (with evidence labels) from stored rows."""
    ev = row.field_evidence or {}

    def evidence(field: str, value) -> Evidence:
        meta = ev.get(field) or {}
        if value is None:
            return Evidence(note=meta.get("note"))
        return Evidence(value=value, label=EvidenceLabel(meta.get("label", "declared")), source=meta.get("source"),
                        note=meta.get("note"))

    latest_source = row.sources[-1] if row.sources else None
    price = row.prices[-1] if row.prices else None
    p = Product(
        product_id=str(row.id),
        name=evidence("name", row.name), brand=evidence("brand", row.brand),
        category=evidence("category", row.category), variant=evidence("variant", row.variant),
        pack_size=evidence("pack_size", row.pack_size), pack_unit=evidence("pack_unit", row.pack_unit),
        price_inr=(Evidence(value=price.price_inr, label=EvidenceLabel(price.evidence_status), source=price.source,
                            note=f"observed {_iso(price.observed_at)}") if price else Evidence()),
        nutrition_basis=row.nutrition_basis,
        ingredients_raw=evidence("ingredients_raw", row.ingredients_text),
        ingredients_normalised=[pi.detail for pi in row.ingredients],
        additives_ins=row.additives_ins or [], allergens=row.allergens or [], claims_raw=row.claims_text or [],
        source_url=latest_source.source_url if latest_source else None,
        collected_at=_iso(latest_source.collected_at) if latest_source else _iso(row.created_at),
        last_verified_at=_iso(latest_source.last_verified_at) if latest_source else None,
        conflict_flag=bool(row.conflicts), conflicts=row.conflicts or [], warnings=row.warnings or [],
    )
    for nv in row.nutrients:
        if nv.nutrient_name in NUTRIENTS:
            p.nutrition[nv.nutrient_name] = (
                Evidence(value=nv.normalized_value, label=EvidenceLabel(nv.evidence_status), source=nv.source,
                         note=nv.note) if nv.normalized_value is not None else Evidence(note=nv.note))
        if nv.original_value:
            p.nutrition_original[nv.nutrient_name] = {"value": nv.original_value, "basis_text": nv.original_unit,
                                                      "source": nv.source}
    return p


def source_info(row: ProductRow) -> dict:
    src = row.sources[-1] if row.sources else None
    if src is None:
        return {"source_type": "manual", "source_url": None, "extraction_method": None, "collected_at": None,
                "last_verified_at": None, "source_reliability": "unknown"}
    return {"source_type": src.source_type, "source_url": src.source_url, "extraction_method": src.extraction_method,
            "collected_at": _iso(src.collected_at), "last_verified_at": _iso(src.last_verified_at),
            "source_reliability": src.source_reliability}


def is_synthetic(row: ProductRow) -> bool:
    return any(src.source_type == "synthetic_sample" for src in row.sources)


# ---------------------------------------------------------------- analyses

def save_analysis(s: Session, row: ProductRow, report: dict) -> AnalysisResult:
    d, o = report["dimensions"], report["overall"]
    res = AnalysisResult(
        product_id=row.id, methodology_version=report["methodology_version"],
        nutrition_score=d["nutrition"]["score"], ingredient_score=d["ingredients"]["score"],
        transparency_score=d["transparency"]["score"], claim_score=d["claims"]["score"],
        value_score=d["value"]["score"], overall_score=o["score"], grade=o["grade"], status=report["status"],
        price_per_100=d["value"]["price_per_100"], report=report)
    s.add(res)
    save_claims(s, row, d["claims"]["claims"])
    s.flush()
    return res


def latest_analysis(s: Session, product_id: int, version: Optional[str] = None) -> Optional[AnalysisResult]:
    version = version or scoring_config()["methodology_version"]
    return s.scalar(select(AnalysisResult)
                    .where(AnalysisResult.product_id == product_id, AnalysisResult.methodology_version == version)
                    .order_by(AnalysisResult.id.desc()).limit(1))


def latest_analyses(s: Session, category: Optional[str] = None,
                    version: Optional[str] = None) -> list[tuple[ProductRow, AnalysisResult]]:
    """The newest analysis of every product (optionally in one category), current methodology only."""
    version = version or scoring_config()["methodology_version"]
    newest = (select(AnalysisResult.product_id, func.max(AnalysisResult.id).label("aid"))
              .where(AnalysisResult.methodology_version == version)
              .group_by(AnalysisResult.product_id).subquery())
    q = (select(ProductRow, AnalysisResult)
         .join(newest, newest.c.product_id == ProductRow.id)
         .join(AnalysisResult, AnalysisResult.id == newest.c.aid)
         .options(selectinload(ProductRow.sources)))
    if category:
        q = q.where(ProductRow.category == category)
    return list(s.execute(q.order_by(ProductRow.id)).all())


def peer_unit_prices(s: Session, category: Optional[str], basis: Optional[str], exclude_id: Optional[int]) -> list[float]:
    """Latest price per 100 g/ml of the other stored products in the same category and basis."""
    if not category:
        return []
    rows = s.scalars(select(ProductRow).where(ProductRow.category == category,
                                              ProductRow.nutrition_basis == basis)
                     .options(selectinload(ProductRow.prices))).all()
    out = []
    for r in rows:
        if r.id == exclude_id or not r.prices:
            continue
        unit = r.prices[-1].price_per_100g_or_ml
        if unit is not None:
            out.append(float(unit))
    return out


def save_recommendations(s: Session, source_id: int, preference: str, alternatives: list[dict]) -> None:
    version = scoring_config()["methodology_version"]
    for a in alternatives:
        s.add(Recommendation(source_product_id=source_id, alternative_product_id=a["product_id"],
                             preference=preference, ranking=a["rank"], rationale=a["rationale"],
                             matching_attributes=a["matching_attributes"], methodology_version=version))
    s.flush()


def count_products(s: Session) -> int:
    return s.scalar(select(func.count(ProductRow.id))) or 0
