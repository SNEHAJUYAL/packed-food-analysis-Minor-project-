"""Source-policy-gated product URL extraction using the existing extractors.

The adapter fetches only a URL host registered for network access, delegates
HTTP safety and robots handling to ``extract.fetch``, and returns unverified
candidate data with source-level evidence. It does not persist to a database.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field

from acquisition.models import (
    AcquisitionContext, AcquisitionRecord, FieldProvenance, FieldValue,
    ImageReference, PolicyDecision, PriceObservation, ProductIdentity,
    RawRecordReference, RawSourceRecord, RetailerListing, ValidationIssue,
)
from acquisition.registry import DEFAULT_SOURCE_REGISTRY, SourceRegistration, SourceRegistry
from acquisition.validation import valid_gtin, valid_http_url, validate_acquisition_record
from core.schema import Evidence, Product
from extract import fetch as safe_fetch
from extract.html_parser import extract_html
from extract.image_validation import image_url_from_metadata
from extract.jsonld import extract_jsonld, find_products, parse_product
from normalise.build import build_product
from normalise.ingredients import normalise_ingredients
from normalise.units import parse_pack_size, parse_quantity

ADAPTER_VERSION = "product-url-extraction/1.0"
_FIELD_TO_PRODUCT_ATTR = {
    "name": "name", "brand": "brand", "category_hint": "category",
    "variant": "variant", "price": "price_inr", "mrp": "mrp_inr",
    "availability": "availability", "ingredients_text": "ingredients_raw",
}
_EXTRACTED_FIELDS = (
    "name", "brand", "description", "category_hint", "variant", "pack_size_text",
    "multipack_count", "gtin", "ingredients_text", "nutrition_basis_text",
    "serving_size_text", "allergens_text", "nutrition", "claims_text", "price",
    "mrp", "currency", "availability", "image_url",
)


class URLFieldEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_path: str
    original_value: Any
    normalized_value: Any = None
    provenance: FieldProvenance
    validation_status: Literal["candidate", "requires_review", "conflict", "invalid"] = "candidate"


class URLImageCandidate(BaseModel):
    image_url: str
    source: str
    image_type: str = "product_image"
    product_association: Literal["product_entity", "page_level_unverified"]
    validation_status: Literal["url_syntax_valid_not_fetched", "requires_review", "invalid"]
    provenance: FieldProvenance


class ProductURLCandidate(BaseModel):
    schema_version: Literal["product-url-candidate/1"] = "product-url-candidate/1"
    candidate_id: str
    source_id: str
    source_attribution: str | None = None
    license: str | None = None
    status: Literal["candidate"] = "candidate"
    submitted_url: str
    final_url: str
    extracted_at: datetime
    normalized_product: Product
    acquisition_record: AcquisitionRecord
    field_evidence: list[URLFieldEvidence] = Field(default_factory=list)
    images: list[URLImageCandidate] = Field(default_factory=list)
    additional_product_candidates: list[dict[str, Any]] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)


class ProductURLResult(BaseModel):
    status: Literal["candidate", "blocked", "invalid", "failed"]
    submitted_url: str
    source_id: str | None = None
    policy: PolicyDecision | None = None
    candidate: ProductURLCandidate | None = None
    issues: list[ValidationIssue] = Field(default_factory=list)
    error_code: str | None = None
    message: str | None = None


def _parse_submitted_url(url: str) -> tuple[str, int | None]:
    """Parse syntax without DNS/network access, allowing policy to run first."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError("Enter a full HTTP(S) product URL.")
    try:
        parts = urlsplit(url.strip())
        port = parts.port
    except ValueError as exc:
        raise ValueError("The address is not a valid URL.") from exc
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("Only full HTTP(S) product URLs are supported.")
    if parts.username or parts.password or port not in {None, 80, 443}:
        raise ValueError("URLs with credentials or nonstandard ports are not accepted.")
    host = parts.hostname.rstrip(".").lower()
    return host, port


def _domain_matches(host: str, registration: SourceRegistration) -> bool:
    return any(host == domain.lower().rstrip(".")
               or host.endswith("." + domain.lower().rstrip("."))
               for domain in registration.allowed_domains)


def authorize_product_url(submitted_url: str, registry: SourceRegistry = DEFAULT_SOURCE_REGISTRY
                          ) -> tuple[SourceRegistration | None, PolicyDecision | None, str | None]:
    """Resolve source policy using syntax only; this function performs no DNS or HTTP access."""
    try:
        host, _ = _parse_submitted_url(submitted_url)
    except ValueError as exc:
        return None, None, str(exc)

    registration = next((item for item in registry.all() if _domain_matches(host, item)), None)
    if registration is None:
        decision = registry.policy_decision("unsupported_url_source", requires_network=True)
    else:
        decision = registry.policy_decision(registration.source_id, requires_network=True)
    return registration, decision, None


def _raw_field(extractions: list[dict], key: str) -> tuple[Any, str] | tuple[None, None]:
    for extraction in extractions:
        value = extraction.get(key)
        if value not in (None, "", [], {}):
            return value, extraction.get("source") or "html"
    return None, None


def _candidate_id(source_id: str, submitted_url: str, extractions: list[dict]) -> str:
    identity = {
        "source_id": source_id,
        "url": submitted_url,
        "name": _raw_field(extractions, "name")[0],
        "brand": _raw_field(extractions, "brand")[0],
        "gtin": _raw_field(extractions, "gtin")[0],
    }
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False,
                                       separators=(",", ":"), default=str).encode()).hexdigest()[:24]
    return f"urlcand_{digest}"


def _field_provenance(source_id: str, source_url: str, extraction_method: str,
                      field_path: str, original: Any, collected_at: datetime,
                      evidence_state: str = "declared") -> FieldProvenance:
    return FieldProvenance(source_id=source_id, source_url=source_url,
                           input_locator=f"{source_url}#{extraction_method}/{field_path}",
                           extraction_method=extraction_method, collected_at=collected_at,
                           raw_value=original, evidence_state=evidence_state)


def _normal_value(field_path: str, extraction: dict, product: Product) -> Any:
    if field_path.startswith("nutrition."):
        nutrient = field_path.split(".", 1)[1]
        item = product.nutrition.get(nutrient)
        return item.value if item and item.known else None
    if field_path == "pack_size_text":
        return {"quantity": product.pack_size.value, "unit": product.pack_unit.value,
                "multipack_count": product.multipack_count.value}
    if field_path == "serving_size_text":
        parsed = parse_quantity(str(extraction.get(field_path) or ""))
        return {"amount": parsed[0], "unit": parsed[1]} if parsed else None
    if field_path == "allergens_text":
        return list(product.allergens) if product.allergens else None
    if field_path == "claims_text":
        return list(extraction.get(field_path) or [])
    if field_path == "currency":
        value = extraction.get(field_path)
        return value.upper() if isinstance(value, str) else value
    attr = _FIELD_TO_PRODUCT_ATTR.get(field_path)
    if attr:
        ev = getattr(product, attr)
        return ev.value if ev.known else None
    return extraction.get(field_path)


def _evidence_and_images(source_id: str, final_url: str, extractions: list[dict],
                         product: Product, extracted_at: datetime,
                         issues: list[ValidationIssue]) -> tuple[list[URLFieldEvidence], list[URLImageCandidate]]:
    field_evidence: list[URLFieldEvidence] = []
    images: list[URLImageCandidate] = []
    seen_images: set[str] = set()
    conflicted_fields = {issue.field_path for issue in issues
                         if issue.code in {"conflicting_identity_attribute", "conflicting_product_data"}}
    for issue in issues:
        if issue.code == "conflicting_product_data" and issue.field_path == "product":
            prefix = issue.message.split(":", 1)[0].strip()
            mapped = {"price_inr": "price", "mrp_inr": "mrp", "pack_size": "pack_size_text"}.get(prefix, prefix)
            conflicted_fields.add(mapped)
    invalid_fields = {issue.field_path.removeprefix("nutrition.") for issue in issues
                      if issue.code == "invalid_nutrition_unit"}
    review_fields = {issue.field_path for issue in issues
                     if issue.code in {"variant_requires_review", "ambiguous_pack_size",
                                       "invalid_or_ambiguous_pack_size"}}
    for extraction in extractions:
        method = extraction.get("source") or "html"
        for key in _EXTRACTED_FIELDS:
            value = extraction.get(key)
            if value in (None, "", [], {}):
                continue
            if key == "nutrition" and isinstance(value, dict):
                pairs = [(f"nutrition.{name}", amount) for name, amount in value.items()]
            elif key == "claims_text" and isinstance(value, list):
                pairs = [(f"claims_text[{i}]", claim) for i, claim in enumerate(value)]
            else:
                pairs = [(key, value)]
            for field_path, original in pairs:
                normalized = original if field_path.startswith("claims_text[") else _normal_value(key, extraction, product)
                if key == "nutrition" and field_path.startswith("nutrition."):
                    normalized = _normal_value(field_path, extraction, product)
                base_path = field_path.split(".", 1)[0].split("[", 1)[0]
                validation_status: Literal["candidate", "requires_review", "conflict", "invalid"] = "candidate"
                if field_path in conflicted_fields or base_path in conflicted_fields:
                    validation_status = "conflict"
                elif field_path.startswith("nutrition.") and field_path.split(".", 1)[1] in invalid_fields:
                    validation_status = "invalid"
                elif field_path in review_fields or base_path in review_fields:
                    validation_status = "requires_review"
                field_evidence.append(URLFieldEvidence(
                    field_path=field_path, original_value=original, normalized_value=normalized,
                    provenance=_field_provenance(source_id, final_url, method, field_path,
                                                 original, extracted_at,
                                                 "interpreted" if key in {"category_hint", "pack_size_text", "nutrition"} else "declared"),
                    validation_status=validation_status,
                ))

        image_url = extraction.get("image_url")
        if image_url:
            safe_image = image_url_from_metadata(str(image_url), final_url)
            if not safe_image or safe_image != image_url or not valid_http_url(safe_image):
                issues.append(ValidationIssue(code="invalid_image_url", field_path="image_url",
                                              message="Image reference did not pass safe HTTPS URL validation.",
                                              severity="warning"))
                continue
            if safe_image in seen_images:
                continue
            seen_images.add(safe_image)
            association = "product_entity" if method == "json-ld" else "page_level_unverified"
            status = "url_syntax_valid_not_fetched" if method == "json-ld" else "requires_review"
            images.append(URLImageCandidate(
                image_url=safe_image, source=str(extraction.get("image_source") or method),
                product_association=association, validation_status=status,
                provenance=_field_provenance(source_id, final_url, method, "image_url", image_url,
                                             extracted_at),
            ))
            if association == "page_level_unverified":
                issues.append(ValidationIssue(code="image_association_requires_review", field_path="image_url",
                                              message="HTML page-level image is retained as a candidate; product association was not independently verified.",
                                              severity="warning"))
    return field_evidence, images


def _identity_conflicts(extractions: list[dict]) -> list[ValidationIssue]:
    issues = []
    for field in ("name", "brand", "category_hint", "variant", "pack_size_text", "gtin"):
        values: list[tuple[str, str]] = []
        for extraction in extractions:
            value = extraction.get(field)
            if value not in (None, "", [], {}):
                rendered = " ".join(str(value).split())
                signature = rendered.casefold()
                if signature not in {item[0] for item in values}:
                    values.append((signature, rendered))
        if len(values) > 1:
            issues.append(ValidationIssue(code="conflicting_identity_attribute", field_path=field,
                                          message=f"Sources disagree on {field}; all original values are retained for review.",
                                          severity="warning"))
    return issues


def _nutrition_issues(extractions: list[dict]) -> list[ValidationIssue]:
    issues = []
    for extraction in extractions:
        for nutrient, raw in (extraction.get("nutrition") or {}).items():
            quantity = parse_quantity(str(raw))
            allowed = {"kcal", "kj"} if nutrient == "energy" else {"g", "mg", "mcg", "ug", "µg"}
            if not quantity or quantity[1].lower() not in allowed:
                issues.append(ValidationIssue(code="invalid_nutrition_unit",
                                              field_path=f"nutrition.{nutrient}",
                                              message="Nutrition value has a missing or unsupported unit and remains in original evidence only.",
                                              severity="warning"))
    return issues


def _normalization_extractions(extractions: list[dict]) -> list[dict]:
    """Copy extracted data and exclude nutrient values with ambiguous units."""
    normalized = []
    for extraction in extractions:
        copy = dict(extraction)
        nutrients = dict(copy.get("nutrition") or {})
        for nutrient, raw in list(nutrients.items()):
            quantity = parse_quantity(str(raw))
            allowed = {"kcal", "kj"} if nutrient == "energy" else {"g", "mg", "mcg", "ug", "µg"}
            if not quantity or quantity[1].lower() not in allowed:
                nutrients.pop(nutrient, None)
        copy["nutrition"] = nutrients
        normalized.append(copy)
    return normalized


class ProductURLExtractionService:
    """Extract one user-submitted URL under a fail-closed source policy."""

    def __init__(self, registry: SourceRegistry = DEFAULT_SOURCE_REGISTRY,
                 fetch_page: Callable[..., tuple[str, str]] | None = None,
                 client: Any = None, resolver: Callable[[str], list[str]] = safe_fetch.resolve):
        self.registry = registry
        self.fetch_page = fetch_page or safe_fetch.fetch_page
        self.client = client
        self.resolver = resolver

    def acquire(self, submitted_url: str,
                context: AcquisitionContext | None = None) -> ProductURLResult:
        context = context or AcquisitionContext()
        registration, policy, invalid_message = authorize_product_url(submitted_url, self.registry)
        if invalid_message:
            issue = ValidationIssue(code="invalid_url", field_path="submitted_url",
                                    message=invalid_message, severity="error")
            return ProductURLResult(status="invalid", submitted_url=str(submitted_url),
                                    issues=[issue], error_code="invalid_url", message=invalid_message)
        source_id = registration.source_id if registration else "unsupported_url_source"
        if registration is None or not policy or not policy.allowed:
            message = ("This source is not currently supported for automated product extraction. You can upload a "
                       "saved product page or packaging screenshots instead.")
            issue = ValidationIssue(code="unsupported_source", field_path="source_id",
                                    message=message, severity="error")
            return ProductURLResult(status="blocked", submitted_url=submitted_url,
                                    source_id=source_id, policy=policy, issues=[issue],
                                    error_code="unsupported_source", message=message)

        # DNS/destination validation and all HTTP access happen only after the
        # host has passed the registry policy gate.
        try:
            final_url, html = self.fetch_page(
                submitted_url, client=self.client, resolver=self.resolver,
                allowed_hosts=registration.allowed_domains,
            )
        except safe_fetch.FetchError as exc:
            status = "blocked" if isinstance(exc, safe_fetch.FetchBlocked) or exc.code in {
                "blocked_destination", "source_redirect_blocked", "robots_disallowed"
            } else "failed"
            code, message, _ = safe_fetch.public_source_fetch_error(exc)
            issue = ValidationIssue(code=code, field_path="fetch", message=message,
                                    severity="error")
            return ProductURLResult(status=status, submitted_url=submitted_url,
                                    source_id=source_id, policy=policy, issues=[issue],
                                    error_code=code, message=message)

        return self._candidate(submitted_url, final_url, html, registration, policy, context)

    def _candidate(self, submitted_url: str, final_url: str, html: str,
                   registration: SourceRegistration, policy: PolicyDecision,
                   context: AcquisitionContext) -> ProductURLResult:
        issues: list[ValidationIssue] = []
        extractions: list[dict] = []
        jsonld_entities = []
        try:
            raw_entities = find_products(html, final_url)
            jsonld_entities = [parse_product(item, final_url) for item in raw_entities]
            for item, parsed_item in zip(raw_entities, jsonld_entities):
                if (item.get("image") or item.get("photo")) and not parsed_item.get("image_url"):
                    issues.append(ValidationIssue(code="invalid_image_url", field_path="image_url",
                                                  message="A structured image reference was present but failed safe URL parsing.",
                                                  severity="warning"))
            jsonld = extract_jsonld(html, final_url)
            if jsonld:
                extractions.append(jsonld)
        except Exception as exc:
            issues.append(ValidationIssue(code="jsonld_parse_failed", field_path="jsonld",
                                          message=f"Structured metadata extraction failed ({type(exc).__name__}); HTML fallback was attempted.",
                                          severity="warning"))
        try:
            html_extraction = extract_html(html, final_url)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            raw_html_image = (soup.find("meta", property="og:image") or
                              soup.find("meta", attrs={"name": "twitter:image"}))
            if raw_html_image and raw_html_image.get("content") and not html_extraction.get("image_url"):
                issues.append(ValidationIssue(code="invalid_image_url", field_path="image_url",
                                              message="A page image reference was present but failed safe URL parsing.",
                                              severity="warning"))
            if any(html_extraction.get(key) for key in _EXTRACTED_FIELDS):
                extractions.append(html_extraction)
        except Exception as exc:
            issues.append(ValidationIssue(code="html_parse_failed", field_path="html",
                                          message=f"HTML fallback extraction failed ({type(exc).__name__}).",
                                          severity="warning"))

        # Multiple distinct Product entities are retained as alternates and
        # never silently treated as an exact match.
        signatures = {(str(item.get("gtin") or "").casefold(),
                       str(item.get("name") or "").strip().casefold(),
                       str(item.get("brand") or "").strip().casefold())
                      for item in jsonld_entities}
        signatures.discard(("", "", ""))
        if len(signatures) > 1:
            issues.append(ValidationIssue(code="duplicate_product_candidates",
                                          field_path="jsonld.Product",
                                          message="Page contains multiple distinct Product entities; no exact identity was selected automatically.",
                                          severity="warning"))

        if not extractions:
            extractions = [{"source": "html"}]
        if not any(ex.get(key) for ex in extractions for key in
                   ("name", "ingredients_text", "nutrition", "pack_size_text")):
            message = ("The page was retrieved, but the required product information could not be extracted. "
                       "Upload packaging images or enter the product details manually.")
            issue = ValidationIssue(code="product_extraction_failed", field_path="product",
                                    message=message, severity="error")
            return ProductURLResult(status="failed", submitted_url=submitted_url,
                                    source_id=registration.source_id, policy=policy, issues=[issue],
                                    error_code="product_extraction_failed", message=message)
        issues.extend(_identity_conflicts(extractions))
        issues.extend(_nutrition_issues(extractions))
        product = build_product(_normalization_extractions(extractions), url=final_url)
        product.collected_at = context.started_at.isoformat()
        priced_extractions = [ex for ex in extractions
                              if ex.get("price") not in (None, "") or ex.get("mrp") not in (None, "")]
        currencies = {str(ex.get("currency")).upper() for ex in priced_extractions if ex.get("currency")}
        currency_confirmed = bool(priced_extractions) and all(ex.get("currency") for ex in priced_extractions) \
            and len(currencies) == 1
        if product.price_inr.known and (not currency_confirmed or currencies != {"INR"}):
            product.price_inr = Evidence.unknown(
                "A price was extracted, but INR was not explicitly established; retain original price/currency evidence.")
            issues.append(ValidationIssue(code="price_currency_unconfirmed", field_path="price",
                                          message="Price is retained in source evidence but not normalized as INR because currency is absent or conflicting.",
                                          severity="warning"))
        if product.mrp_inr.known and (not currency_confirmed or currencies != {"INR"}):
            product.mrp_inr = Evidence.unknown(
                "An MRP was extracted, but INR was not explicitly established; retain original price/currency evidence.")
        if product.conflict_flag:
            for conflict in product.conflicts:
                issues.append(ValidationIssue(code="conflicting_product_data", field_path="product",
                                              message=conflict, severity="warning"))
        if not product.name.known:
            issues.append(ValidationIssue(code="missing_product_name", field_path="name",
                                          message="No product name was extracted.", severity="warning"))
        if not product.brand.known:
            issues.append(ValidationIssue(code="missing_brand", field_path="brand",
                                          message="No brand was extracted.", severity="warning"))
        if not product.ingredients_raw.known:
            issues.append(ValidationIssue(code="missing_ingredients", field_path="ingredients_text",
                                          message="Ingredient information was not present in extracted page content.",
                                          severity="warning"))
        if product.variant.known:
            issues.append(ValidationIssue(code="variant_requires_review", field_path="variant",
                                          message="Variant/flavour is a candidate attribute and requires package-level review before exact identity use.",
                                          severity="warning"))
        if any(ex.get("pack_size_text") for ex in extractions):
            for extraction in extractions:
                pack_text = extraction.get("pack_size_text")
                if pack_text and not parse_pack_size(str(pack_text)):
                    issues.append(ValidationIssue(code="invalid_or_ambiguous_pack_size",
                                                  field_path="pack_size_text",
                                                  message="Pack-size text could not be parsed unambiguously; original text is retained.",
                                                  severity="warning"))
                elif pack_text and re.search(r"\d\s*[-–]\s*\d", str(pack_text)):
                    issues.append(ValidationIssue(code="ambiguous_pack_size", field_path="pack_size_text",
                                                  message="Pack size contains a numeric range and requires review.",
                                                  severity="warning"))

        source_url = final_url
        candidate_id = _candidate_id(registration.source_id, submitted_url, extractions)
        product.product_id = candidate_id
        field_evidence, images = _evidence_and_images(registration.source_id, final_url,
                                                       extractions, product, context.started_at, issues)
        for field in ("name", "brand", "category_hint", "variant", "pack_size_text", "gtin",
                      "description", "ingredients_text", "nutrition_basis_text", "serving_size_text",
                      "allergens_text", "nutrition", "claims_text", "price", "mrp", "currency",
                      "availability", "image_url"):
            if not any(e.field_path == field or e.field_path.startswith(field + ".") or
                       e.field_path.startswith(field + "[") for e in field_evidence):
                issues.append(ValidationIssue(code="missing_extracted_field", field_path=field,
                                              message=f"No {field} value was present; the field remains null.",
                                              severity="info"))

        def provenance_for(key: str) -> FieldProvenance | None:
            value, method = _raw_field(extractions, key)
            if method is None:
                return None
            return _field_provenance(registration.source_id, source_url, method, key,
                                     value, context.started_at)

        def identity_field(value: Any, key: str, *, state: str = "declared") -> FieldValue:
            provenance = provenance_for(key)
            if provenance and state != "declared":
                provenance.evidence_state = state
            return FieldValue(value=value, provenance=provenance if value is not None else None)

        candidate_id_provenance = _field_provenance(registration.source_id, source_url,
                                                    "candidate_identity", "candidate_id",
                                                    submitted_url, context.started_at,
                                                    evidence_state="interpreted")

        gtin_raw, _ = _raw_field(extractions, "gtin")
        if gtin_raw is not None and (not isinstance(gtin_raw, str) or not valid_gtin(gtin_raw)):
            issues.append(ValidationIssue(code="invalid_or_unverified_barcode", field_path="gtin",
                                          message="Extracted barcode is retained as supplied but did not pass GTIN format/checksum validation.",
                                          severity="warning"))
        if product.conflict_flag or any(i.code == "conflicting_identity_attribute" for i in issues):
            conflict_status = "conflict"
        else:
            conflict_status = "candidate"
        identity = ProductIdentity(
            source_product_id=FieldValue(value=candidate_id, provenance=candidate_id_provenance),
            gtin=identity_field(gtin_raw, "gtin") if isinstance(gtin_raw, str) else FieldValue(),
            name=identity_field(product.name.value, "name"),
            brand=identity_field(product.brand.value, "brand"),
            category=FieldValue(value=product.category.value,
                                provenance=(provenance_for("category_hint") or provenance_for("name"))
                                if product.category.value is not None else None),
            variant=identity_field(product.variant.value, "variant"),
            pack_quantity=identity_field(Decimal(str(product.pack_size.value)) if product.pack_size.known else None,
                                         "pack_size_text", state="interpreted"),
            pack_unit=identity_field(product.pack_unit.value, "pack_size_text", state="interpreted"),
            multipack_count=FieldValue(
                value=product.multipack_count.value,
                provenance=(provenance_for("multipack_count") or provenance_for("pack_size_text"))
                if product.multipack_count.value is not None else None),
        )
        listing = RetailerListing(
            retailer_name=FieldValue(),  # OFF is a product reference source, not a retailer listing.
            listing_url=FieldValue(value=submitted_url,
                                   provenance=_field_provenance(registration.source_id, source_url,
                                                               "user_submitted_url", "submitted_url",
                                                               submitted_url, context.started_at)),
            listing_name=identity_field(product.name.value, "name"),
            image_refs=[ImageReference(product_id=candidate_id, image_type=image.image_type,
                                       image_url=image.image_url,
                                       source_field=image.source,
                                       provenance=image.provenance)
                        for image in images],
        )

        price_raw, _ = _raw_field(extractions, "price")
        mrp_raw, _ = _raw_field(extractions, "mrp")
        currency_raw, _ = _raw_field(extractions, "currency")
        observation = None
        if (price_raw not in (None, "") or mrp_raw not in (None, "") or
                any(ex.get("availability") for ex in extractions)):
            def amount(raw: Any) -> Decimal | None:
                try:
                    parsed = Decimal(str(raw).replace(",", "").strip())
                    return parsed if parsed.is_finite() and parsed > 0 else None
                except (InvalidOperation, ValueError):
                    return None
            currency = currency_raw.upper() if isinstance(currency_raw, str) else ""
            has_offer_data = price_raw not in (None, "") or mrp_raw not in (None, "") or any(
                ex.get("availability") for ex in extractions)
            observation = PriceObservation(
                observed_at=context.started_at if has_offer_data else None,
                selling_price=FieldValue(value=amount(price_raw), unit=currency or None,
                                         provenance=provenance_for("price") if price_raw is not None else None),
                mrp=FieldValue(value=amount(mrp_raw), unit=currency or None,
                               provenance=provenance_for("mrp") if mrp_raw is not None else None),
                availability=FieldValue(value=product.availability.value,
                                        provenance=provenance_for("availability") if product.availability.known else None),
                currency=currency or None,
                currency_provenance=provenance_for("currency") if currency_raw else None,
            )
        raw_source = RawSourceRecord(
            source_id=registration.source_id, record_id=candidate_id,
            payload={"submitted_url": submitted_url, "final_url": final_url,
                     "extractions": extractions},
            record_locator=submitted_url, source_url=final_url,
            retrieved_at=context.started_at, license=registration.license,
            attribution=registration.attribution, adapter_version=ADAPTER_VERSION,
        )
        observation_provenance = (_field_provenance(registration.source_id, source_url,
                                                     "page_retrieval", "observed_at",
                                                     context.started_at, context.started_at,
                                                     evidence_state="derived")
                                  if observation is not None and observation.observed_at is not None else None)
        if observation is not None:
            observation.observed_at_provenance = observation_provenance
        record = AcquisitionRecord(
            source_id=registration.source_id, record_id=f"{candidate_id}:product",
            source_url=source_url, source_license=registration.license,
            source_attribution=registration.attribution, collected_at=context.started_at,
            adapter_version=ADAPTER_VERSION, verification_status="candidate",
            product_identity=identity, listing=listing, observation=observation,
            raw_record_ref=RawRecordReference(
                payload_sha256=raw_source.payload_sha256, record_locator=submitted_url),
        )
        issues.extend(validate_acquisition_record(record))
        for issue in issues:
            if issue.field_path in {"name", "brand", "variant", "pack_size_text", "gtin"}:
                issue.severity = "warning"

        alternates = [entity for entity in jsonld_entities
                      if (entity.get("name"), entity.get("brand"), entity.get("gtin")) !=
                      (_raw_field(extractions, "name")[0], _raw_field(extractions, "brand")[0],
                       _raw_field(extractions, "gtin")[0])]
        candidate = ProductURLCandidate(
            candidate_id=candidate_id, source_id=registration.source_id,
            source_attribution=registration.attribution, license=registration.license,
            submitted_url=submitted_url, final_url=final_url, extracted_at=context.started_at,
            normalized_product=product, acquisition_record=record,
            field_evidence=field_evidence, images=images,
            additional_product_candidates=alternates, issues=issues,
        )
        return ProductURLResult(status="candidate", submitted_url=submitted_url,
                                source_id=registration.source_id, policy=policy,
                                candidate=candidate, issues=issues)
