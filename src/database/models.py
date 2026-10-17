"""Normalised PostgreSQL schema (SQLAlchemy 2.0). Migrations live in migrations/ (Alembic).

Layers: products and their sources/values are the baseline and runtime data,
regulatory_rules is the regulatory layer, analysis_results and recommendations
are versioned outputs. A missing value is stored as NULL with evidence
'unknown', never as zero (a CHECK constraint enforces it for nutrients).
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (JSON, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

JSONType = JSON().with_variant(JSONB(), "postgresql")

EVIDENCE = ("declared", "derived", "interpreted", "verified", "unknown")
CATEGORIES = ("biscuits_cookies", "breakfast_cereals", "instant_noodles", "beverages", "namkeen_chips")
CLAIM_STATUSES = ("consistent with available evidence", "requires context",
                  "potential inconsistency for review", "cannot be verified from available information")
SOURCE_TYPES = ("url", "open_food_facts", "synthetic_sample", "manual", "photo", "saved_page")


def _in(col: str, values) -> str:
    return f"{col} IN (" + ", ".join("'" + v.replace("'", "''") + "'" for v in values) + ")"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class ProductRow(Base):
    __tablename__ = "product"
    __table_args__ = (
        CheckConstraint(_in("category", CATEGORIES) + " OR category IS NULL", name="ck_product_category"),
        CheckConstraint("pack_unit IN ('g', 'ml') OR pack_unit IS NULL", name="ck_product_pack_unit"),
        CheckConstraint("pack_size > 0 OR pack_size IS NULL", name="ck_product_pack_size"),
        CheckConstraint("nutrition_basis IN ('per_100g', 'per_100ml') OR nutrition_basis IS NULL",
                        name="ck_product_basis"),
        Index("ix_product_category", "category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_product_id: Mapped[str] = mapped_column(String(200), unique=True)  # "url:<sha>", "off:<code>", "sample:<id>"
    barcode: Mapped[Optional[str]] = mapped_column(String(32))
    name: Mapped[Optional[str]] = mapped_column(Text)
    brand: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(40))
    variant: Mapped[Optional[str]] = mapped_column(Text)
    pack_size: Mapped[Optional[float]] = mapped_column(Numeric(12, 3, asdecimal=False))
    pack_unit: Mapped[Optional[str]] = mapped_column(String(4))
    nutrition_basis: Mapped[Optional[str]] = mapped_column(String(10))
    ingredients_text: Mapped[Optional[str]] = mapped_column(Text)
    # Evidence label/source/note for the scalar fields above: {"name": {"label", "source", "note"}, ...}
    field_evidence: Mapped[dict] = mapped_column(JSONType, default=dict)
    additives_ins: Mapped[list] = mapped_column(JSONType, default=list)
    allergens: Mapped[list] = mapped_column(JSONType, default=list)
    claims_text: Mapped[list] = mapped_column(JSONType, default=list)
    conflicts: Mapped[list] = mapped_column(JSONType, default=list)
    warnings: Mapped[list] = mapped_column(JSONType, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    sources: Mapped[list["ProductSource"]] = relationship(back_populates="product", cascade="all, delete-orphan",
                                                          order_by="ProductSource.collected_at")
    nutrients: Mapped[list["NutrientValue"]] = relationship(cascade="all, delete-orphan")
    ingredients: Mapped[list["ProductIngredient"]] = relationship(cascade="all, delete-orphan",
                                                                  order_by="ProductIngredient.sequence")
    claims: Mapped[list["ProductClaim"]] = relationship(cascade="all, delete-orphan")
    prices: Mapped[list["PriceObservation"]] = relationship(cascade="all, delete-orphan",
                                                            order_by="PriceObservation.observed_at")
    analyses: Mapped[list["AnalysisResult"]] = relationship(cascade="all, delete-orphan",
                                                            order_by="AnalysisResult.id")


class ProductSource(Base):
    __tablename__ = "product_source"
    __table_args__ = (CheckConstraint(_in("source_type", SOURCE_TYPES), name="ck_source_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(30))
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    site: Mapped[Optional[str]] = mapped_column(String(100), index=True)  # shop the listing came from, e.g. blinkit.com
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    source_reliability: Mapped[str] = mapped_column(String(60))
    extraction_method: Mapped[Optional[str]] = mapped_column(String(100))
    extraction_log: Mapped[list] = mapped_column(JSONType, default=list)

    product: Mapped[ProductRow] = relationship(back_populates="sources")


class NutrientValue(Base):
    __tablename__ = "nutrient_value"
    __table_args__ = (
        CheckConstraint(_in("evidence_status", EVIDENCE), name="ck_nutrient_evidence"),
        CheckConstraint("evidence_status <> 'unknown' OR normalized_value IS NULL", name="ck_nutrient_unknown_is_null"),
        CheckConstraint("normalized_value >= 0 OR normalized_value IS NULL", name="ck_nutrient_non_negative"),
        CheckConstraint("basis IN ('per_100g', 'per_100ml')", name="ck_nutrient_basis"),
    )

    product_id: Mapped[int] = mapped_column(ForeignKey("product.id", ondelete="CASCADE"), primary_key=True)
    nutrient_name: Mapped[str] = mapped_column(String(30), primary_key=True)
    original_value: Mapped[Optional[str]] = mapped_column(Text)        # as printed, e.g. "12 g"
    original_unit: Mapped[Optional[str]] = mapped_column(Text)         # basis as printed, e.g. "per 30 g serving"
    normalized_value: Mapped[Optional[float]] = mapped_column(Numeric(12, 4, asdecimal=False))
    normalized_unit: Mapped[str] = mapped_column(String(8))
    basis: Mapped[str] = mapped_column(String(10))
    evidence_status: Mapped[str] = mapped_column(String(12))
    source: Mapped[Optional[str]] = mapped_column(Text)
    note: Mapped[Optional[str]] = mapped_column(Text)


class Ingredient(Base):
    __tablename__ = "ingredient"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(Text, unique=True)
    functional_category: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    reference_source: Mapped[Optional[str]] = mapped_column(Text)


class ProductIngredient(Base):
    __tablename__ = "product_ingredient"
    __table_args__ = (
        CheckConstraint(_in("evidence_status", EVIDENCE), name="ck_product_ingredient_evidence"),
        CheckConstraint("match_status IN ('matched', 'fuzzy_match', 'uncertain')", name="ck_product_ingredient_match"),
        CheckConstraint("sequence >= 1", name="ck_product_ingredient_sequence"),
    )

    product_id: Mapped[int] = mapped_column(ForeignKey("product.id", ondelete="CASCADE"), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)   # label order is kept
    ingredient_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ingredient.id"))  # NULL when unclassified
    original_label_text: Mapped[str] = mapped_column(Text)
    declared_percent: Mapped[Optional[float]] = mapped_column(Numeric(6, 2, asdecimal=False))
    match_status: Mapped[str] = mapped_column(String(12))
    evidence_status: Mapped[str] = mapped_column(String(12))
    detail: Mapped[dict] = mapped_column(JSONType, default=dict)       # full normalised entry

    ingredient: Mapped[Optional[Ingredient]] = relationship()


class RegulatoryRule(Base):
    __tablename__ = "regulatory_rule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_key: Mapped[str] = mapped_column(String(60), unique=True)    # fssai_claims.csv claim_id
    jurisdiction: Mapped[str] = mapped_column(String(8))
    rule_name: Mapped[str] = mapped_column(Text)
    claim_type: Mapped[str] = mapped_column(String(60))
    criteria: Mapped[dict] = mapped_column(JSONType)                   # condition, thresholds, unit
    required_fields: Mapped[list] = mapped_column(JSONType, default=list)
    verification_logic: Mapped[str] = mapped_column(Text)
    regulation: Mapped[str] = mapped_column(Text)
    clause: Mapped[str] = mapped_column(Text)
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    effective_date: Mapped[Optional[date]] = mapped_column(Date)
    last_checked_at: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40))


class ProductClaim(Base):
    __tablename__ = "product_claim"
    __table_args__ = (CheckConstraint(_in("verification_status", CLAIM_STATUSES), name="ck_claim_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id", ondelete="CASCADE"), index=True)
    original_claim: Mapped[str] = mapped_column(Text)
    claim_type: Mapped[str] = mapped_column(String(60))
    applicable_rule_id: Mapped[Optional[int]] = mapped_column(ForeignKey("regulatory_rule.id"))
    verification_status: Mapped[str] = mapped_column(String(60))
    explanation: Mapped[str] = mapped_column(Text)
    facts: Mapped[list] = mapped_column(JSONType, default=list)
    missing_information: Mapped[list] = mapped_column(JSONType, default=list)


class PriceObservation(Base):
    __tablename__ = "price_observation"
    __table_args__ = (
        CheckConstraint("price_inr > 0", name="ck_price_positive"),
        CheckConstraint("pack_unit IN ('g', 'ml') OR pack_unit IS NULL", name="ck_price_pack_unit"),
        CheckConstraint(_in("evidence_status", EVIDENCE), name="ck_price_evidence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id", ondelete="CASCADE"), index=True)
    price_inr: Mapped[float] = mapped_column(Numeric(10, 2, asdecimal=False))
    pack_size: Mapped[Optional[float]] = mapped_column(Numeric(12, 3, asdecimal=False))
    pack_unit: Mapped[Optional[str]] = mapped_column(String(4))
    price_per_100g_or_ml: Mapped[Optional[float]] = mapped_column(Numeric(10, 2, asdecimal=False))
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[Optional[str]] = mapped_column(Text)
    evidence_status: Mapped[str] = mapped_column(String(12), default="declared")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AnalysisResult(Base):
    __tablename__ = "analysis_result"
    __table_args__ = (
        CheckConstraint("grade IN ('A', 'B', 'C', 'D', 'E') OR grade IS NULL", name="ck_analysis_grade"),
        CheckConstraint("status IN ('complete', 'partial', 'insufficient_data')", name="ck_analysis_status"),
        CheckConstraint("overall_score BETWEEN 0 AND 100 OR overall_score IS NULL", name="ck_analysis_overall"),
        Index("ix_analysis_product_version", "product_id", "methodology_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id", ondelete="CASCADE"))
    methodology_version: Mapped[str] = mapped_column(String(20))
    nutrition_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2, asdecimal=False))
    ingredient_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2, asdecimal=False))
    transparency_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2, asdecimal=False))
    claim_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2, asdecimal=False))
    value_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2, asdecimal=False))
    overall_score: Mapped[Optional[int]] = mapped_column(Integer)
    grade: Mapped[Optional[str]] = mapped_column(String(1))
    status: Mapped[str] = mapped_column(String(20))
    price_per_100: Mapped[Optional[float]] = mapped_column(Numeric(10, 2, asdecimal=False))
    report: Mapped[dict] = mapped_column(JSONType)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Recommendation(Base):
    __tablename__ = "recommendation"
    __table_args__ = (
        CheckConstraint("source_product_id <> alternative_product_id", name="ck_recommendation_not_self"),
        CheckConstraint("ranking >= 1", name="ck_recommendation_ranking"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_product_id: Mapped[int] = mapped_column(ForeignKey("product.id", ondelete="CASCADE"), index=True)
    alternative_product_id: Mapped[int] = mapped_column(ForeignKey("product.id", ondelete="CASCADE"))
    preference: Mapped[str] = mapped_column(String(20))
    ranking: Mapped[int] = mapped_column(Integer)
    rationale: Mapped[str] = mapped_column(Text)
    matching_attributes: Mapped[list] = mapped_column(JSONType, default=list)
    methodology_version: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
