"""Read-only importer for Complete_Product_Catalog_With_JSON_Photos.xlsx.

Outputs stay in an isolated annotation candidate-source directory. This module
does not fetch image URLs, access retailer networks, or write to a database.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pydantic import ValidationError

try:
    from openpyxl import load_workbook
except ImportError as exc:  # optional workbook adapter; do not install dependencies implicitly
    raise RuntimeError("openpyxl is required for XLSX candidate import; no dependency was installed") from exc

from scripts.consolidate_product_datasets import (
    category_candidate,
    field as annotation_field,
    make_annotation,
    source_record,
    stable_id,
)
from scripts.validate_annotation_dataset import validate_file

from .models import (
    AcquisitionContext,
    AcquisitionRecord,
    FieldProvenance,
    FieldValue,
    ImageReference,
    PriceObservation,
    ProductIdentity,
    RawRecordReference,
    RawSourceRecord,
    RetailerListing,
    SourceCapabilities,
    decimal_value,
)
from .registry import DEFAULT_SOURCE_REGISTRY, SourceRegistry
from .validation import valid_gtin, valid_http_url, validate_acquisition_record, validate_raw_source_record

IMPORTER_VERSION = "complete-product-catalog/1.2"
SOURCE_ID = "complete_product_catalog"
PRODUCT_SHEET = "Sheet1"
IMAGE_COLUMNS = (
    ("Paste or insert a link to the original photo file. Google Form file uploads are stored in Drive. Front packaging photo",
     "front_packaging_photo", 1),
    ("Back packaging photo", "back_packaging_photo", 2),
    ("Ingredient-label photo", "ingredient_label_photo", 3),
    ("Nutrition-table photo", "nutrition_table_photo", 4),
    ("Barcode photo", "barcode_photo", 5),
)
PRICE_COLUMNS = (
    ("Blinkit price (₹)", "Blinkit"),
    ("Zepto price (₹)", "Zepto"),
    ("Swiggy Instamart price (₹)", "Swiggy Instamart"),
)
NUTRIENT_PATTERNS = {
    "energy": r"\bEnergy\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(kcal|kj)\b",
    "protein": r"\bProtein\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)\b",
    "carbohydrate": r"\bCarbohydrate\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)\b",
    "total_sugars": r"\bTotal\s+Sugars?\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)\b",
    "added_sugars": r"\bAdded\s+Sugars?\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)\b",
    "total_fat": r"\bTotal\s+Fat\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)\b",
    "saturated_fat": r"\bSaturated\s+Fat\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)\b",
    "trans_fat": r"\bTrans\s+Fat\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)\b",
    "fibre": r"\b(?:Dietary\s+)?Fib(?:re|er)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)\b",
    "sodium": r"\bSodium\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(g|mg)\b",
}


def json_value(value: Any) -> Any:
    # Excel date cells are materialized as midnight datetimes by openpyxl even
    # when the cell represents a date only. Do not serialize that placeholder
    # midnight as a source collection time.
    if isinstance(value, datetime):
        if value.time().isoformat() == "00:00:00":
            return value.date().isoformat()
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value)
    return value if value.strip() else None


def _date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            try:
                return datetime.fromisoformat(value.strip()).date()
            except ValueError:
                return None
    return None


def _price(value: Any) -> Decimal | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        parsed = Decimal(str(value).replace("₹", "").replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _provenance(context: AcquisitionContext, sheet: str, row_number: int,
                column_name: str, raw_value: Any, source_url: str | None = None) -> FieldProvenance:
    return FieldProvenance(
        source_id=SOURCE_ID, source_url=source_url,
        input_locator=f"{sheet}!row:{row_number} / {column_name}",
        extraction_method="xlsx_cell_import", collected_at=context.started_at,
        raw_value=json_value(raw_value), evidence_state="unknown",
    )


def _field(value: Any, context: AcquisitionContext, sheet: str, row: int,
           column: str, *, unit: str | None = None, source_url: str | None = None) -> FieldValue:
    return FieldValue(value=value, unit=unit,
                      provenance=_provenance(context, sheet, row, column, value, source_url)
                      if value is not None else None)


def _headers_and_records(workbook_path: Path) -> tuple[list[str], list[tuple[int, tuple]]]:
    wb = load_workbook(workbook_path, read_only=True, data_only=False)
    if PRODUCT_SHEET not in wb.sheetnames:
        wb.close()
        raise ValueError(f"Expected product worksheet {PRODUCT_SHEET!r}; found {wb.sheetnames!r}")
    ws = wb[PRODUCT_SHEET]
    rows = list(ws.iter_rows(values_only=True))
    if not rows or not any(x is not None for x in rows[0]):
        wb.close()
        raise ValueError("Product worksheet is missing its header row")
    headers = [str(x) if x is not None else f"column_{i + 1}" for i, x in enumerate(rows[0])]
    records = [(i, row) for i, row in enumerate(rows[1:], 2) if any(x is not None for x in row)]
    wb.close()
    return headers, records


def _field_records(headers: list[str], row: tuple) -> list[dict]:
    fields = []
    for i in range(max(len(headers), len(row))):
        header = headers[i] if i < len(headers) else f"column_{i + 1}"
        raw = row[i] if i < len(row) else None
        fields.append({"column_index": i + 1, "column_name": header,
                       "original_header": header if i < len(headers) else None,
                       "original_value": json_value(raw),
                       "normalized_value": " ".join(raw.split()) if isinstance(raw, str) else json_value(raw)})
    return fields


def _value_map(headers: list[str], row: tuple) -> dict[str, Any]:
    return {header: row[i] if i < len(row) else None for i, header in enumerate(headers)}


def source_row_fingerprint(fields: list[dict]) -> str:
    """Hash ordered original headers/cell values, including explicit nulls."""
    canonical = [{"original_header": field["original_header"],
                  "original_value": field["original_value"]} for field in fields]
    return hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def source_row_identity(raw: RawSourceRecord) -> str:
    row_id = raw.payload.get("source_row_id")
    if row_id:
        return str(row_id)
    # Fallback remains deterministic for callers constructing RawSourceRecord
    # directly rather than using this adapter's fetch method.
    row_number = raw.payload.get("row_number", raw.record_locator or raw.record_id)
    fingerprint = raw.payload.get("source_row_fingerprint", raw.payload_sha256)
    return f"{SOURCE_ID}:{PRODUCT_SHEET}:row-{row_number}:{str(fingerprint)[:16]}"


def _numeric_excel_cell(value: Any) -> bool:
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)


def _retailer_from_product_url(url: str | None) -> str | None:
    """Name a retailer only when the provided product URL's host supports it."""
    if not valid_http_url(url):
        return None
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    if host == "zepto.com" or host.endswith(".zepto.com"):
        return "Zepto"
    return None


def parse_image_references(values: dict[str, Any], product_id: str, context: AcquisitionContext,
                           row_number: int) -> tuple[list[ImageReference], list[dict]]:
    refs: list[ImageReference] = []
    issues: list[dict] = []
    for source_field, expected_type, expected_index in IMAGE_COLUMNS:
        raw = values.get(source_field)
        if raw in (None, ""):
            issues.append({"severity": "warning", "record_id": product_id, "field_path": source_field,
                           "code": "missing_image_reference", "message": "Image JSON field is empty."})
            continue
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            issues.append({"severity": "error", "record_id": product_id, "field_path": source_field,
                           "code": "invalid_image_json", "message": "Image field is not valid JSON."})
            continue
        if not isinstance(parsed, dict):
            issues.append({"severity": "error", "record_id": product_id, "field_path": source_field,
                           "code": "invalid_image_json_shape", "message": "Image JSON must be an object."})
            continue
        if str(parsed.get("product_id") or "") != product_id:
            issues.append({"severity": "error", "record_id": product_id, "field_path": source_field,
                           "code": "image_product_id_mismatch", "message": "Image reference product_id does not match workbook row ID."})
        if parsed.get("image_type") != expected_type:
            issues.append({"severity": "warning", "record_id": product_id, "field_path": source_field,
                           "code": "image_type_column_mismatch", "message": "Image type differs from the source column's expected type."})
        if parsed.get("image_index") != expected_index:
            issues.append({"severity": "warning", "record_id": product_id, "field_path": source_field,
                           "code": "image_index_column_mismatch", "message": "Image index differs from the source column's expected index."})
        image_url = parsed.get("image_url")
        if not valid_http_url(image_url):
            issues.append({"severity": "error", "record_id": product_id, "field_path": source_field,
                           "code": "invalid_image_url", "message": "Image URL is not a valid HTTP(S) reference."})
        provenance = _provenance(context, PRODUCT_SHEET, row_number, source_field, raw)
        refs.append(ImageReference(
            product_id=str(parsed.get("product_id")) if parsed.get("product_id") is not None else None,
            pvid=_text(parsed.get("pvid")), image_type=_text(parsed.get("image_type")),
            image_index=parsed.get("image_index") if isinstance(parsed.get("image_index"), int) else None,
            source_platform=_text(parsed.get("source_platform")), image_url=_text(image_url),
            mime_type=_text(parsed.get("mime_type")), status=_text(parsed.get("status")),
            source_field=source_field, provenance=provenance,
        ))
    return refs, issues


def parse_nutrition(text: str | None) -> tuple[dict[str, dict], str | None, list[dict]]:
    parsed: dict[str, dict] = {}
    issues: list[dict] = []
    basis_match = re.search(r"\bper\s*100\s*(g|ml)\b", text or "", re.IGNORECASE)
    basis = f"per_100{'ml' if basis_match and basis_match.group(1).lower() == 'ml' else 'g'}" if basis_match else None
    if text and not basis:
        issues.append({"severity": "warning", "record_id": None, "field_path": "nutrition.basis",
                       "code": "nutrition_basis_missing", "message": "Could not identify a per-100-g/ml nutrition basis."})
    if text:
        for key, pattern in NUTRIENT_PATTERNS.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            amount, original_unit = match.group(1), match.group(2)
            number = decimal_value(amount)
            if number is None or number < 0:
                issues.append({"severity": "error", "record_id": None, "field_path": f"nutrition.{key}",
                               "code": "invalid_nutrition_value", "message": "Nutrient amount must be a nonnegative number."})
                continue
            parsed[key] = {"amount": amount, "original_unit": original_unit,
                           "normalized_value": None, "normalized_unit": None}
    return parsed, basis, issues


def _annotation_record(path: Path, headers: list[str], row_number: int, row: tuple,
                       raw_record_id: str, context: AcquisitionContext,
                       image_refs: list[ImageReference], price_records: list[AcquisitionRecord]) -> dict:
    values = _value_map(headers, row)
    fields = _field_records(headers, row)
    fingerprint = source_row_fingerprint(fields)
    category_map = category_candidate(values.get("Product category"), values.get("Product name"))
    record_id = stable_id("cand", path.name, PRODUCT_SHEET, str(row_number), raw_record_id)
    src = source_record(path.name, PRODUCT_SHEET, row_number, raw_record_id, "primary")
    src.update({"license": "unknown",
                "attribution": "User-supplied workbook; original dataset license/source not stated",
                "worksheet": PRODUCT_SHEET, "row_number": row_number})
    values_for_annotation = {
        "product name": values.get("Product name"), "brand": values.get("Brand name"),
        "category": values.get("Product category"),
        "product id": raw_record_id,
        "verification status": "Candidate source only; not independently verified",
    }
    ann = make_annotation(record_id, [src], context.started_at.isoformat(), fields,
                          values_for_annotation, category_map, row_number)
    refs = [src["source_record_id"]]
    def candidate(value):
        return annotation_field(value, "requires_review", refs,
                                "Imported from the supplied candidate workbook; not independently verified.") if value not in (None, "") else annotation_field()

    ann["identity"]["variant"]["name"] = candidate(values.get("Product variant/flavour"))
    ann["identity"]["variant"]["flavour"] = candidate(values.get("Product variant/flavour"))
    barcode = values.get("Barcode number")
    # Annotation GTIN is string-typed. Keep numeric Excel input in original
    # source fields/metadata and leave the GTIN candidate unset rather than
    # coercing it into a plausible-looking digit string.
    ann["identity"]["pack"]["gtin"] = candidate(None if _numeric_excel_cell(barcode) else barcode)
    pack_text = _text(values.get("Pack size"))
    quantity = None
    pack_unit = None
    if pack_text:
        from normalise.units import parse_pack_size
        parsed_pack = parse_pack_size(pack_text)
        if parsed_pack:
            quantity, pack_unit = parsed_pack
    ann["identity"]["pack"]["declared_quantity"] = (
        annotation_field({"original": pack_text, "amount": quantity, "unit": pack_unit}, "requires_review", refs,
                         "Parsed quantity is a candidate interpretation of the original pack-size text.")
        if pack_text else annotation_field())
    multi = re.search(r"(\d+)\s*[x×]", pack_text or "", re.IGNORECASE)
    ann["identity"]["pack"]["multipack_count"] = candidate(int(multi.group(1)) if multi else None)
    ann["label"]["ingredients_original"] = candidate(values.get("Ingredients (copy from pack)"))
    nutrition_text = _text(values.get("Nutritional information (per 100 g/ml)"))
    nutrient_values, basis, _ = parse_nutrition(nutrition_text)
    ann["label"]["nutrition"]["basis"] = candidate(basis)
    ann["label"]["nutrition"]["panel_source_text"] = candidate(nutrition_text)
    for nutrient, detail in ann["label"]["nutrition"]["nutrients"].items():
        found = nutrient_values.get(nutrient)
        if found:
            detail["original_value"] = candidate(found["amount"])
            detail["original_unit"] = found["original_unit"]
            # No normalized value is derived in this import.
    claims = _text(values.get("Marketing claims (exact wording)"))
    ann["label"]["claims"] = candidate([part.strip() for part in claims.split(";") if part.strip()] if claims else None)
    ann["annotation_status"] = "pending_review"
    ann["verification"] = {"status": "unverified",
                            "notes": "Candidate workbook assertions; source images and retailer prices have not been independently verified."}
    ann["source_row_fingerprint"] = fingerprint
    ann["candidate_source_metadata"] = {
        "source_id": SOURCE_ID,
        "candidate_source_status": "candidate",
        "barcode_original_cell": ({"value": json_value(barcode), "excel_value_type": "numeric",
                                   "gtin_candidate_created": False,
                                   "reason": "Numeric Excel cells cannot preserve or establish barcode text."}
                                  if _numeric_excel_cell(barcode) else
                                  {"value": json_value(barcode), "excel_value_type": "text" if isinstance(barcode, str) else "missing",
                                   "gtin_candidate_created": isinstance(barcode, str)}),
        "image_references": [img.model_dump(mode="json") for img in image_refs],
        "retailer_price_candidate_record_ids": [record.record_id for record in price_records],
        "retailer_prices_verified": False,
        "source_claimed_notes": _text(values.get("Photo/source notes")),
    }
    ann["research_assertions"] = {
        "front_of_pack_marketing_claim": claims,
        "reported_ingredient_or_reality_description": None,
        "alleged_misleading_concern": None,
        "reported_regulatory_or_scrutiny_statement": None,
        "source_claimed_verification_status": "Candidate workbook; not independently verified",
        "pipeline_verification_status": "unverified",
        "assertion_note": "Preserved workbook assertions only; no retailer or package evidence was fetched or independently checked.",
    }
    return ann


class CompleteCatalogWorkbookAdapter:
    """Local-file adapter for the user-supplied candidate catalog workbook."""

    source_id = SOURCE_ID
    adapter_version = IMPORTER_VERSION
    capabilities = SourceCapabilities(product_identity=True, retailer_listing=True,
                                      price_observation=True, images=True, location_scoped=False)

    def __init__(self, workbook_path: Path):
        self.workbook_path = workbook_path
        self.headers, self.rows = _headers_and_records(workbook_path)

    def check_policy(self, registry: SourceRegistry):
        registration = registry.get(self.source_id)
        return registry.policy_decision(self.source_id,
                                        requires_network=registration.network_acquisition if registration else False)

    def fetch(self, context: AcquisitionContext):
        for row_number, row in self.rows:
            values = _value_map(self.headers, row)
            product_id = _text(values.get("Product Submission ID")) or f"row-{row_number}"
            fields = _field_records(self.headers, row)
            payload = {"workbook": self.workbook_path.name, "worksheet": PRODUCT_SHEET,
                       "row_number": row_number, "source_fields": fields,
                       "source_row_fingerprint": source_row_fingerprint(fields),
                       "source_row_id": f"{SOURCE_ID}:{PRODUCT_SHEET}:row-{row_number}:"
                                        f"{source_row_fingerprint(fields)[:16]}"}
            yield RawSourceRecord(
                source_id=self.source_id, record_id=product_id, payload=payload,
                record_locator=f"{self.workbook_path.name}#{PRODUCT_SHEET}!{row_number}",
                retrieved_at=context.started_at, license="unknown",
                attribution="User-supplied workbook; original dataset license/source not stated",
                adapter_version=self.adapter_version,
            )

    def normalize(self, raw: RawSourceRecord) -> AcquisitionRecord:
        if raw.source_id != self.source_id:
            raise ValueError("Raw record belongs to a different source")
        source_fields = raw.payload["source_fields"]
        values = {field["column_name"]: field["original_value"] for field in source_fields}
        row_number = int(raw.payload["row_number"])
        record_locator = raw.record_locator or raw.record_id
        source_url_raw = _text(values.get("Product source URL"))
        source_url = source_url_raw if valid_http_url(source_url_raw) else None
        product_id = str(values.get("Product Submission ID") or raw.record_id)
        image_refs, _ = parse_image_references(values, product_id,
                                               AcquisitionContext(run_id="import", started_at=raw.retrieved_at),
                                               row_number)
        source_record_prov = lambda column: _provenance(
            AcquisitionContext(run_id="import", started_at=raw.retrieved_at), PRODUCT_SHEET,
            row_number, column, values.get(column), source_url)

        def val(column: str, value: Any, unit: str | None = None):
            return FieldValue(value=value, unit=unit,
                              provenance=source_record_prov(column) if value is not None else None)

        pack_text = _text(values.get("Pack size"))
        pack_size = None
        pack_unit = None
        if pack_text:
            from normalise.units import parse_pack_size
            parsed = parse_pack_size(pack_text)
            if parsed:
                pack_size, pack_unit = parsed
        multipack_match = re.search(r"(\d+)\s*[x×]", pack_text or "", re.IGNORECASE)
        image_refs = [img for img in image_refs]
        category = _text(values.get("Product category"))
        identity = ProductIdentity(
            source_product_id=val("Product Submission ID", product_id),
            gtin=val("Barcode number", values.get("Barcode number")),
            name=val("Product name", _text(values.get("Product name"))),
            brand=val("Brand name", _text(values.get("Brand name"))),
            category=val("Product category", category),
            variant=val("Product variant/flavour", _text(values.get("Product variant/flavour"))),
            pack_quantity=val("Pack size", Decimal(str(pack_size)) if pack_size is not None else None, pack_unit),
            pack_unit=val("Pack size", pack_unit),
            multipack_count=val("Pack size", int(multipack_match.group(1)) if multipack_match else None),
        )
        retailer_name = _retailer_from_product_url(source_url)
        listing = RetailerListing(
            retailer_name=FieldValue(
                value=retailer_name,
                provenance=source_record_prov("Product source URL") if retailer_name is not None else None,
            ),
            listing_url=val("Product source URL", source_url),
            listing_name=val("Product name", _text(values.get("Product name"))),
            image_refs=image_refs,
        )
        price_date_raw = values.get("Price checked date")
        price_date = _date(price_date_raw)
        date_prov = source_record_prov("Price checked date") if price_date else None
        # The product record is an identity/listing candidate. Price columns are
        # emitted separately as three observation records by import_catalog_workbook.
        return AcquisitionRecord(
            source_id=self.source_id, record_id=f"{source_row_identity(raw)}:product",
            source_license="unknown", source_attribution=raw.attribution,
            collected_at=raw.retrieved_at, adapter_version=self.adapter_version,
            verification_status="candidate", product_identity=identity, listing=listing,
            raw_record_ref=RawRecordReference(payload_sha256=raw.payload_sha256,
                                              record_locator=record_locator),
        )


def _observation_record(adapter: CompleteCatalogWorkbookAdapter, raw: RawSourceRecord,
                        product_record: AcquisitionRecord, retailer: str, price_column: str,
                        column_name: str, context: AcquisitionContext,
                        image_refs: list[ImageReference]) -> AcquisitionRecord:
    source_fields = raw.payload["source_fields"]
    values = {field["column_name"]: field["original_value"] for field in source_fields}
    raw_price = values.get(column_name)
    price = _price(raw_price)
    price_provenance = _provenance(context, PRODUCT_SHEET, int(raw.payload["row_number"]),
                                   column_name, raw_price)
    date_raw = values.get("Price checked date")
    observation_date = _date(date_raw)
    date_provenance = _provenance(context, PRODUCT_SHEET, int(raw.payload["row_number"]),
                                  "Price checked date", date_raw) if observation_date else None
    currency_provenance = _provenance(context, PRODUCT_SHEET, int(raw.payload["row_number"]),
                                      column_name, f"INR inferred from header {column_name!r}")
    url_value = _text(values.get("Product source URL")) if retailer == "Zepto" else None
    listing_url = url_value if valid_http_url(url_value) else None
    if retailer == "Zepto":
        retailer_name_prov = _provenance(context, PRODUCT_SHEET, int(raw.payload["row_number"]),
                                         "Product source URL", url_value)
    else:
        retailer_name_prov = _provenance(context, PRODUCT_SHEET, int(raw.payload["row_number"]),
                                         column_name, column_name)
    listing = RetailerListing(
        retailer_name=FieldValue(value=retailer, provenance=retailer_name_prov),
        listing_url=FieldValue(value=listing_url,
                               provenance=_provenance(context, PRODUCT_SHEET, int(raw.payload["row_number"]),
                                                      "Product source URL", url_value) if listing_url else None),
        listing_name=product_record.listing.listing_name if product_record.listing else FieldValue(),
        image_refs=image_refs if retailer == "Zepto" else [],
    )
    observation = PriceObservation(
        observed_at=None,
        observed_date=observation_date,
        observed_date_provenance=date_provenance,
        selling_price=FieldValue(value=price, unit="INR", provenance=price_provenance if raw_price is not None else None),
        currency="INR", currency_provenance=currency_provenance,
        location={"country": "IN", "pin_code": None},
    )
    retailer_key = re.sub(r"[^a-z0-9]+", "_", retailer.lower()).strip("_")
    return AcquisitionRecord(
        source_id=adapter.source_id,
        record_id=f"{source_row_identity(raw)}:price:{retailer_key}",
        source_license="unknown", source_attribution=raw.attribution,
        collected_at=raw.retrieved_at, adapter_version=adapter.adapter_version,
        verification_status="candidate", product_identity=product_record.product_identity,
        listing=listing, observation=observation,
        raw_record_ref=RawRecordReference(payload_sha256=raw.payload_sha256,
                                          record_locator=f"{raw.record_locator}#{column_name}"),
    )


def _workbook_snapshot(path: Path) -> list[dict]:
    wb = load_workbook(path, read_only=True, data_only=False)
    records = []
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        header_row = 1 if ws.title == PRODUCT_SHEET else 3
        headers = rows[header_row - 1] if len(rows) >= header_row else ()
        for row_number, row in enumerate(rows, 1):
            if not any(value is not None for value in row):
                continue
            records.append({"source_workbook": path.name, "worksheet": ws.title,
                            "row_number": row_number,
                            "cells": [{"column_index": i + 1, "column_name": (
                                str(headers[i]) if i < len(headers) and headers[i] is not None
                                else f"column_{i + 1}"),
                                       "is_header_row": row_number == header_row,
                                       "original_value": json_value(value),
                                       "is_formula": isinstance(value, str) and value.startswith("=")}
                                      for i, value in enumerate(row)]})
    wb.close()
    return records


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False, separators=(",", ":"), default=str) + "\n")


def import_catalog_workbook(workbook_path: Path, output_dir: Path, *,
                            context: AcquisitionContext | None = None,
                            registry: SourceRegistry = DEFAULT_SOURCE_REGISTRY) -> dict:
    """Write an isolated candidate release; the input workbook is read-only."""
    workbook_path = Path(workbook_path)
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Candidate output directory is not empty; refusing overwrite: {output_dir}")
    if not workbook_path.is_file():
        raise FileNotFoundError(workbook_path)
    context = context or AcquisitionContext()
    decision = registry.policy_decision(SOURCE_ID, requires_network=False)
    if not decision.allowed:
        raise PermissionError(decision.reason)

    adapter = CompleteCatalogWorkbookAdapter(workbook_path)
    adapter_decision = adapter.check_policy(registry)
    if not adapter_decision.allowed:
        raise PermissionError(adapter_decision.reason)
    output_dir.mkdir(parents=True, exist_ok=True)
    input_hash = hashlib.sha256(workbook_path.read_bytes()).hexdigest()
    headers = adapter.headers
    raw_records = list(adapter.fetch(context))
    annotations: list[dict] = []
    acquisitions: list[AcquisitionRecord] = []
    image_jsonl: list[dict] = []
    issues: list[dict] = []
    barcode_counts = Counter()
    category_counts = Counter()
    pack_counts = Counter()
    nutrition_counts = Counter()
    price_counts = Counter()
    retailer_url_missing = Counter()
    source_product_ids = []
    price_total = 0
    price_not_verified = 0

    for raw in raw_records:
        issue_start = len(issues)
        raw_issues = validate_raw_source_record(raw)
        issues.extend(issue.model_dump(mode="json") for issue in raw_issues)
        values = {field["column_name"]: field["original_value"] for field in raw.payload["source_fields"]}
        product_id = _text(values.get("Product Submission ID")) or raw.record_id
        source_product_ids.append(product_id)
        row_number = int(raw.payload["row_number"])
        image_refs, image_issues = parse_image_references(values, product_id, context, row_number)
        issues.extend(image_issues)
        image_jsonl.extend({"source_id": SOURCE_ID, "source_product_id": product_id,
                            "source_workbook": workbook_path.name, "worksheet": PRODUCT_SHEET,
                            "source_row": row_number, **image.model_dump(mode="json")}
                           for image in image_refs)

        barcode = values.get("Barcode number")
        if barcode is None:
            barcode_counts["missing"] += 1
        elif _numeric_excel_cell(barcode):
            barcode_counts["numeric_requires_review"] += 1
            issues.append({"severity": "warning", "record_id": product_id,
                           "field_path": "Barcode number", "code": "numeric_barcode_requires_review",
                           "message": "Barcode is stored as an Excel number; original value is preserved and leading zeroes cannot be reconstructed."})
        elif isinstance(barcode, str) and valid_gtin(barcode):
            barcode_counts["checksum_valid_candidate_only"] += 1
        else:
            barcode_counts["invalid_format_or_checksum"] += 1
            issues.append({"severity": "warning", "record_id": product_id,
                           "field_path": "Barcode number", "code": "barcode_candidate_invalid",
                           "message": "Barcode format/checksum fails; original value preserved and not corrected."})

        source_category = _text(values.get("Product category"))
        mapping = category_candidate(source_category, values.get("Product name"))
        category_counts[source_category or "missing"] += 1
        if mapping[0] is None:
            issues.append({"severity": "warning", "record_id": product_id,
                           "field_path": "Product category", "code": "category_unmapped",
                           "message": mapping[2]})

        pack_text = _text(values.get("Pack size"))
        parsed_pack = None
        if pack_text:
            from normalise.units import parse_pack_size
            parsed_pack = parse_pack_size(pack_text)
        if parsed_pack is None:
            pack_counts["unparsed_or_missing"] += 1
            issues.append({"severity": "warning", "record_id": product_id,
                           "field_path": "Pack size", "code": "pack_size_unparsed",
                           "message": "Original pack text is preserved; no normalized pack quantity was inferred."})
        else:
            pack_counts[f"{parsed_pack[1]}_parsed"] += 1
        if pack_text and re.search(r"\d\s*[-–]\s*\d", pack_text):
            issues.append({"severity": "warning", "record_id": product_id,
                           "field_path": "Pack size", "code": "pack_size_range",
                           "message": "Pack text includes a quantity range; parsed amount remains a candidate and needs review."})

        ingredients = _text(values.get("Ingredients (copy from pack)"))
        if ingredients:
            pack_counts["ingredients_present_candidate"] += 1
        else:
            pack_counts["ingredients_missing"] += 1
            issues.append({"severity": "warning", "record_id": product_id,
                           "field_path": "Ingredients (copy from pack)", "code": "ingredients_missing",
                           "message": "Ingredient transcription is missing."})

        nutrition_text = _text(values.get("Nutritional information (per 100 g/ml)"))
        nutrients, basis, nutrition_issues = parse_nutrition(nutrition_text)
        for issue in nutrition_issues:
            issue["record_id"] = product_id
            issues.append(issue)
        nutrition_counts["panel_present"] += bool(nutrition_text)
        nutrition_counts["recognized_nutrient_fields"] += len(nutrients)
        nutrition_counts["basis_present"] += bool(basis)

        product_record = adapter.normalize(raw)
        product_record_issues = validate_acquisition_record(product_record)
        issues.extend(issue.model_dump(mode="json") for issue in product_record_issues)
        acquisitions.append(product_record)
        retailer_records = []
        for column_name, retailer in PRICE_COLUMNS:
            value = values.get(column_name)
            amount = _price(value)
            price_total += 1
            if value in (None, ""):
                price_counts[f"{retailer}:missing"] += 1
            elif amount is None or amount <= 0:
                price_counts[f"{retailer}:invalid"] += 1
                issues.append({"severity": "warning", "record_id": product_id,
                               "field_path": column_name, "code": "invalid_candidate_price",
                               "message": "Price is not positive numeric INR; source value retained without correction."})
            else:
                price_counts[f"{retailer}:present_unverified"] += 1
                price_not_verified += 1
            if retailer in {"Blinkit", "Swiggy Instamart"}:
                retailer_url_missing[retailer] += 1
                issues.append({"severity": "warning", "record_id": product_id,
                               "field_path": f"{retailer}.listing_url", "code": "listing_url_missing",
                               "message": f"No individual {retailer} product evidence URL is provided."})
            rec = _observation_record(adapter, raw, product_record, retailer,
                                      retailer.lower().replace(" ", "_"), column_name, context,
                                      image_refs)
            rec_issues = validate_acquisition_record(rec)
            issues.extend(issue.model_dump(mode="json") for issue in rec_issues)
            acquisitions.append(rec)
            retailer_records.append(rec)

        ann = _annotation_record(workbook_path, headers, row_number,
                                 tuple(field["original_value"] for field in raw.payload["source_fields"]),
                                 raw.record_id, context, image_refs, retailer_records)
        annotations.append(ann)
        source_row_id = source_row_identity(raw)
        product_record_id = f"{source_row_id}:product"
        for issue in issues[issue_start:]:
            issue.setdefault("source_row_id", source_row_id)
            issue.setdefault("product_record_identity", product_record_id)

    duplicate_ids = sorted(pid for pid, count in Counter(source_product_ids).items() if count > 1)
    if duplicate_ids:
        duplicate_id_set = set(duplicate_ids)
        for raw in raw_records:
            row_fields = raw.payload["source_fields"]
            row_values = {field["column_name"]: field["original_value"] for field in row_fields}
            product_id = _text(row_values.get("Product Submission ID")) or raw.record_id
            if product_id not in duplicate_id_set:
                continue
            source_row_id = source_row_identity(raw)
            issues.append({"severity": "error", "record_id": product_id,
                           "field_path": "Product Submission ID", "code": "duplicate_source_product_id",
                           "message": "Duplicate source ID preserved as a separate row; no automatic merge was performed.",
                           "source_row_id": source_row_id,
                           "product_record_identity": f"{source_row_id}:product"})

    workbook_rows = _workbook_snapshot(workbook_path)
    # Identity validation repeats for each retailer observation because the
    # acquisition records intentionally share the product identity. Report a
    # single product-level issue while retaining distinct retailer URL issues.
    deduplicated_issues = []
    seen_issue_keys = set()
    for issue in issues:
        key = (issue.get("source_row_id"), issue.get("product_record_identity"),
               issue.get("field_path"), issue.get("code"), issue.get("message"))
        if key not in seen_issue_keys:
            seen_issue_keys.add(key)
            deduplicated_issues.append(issue)
    issues = deduplicated_issues
    annotation_path = output_dir / "candidate_annotations.jsonl"
    acquisition_path = output_dir / "acquisition_observations.jsonl"
    image_path = output_dir / "image_references.jsonl"
    source_rows_path = output_dir / "source_workbook_rows.jsonl"
    _write_jsonl(annotation_path, annotations)
    _write_jsonl(acquisition_path, [record.model_dump(mode="json") for record in acquisitions])
    _write_jsonl(image_path, image_jsonl)
    _write_jsonl(source_rows_path, workbook_rows)

    annotation_validation = validate_file(annotation_path)
    report = {
        "source_id": SOURCE_ID, "source_workbook": workbook_path.name,
        "source_sha256": input_hash, "candidate_status": "candidate",
        "verification_status": "unverified", "candidate_annotation_count": len(annotations),
        "acquisition_record_count": len(acquisitions),
        "product_listing_record_count": sum(record.observation is None for record in acquisitions),
        "price_candidate_record_count": sum(record.observation is not None for record in acquisitions),
        "price_observation_record_count": price_not_verified,
        "missing_price_placeholder_count": sum(count for key, count in price_counts.items() if key.endswith(":missing")),
        "invalid_price_placeholder_count": sum(count for key, count in price_counts.items() if key.endswith(":invalid")),
        "acquisition_records_by_type": {
            "product_listing": sum(record.observation is None for record in acquisitions),
            "populated_unverified_price": price_not_verified,
            "missing_price_placeholder": sum(count for key, count in price_counts.items() if key.endswith(":missing")),
            "invalid_price_placeholder": sum(count for key, count in price_counts.items() if key.endswith(":invalid")),
        },
        "source_product_ids_total": len(source_product_ids),
        "source_product_ids_unique": len(set(source_product_ids)),
        "duplicate_source_product_ids": duplicate_ids,
        "worksheets_preserved": sorted({row["worksheet"] for row in workbook_rows}),
        "nonempty_workbook_rows_preserved": len(workbook_rows),
        "source_fields_per_product_row": len(headers),
        "source_row_fingerprints": "SHA-256 over ordered original header/value pairs",
        "image_references": {"count": len(image_jsonl), "expected": len(annotations) * len(IMAGE_COLUMNS),
                             "source_platform_counts": dict(Counter(item["source_platform"] for item in image_jsonl)),
                             "downloaded_or_network_checked": False},
        "barcode_validation": dict(barcode_counts),
        "category_distribution": dict(category_counts),
        "pack_and_ingredient_checks": dict(pack_counts),
        "nutrition_checks": dict(nutrition_counts),
        "retailer_price_candidates": {"candidate_record_count": price_total,
                                      "populated_unverified_count": price_not_verified,
                                      "missing_placeholder_count": sum(count for key, count in price_counts.items() if key.endswith(":missing")),
                                      "invalid_placeholder_count": sum(count for key, count in price_counts.items() if key.endswith(":invalid")),
                                      "by_retailer": dict(price_counts),
                                      "prices_are_verified": False},
        "individual_product_url_missing_count": dict(retailer_url_missing),
        "product_source_url_count": sum(bool(_text({f["column_name"]: f["original_value"] for f in raw.payload["source_fields"]}.get("Product source URL"))) for raw in raw_records),
        "collection_date_only_count": sum(_date({f["column_name"]: f["original_value"] for f in raw.payload["source_fields"]}.get("Price checked date")) is not None for raw in raw_records),
        "collection_time_invented": False, "pin_code_invented": False,
        "source_license": "unknown", "source_attribution": "User-supplied workbook; original dataset license/source not stated",
        "annotation_schema_validation": {k: annotation_validation.get(k) for k in
                                         ("status", "errors_count", "warnings_count", "records_included", "missingness")},
        "issues_count": len(issues),
        "issues_by_code": dict(Counter(issue["code"] for issue in issues)),
        "issues": issues,
    }
    (output_dir / "data_quality_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    (output_dir / "annotation_validation_report.json").write_text(
        json.dumps(annotation_validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "manifest_version": "1.0", "source_id": SOURCE_ID, "importer_version": IMPORTER_VERSION,
        "run_id": context.run_id, "imported_at": context.started_at.isoformat(),
        "input_workbook": workbook_path.name, "input_sha256": input_hash,
        "candidate_annotation_records": len(annotations),
        "product_listing_records": sum(record.observation is None for record in acquisitions),
        "price_candidate_records": sum(record.observation is not None for record in acquisitions),
        "populated_unverified_price_observations": price_not_verified,
        "missing_price_placeholders": sum(count for key, count in price_counts.items() if key.endswith(":missing")),
        "invalid_price_placeholders": sum(count for key, count in price_counts.items() if key.endswith(":invalid")),
        "acquisition_record_count": len(acquisitions),
        "image_reference_records": len(image_jsonl), "source_workbook_rows": len(workbook_rows),
        "candidate_status": "unverified; isolated candidate source; excluded from verified training data",
        "outputs": [annotation_path.name, acquisition_path.name, image_path.name,
                    source_rows_path.name, "data_quality_report.json", "annotation_validation_report.json"],
        "policy_decision": decision.model_dump(mode="json"),
    }
    (output_dir / "import_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
