"""Versioned, source-neutral records for product-data acquisition.

These models are intentionally independent from SQLAlchemy models. Missing
source values remain null; adapters preserve the original payload separately.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "acquisition-record/1"
RAW_SCHEMA_VERSION = "raw-source-record/1"


def _aware(value: datetime | None, field_name: str) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{field_name} must include a timezone")
    return value


class AcquisitionContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    location_pin: str | None = None
    dry_run: bool = True
    max_records: int | None = Field(default=None, gt=0)

    @field_validator("started_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        return _aware(value, "started_at")

    @field_validator("location_pin")
    @classmethod
    def normalize_pin(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not value.isdigit() or len(value) != 6:
            raise ValueError("location_pin must be a six-digit PIN code")
        return value


class FieldProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    source_url: str | None = None
    input_locator: str | None = None
    extraction_method: str = Field(min_length=1)
    collected_at: datetime
    raw_value: Any = None
    evidence_state: Literal["declared", "derived", "interpreted", "verified", "unknown"] = "unknown"

    @field_validator("collected_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        return _aware(value, "collected_at")


class FieldValue(BaseModel):
    """A possibly missing normalized value with its own source provenance."""

    value: str | int | float | Decimal | bool | None = None
    unit: str | None = None
    provenance: FieldProvenance | None = None

    @field_validator("value", mode="before")
    @classmethod
    def blank_is_missing(cls, value: Any) -> Any:
        return None if isinstance(value, str) and not value.strip() else value


class ProductIdentity(BaseModel):
    source_product_id: FieldValue = Field(default_factory=FieldValue)
    gtin: FieldValue = Field(default_factory=FieldValue)
    name: FieldValue = Field(default_factory=FieldValue)
    brand: FieldValue = Field(default_factory=FieldValue)
    category: FieldValue = Field(default_factory=FieldValue)
    variant: FieldValue = Field(default_factory=FieldValue)
    pack_quantity: FieldValue = Field(default_factory=FieldValue)
    pack_unit: FieldValue = Field(default_factory=FieldValue)
    multipack_count: FieldValue = Field(default_factory=FieldValue)


class RetailerListing(BaseModel):
    retailer_id: FieldValue = Field(default_factory=FieldValue)
    retailer_name: FieldValue = Field(default_factory=FieldValue)
    listing_id: FieldValue = Field(default_factory=FieldValue)
    listing_url: FieldValue = Field(default_factory=FieldValue)
    listing_name: FieldValue = Field(default_factory=FieldValue)
    image_refs: list["ImageReference"] = Field(default_factory=list)


class ImageReference(BaseModel):
    product_id: str | None = None
    pvid: str | None = None
    image_type: str | None = None
    image_index: int | None = None
    source_platform: str | None = None
    image_url: str | None = None
    mime_type: str | None = None
    status: str | None = None
    source_field: str | None = None
    provenance: FieldProvenance | None = None


class ObservationLocation(BaseModel):
    country: str | None = "IN"
    pin_code: str | None = None
    provenance: FieldProvenance | None = None

    @field_validator("pin_code")
    @classmethod
    def normalize_pin(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        if not value.isdigit() or len(value) != 6:
            raise ValueError("pin_code must be a six-digit PIN code")
        return value


class PriceObservation(BaseModel):
    observed_at: datetime | None = None
    observed_at_provenance: FieldProvenance | None = None
    observed_date: date | None = None
    observed_date_provenance: FieldProvenance | None = None
    selling_price: FieldValue = Field(default_factory=FieldValue)
    currency: str | None = "INR"
    currency_provenance: FieldProvenance | None = None
    mrp: FieldValue = Field(default_factory=FieldValue)
    discount_percent: FieldValue = Field(default_factory=FieldValue)
    availability: FieldValue = Field(default_factory=FieldValue)
    location: ObservationLocation = Field(default_factory=ObservationLocation)

    @field_validator("observed_at")
    @classmethod
    def timezone_required(cls, value: datetime | None) -> datetime | None:
        return _aware(value, "observed_at")

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None


class RawRecordReference(BaseModel):
    payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    record_locator: str | None = None


class AcquisitionRecord(BaseModel):
    schema_version: Literal["acquisition-record/1"] = SCHEMA_VERSION
    source_id: str = Field(min_length=1)
    record_id: str = Field(min_length=1)
    source_url: str | None = None
    source_license: str | None = None
    source_attribution: str | None = None
    collected_at: datetime | None = None
    adapter_version: str | None = None
    verification_status: Literal["unverified", "candidate", "partially_verified", "verified",
                                 "unavailable", "requires_manual_review"] = "candidate"
    product_identity: ProductIdentity = Field(default_factory=ProductIdentity)
    listing: RetailerListing | None = None
    observation: PriceObservation | None = None
    raw_record_ref: RawRecordReference

    @field_validator("collected_at")
    @classmethod
    def timezone_required(cls, value: datetime | None) -> datetime | None:
        return _aware(value, "collected_at")


class RawSourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["raw-source-record/1"] = RAW_SCHEMA_VERSION
    source_id: str = Field(min_length=1)
    record_id: str = Field(min_length=1)
    payload: dict[str, Any]
    payload_sha256: str | None = None
    record_locator: str | None = None
    source_url: str | None = None
    retrieved_at: datetime
    license: str | None = None
    attribution: str | None = None
    adapter_version: str = Field(min_length=1)

    @field_validator("retrieved_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        return _aware(value, "retrieved_at")

    @field_validator("payload_sha256")
    @classmethod
    def valid_hash(cls, value: str | None) -> str | None:
        if value is not None and not __import__("re").fullmatch(r"[a-f0-9]{64}", value):
            raise ValueError("payload_sha256 must be a lowercase SHA-256 hex digest")
        return value

    @model_validator(mode="after")
    def hash_payload(self) -> "RawSourceRecord":
        canonical = json.dumps(self.payload, ensure_ascii=False, sort_keys=True,
                                separators=(",", ":"), default=str)
        calculated = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if self.payload_sha256 is None:
            self.payload_sha256 = calculated
        elif self.payload_sha256 != calculated:
            raise ValueError("payload_sha256 does not match canonical payload")
        return self


class SourceCapabilities(BaseModel):
    product_identity: bool = False
    retailer_listing: bool = False
    price_observation: bool = False
    images: bool = False
    location_scoped: bool = False


class PolicyDecision(BaseModel):
    source_id: str
    allowed: bool
    reason: str
    requires_network: bool
    authorization_evidence: str | None = None


class ValidationIssue(BaseModel):
    code: str
    field_path: str
    message: str
    severity: Literal["info", "warning", "error"] = "error"
    record_id: str | None = None


def decimal_value(value: Any) -> Decimal | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        number = Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None
