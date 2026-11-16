"""Deterministic validation for source records and canonical observations."""
from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from urllib.parse import urlsplit

from pydantic import BaseModel

from .models import AcquisitionRecord, FieldValue, RawSourceRecord, ValidationIssue, decimal_value


def valid_gtin(value: str) -> bool:
    """Validate GTIN-8/12/13/14 shape and check digit, not product ownership."""
    if not value.isdigit() or len(value) not in {8, 12, 13, 14}:
        return False
    body, check = value[:-1], int(value[-1])
    total = 0
    for offset, digit in enumerate(reversed(body)):
        total += int(digit) * (3 if offset % 2 == 0 else 1)
    return (10 - total % 10) % 10 == check


def valid_http_url(value: str | None) -> bool:
    if not value:
        return False
    try:
        parts = urlsplit(value.strip())
        port = parts.port
    except ValueError:
        return False
    return (parts.scheme.lower() in {"http", "https"} and bool(parts.hostname)
            and not parts.username and not parts.password and port in {None, 80, 443})


def validate_raw_source_record(record: RawSourceRecord) -> list[ValidationIssue]:
    issues = []
    if record.source_url and not valid_http_url(record.source_url):
        issues.append(ValidationIssue(code="invalid_source_url", field_path="source_url",
                                      message="Source URL must be an HTTP(S) URL without credentials or a nonstandard port.",
                                      record_id=record.record_id))
    return issues


def _field_values(value: object, path: str = "") -> Iterable[tuple[str, FieldValue]]:
    if isinstance(value, FieldValue):
        yield path, value
    elif isinstance(value, BaseModel):
        for key in value.__class__.model_fields:
            nested = getattr(value, key)
            yield from _field_values(nested, f"{path}.{key}" if path else key)
    elif isinstance(value, dict):
        for key, nested in value.items():
            if key == "provenance":
                continue
            yield from _field_values(nested, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for i, nested in enumerate(value):
            yield from _field_values(nested, f"{path}[{i}]")


def validate_acquisition_record(record: AcquisitionRecord) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if record.source_url and not valid_http_url(record.source_url):
        issues.append(ValidationIssue(code="invalid_source_url", field_path="source_url",
                                      message="Source URL must be HTTP(S), have a host, and contain no credentials or nonstandard port.",
                                      record_id=record.record_id))
    identity = record.product_identity
    gtin = identity.gtin.value
    if gtin is not None and (not isinstance(gtin, str) or not valid_gtin(gtin)):
        issues.append(ValidationIssue(code="invalid_gtin", field_path="product_identity.gtin",
                                      message="GTIN must be 8, 12, 13, or 14 digits with a valid check digit; this does not verify product ownership.",
                                      record_id=record.record_id))
    if identity.name.value is None:
        issues.append(ValidationIssue(code="missing_value", field_path="product_identity.name",
                                      message="Product name is missing; it remains null and requires review.",
                                      severity="warning", record_id=record.record_id))

    quantity = decimal_value(identity.pack_quantity.value)
    if identity.pack_quantity.value is not None and (quantity is None or quantity <= 0):
        issues.append(ValidationIssue(code="invalid_quantity", field_path="product_identity.pack_quantity",
                                      message="Pack quantity must be a positive number.", record_id=record.record_id))
    if quantity is not None and identity.pack_unit.value not in {"g", "ml"}:
        issues.append(ValidationIssue(code="invalid_quantity_unit", field_path="product_identity.pack_unit",
                                      message="Pack unit must be g or ml; mass and volume are not interchangeable.",
                                      record_id=record.record_id))
    count = decimal_value(identity.multipack_count.value)
    if identity.multipack_count.value is not None and (
            count is None or count <= 0 or count != count.to_integral_value()):
        issues.append(ValidationIssue(code="invalid_multipack_count", field_path="product_identity.multipack_count",
                                      message="Multipack count must be a positive integer.", record_id=record.record_id))

    if record.listing:
        listing_url = record.listing.listing_url.value
        if listing_url is not None and not valid_http_url(str(listing_url)):
            issues.append(ValidationIssue(code="invalid_source_url", field_path="listing.listing_url",
                                          message="Listing URL must be HTTP(S), have a host, and contain no credentials or nonstandard port.",
                                          record_id=record.record_id))
        for i, image in enumerate(record.listing.image_refs):
            if image.image_url is not None and not valid_http_url(image.image_url):
                issues.append(ValidationIssue(code="invalid_source_url", field_path=f"listing.image_refs[{i}]",
                                              message="Image reference must be an HTTP(S) URL.", record_id=record.record_id))
            if image.image_url is not None and image.provenance is None:
                issues.append(ValidationIssue(code="missing_provenance", field_path=f"listing.image_refs[{i}].image_url",
                                              message="An image URL reference must retain its source-row provenance.",
                                              record_id=record.record_id))

    if record.observation:
        obs = record.observation
        if obs.observed_at is not None and obs.observed_at_provenance is None:
            issues.append(ValidationIssue(code="missing_provenance", field_path="observation.observed_at",
                                          message="A populated observation timestamp must retain field-level provenance.",
                                          record_id=record.record_id))
        if obs.observed_date is not None and obs.observed_date_provenance is None:
            issues.append(ValidationIssue(code="missing_provenance", field_path="observation.observed_date",
                                          message="A populated observation date must retain field-level provenance.",
                                          record_id=record.record_id))
        if obs.observed_at is None and obs.observed_date is None and obs.selling_price.value is not None:
            issues.append(ValidationIssue(code="missing_observation_time", field_path="observation.observed_at",
                                          message="Price has no observation date or time; retain it as an undated candidate.",
                                          severity="warning", record_id=record.record_id))
        if obs.location.pin_code is not None and obs.location.provenance is None:
            issues.append(ValidationIssue(code="missing_provenance", field_path="observation.location.pin_code",
                                          message="A populated location must retain field-level provenance.",
                                          record_id=record.record_id))
        if obs.selling_price.value is None:
            issues.append(ValidationIssue(code="missing_value", field_path="observation.selling_price",
                                          message="Selling price is missing; it remains null and is not treated as zero.",
                                          severity="warning", record_id=record.record_id))
        for field_name in ("selling_price", "mrp"):
            field = getattr(obs, field_name)
            amount = decimal_value(field.value)
            if field.value is not None and (amount is None or amount <= 0):
                issues.append(ValidationIssue(code="invalid_price", field_path=f"observation.{field_name}",
                                              message=f"{field_name} must be a positive numeric amount.",
                                              record_id=record.record_id))
        if obs.currency is None and obs.selling_price.value is not None:
            issues.append(ValidationIssue(code="missing_currency", field_path="observation.currency",
                                          message="A selling price is present but its currency is missing; do not assume INR.",
                                          severity="warning", record_id=record.record_id))
        elif obs.currency != "INR" and obs.selling_price.value is not None:
            issues.append(ValidationIssue(code="unsupported_currency", field_path="observation.currency",
                                          message="This acquisition foundation accepts prices denominated in INR.",
                                          record_id=record.record_id))
        discount = decimal_value(obs.discount_percent.value)
        if discount is not None and not Decimal("0") <= discount <= Decimal("100"):
            issues.append(ValidationIssue(code="invalid_discount", field_path="observation.discount_percent",
                                          message="Discount percentage must be between 0 and 100.",
                                          record_id=record.record_id))

    for path, field in _field_values(record):
        if field.value is not None and field.provenance is None:
            issues.append(ValidationIssue(code="missing_provenance", field_path=path,
                                          message="A populated field must retain field-level provenance.",
                                          record_id=record.record_id))
        provenance = field.provenance
        if provenance and provenance.source_url and not valid_http_url(provenance.source_url):
            issues.append(ValidationIssue(code="invalid_source_url", field_path=f"{path}.provenance.source_url",
                                          message="Provenance URL must be HTTP(S), have a host, and contain no credentials or nonstandard port.",
                                          record_id=record.record_id))
    return issues


def observation_key(record: AcquisitionRecord) -> tuple | None:
    obs = record.observation
    if obs is None or (obs.observed_at is None and obs.observed_date is None) or obs.selling_price.value is None:
        return None
    identity = record.product_identity
    listing = record.listing
    product_key = (identity.gtin.value or identity.source_product_id.value or
                   (identity.name.value, identity.brand.value, identity.variant.value,
                    identity.pack_quantity.value, identity.pack_unit.value))
    observed_when = obs.observed_at.isoformat() if obs.observed_at else (
        obs.observed_date.isoformat() if obs.observed_date else None)
    return (record.source_id, product_key,
            listing.listing_id.value if listing else None,
            listing.listing_url.value if listing else None,
            obs.location.pin_code, observed_when,
            str(decimal_value(obs.selling_price.value)),
            str(decimal_value(identity.pack_quantity.value)), identity.pack_unit.value)


def validate_batch(records: list[AcquisitionRecord]) -> dict[str, list[ValidationIssue]]:
    """Validate records and report duplicate observation candidates without merging them."""
    result = {record.record_id: validate_acquisition_record(record) for record in records}
    seen: dict[tuple, str] = {}
    for record in records:
        key = observation_key(record)
        if key is None:
            continue
        if key in seen:
            result[record.record_id].append(ValidationIssue(
                code="duplicate_observation_candidate", field_path="observation",
                message=f"Observation matches candidate record {seen[key]}; review before persistence.",
                severity="warning", record_id=record.record_id))
        else:
            seen[key] = record.record_id
    return result
