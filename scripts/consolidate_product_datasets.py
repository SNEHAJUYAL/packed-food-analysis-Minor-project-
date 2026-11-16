#!/usr/bin/env python3
"""Consolidate Excel research candidates into annotation-schema-v1 review files.

Inputs are read-only. Candidates are never verified or merged by this script.
Requires openpyxl, which is already a project-environment dependency.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, PatternFill
except ImportError as exc:  # do not install implicitly
    raise SystemExit("openpyxl is required for XLSX input/output; no dependency was installed") from exc

SCRIPT_VERSION = "1.2.0"
DATASET_VERSION = "candidate-import-0.1.0"
TAXONOMY_VERSION = "india-packaged-food-v1"
NUTRIENTS = ("energy", "protein", "carbohydrate", "total_sugars", "added_sugars", "total_fat",
             "saturated_fat", "trans_fat", "fibre", "sodium", "salt")


def json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    return " ".join(text.split())


def key_text(value: Any) -> str:
    text = clean_text(value).casefold().replace("&", " and ")
    return " ".join(re.findall(r"[\w]+", text, flags=re.UNICODE))


def field(value=None, state="missing", refs=None, note=None):
    return {"value": value, "state": state, "evidence_refs": refs or [], "note": note}


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_header(header: Any, index: int) -> str:
    return clean_text(header) or f"column_{index + 1}"


def find_header(rows: list[tuple], max_scan: int = 20) -> tuple[int, list[str], list[Any]]:
    for i, row in enumerate(rows[:max_scan]):
        keys = {key_text(x) for x in row if x is not None}
        has_product = any(k in {"product name", "name", "product"} for k in keys)
        has_brand = any(k in {"brand", "brand name"} for k in keys)
        if has_product and has_brand:
            original_headers = [json_value(x) for x in row]
            return i, [canonical_header(x, n) for n, x in enumerate(row)], original_headers
    raise ValueError("Could not find a header row containing product name and brand columns")


def cell_fields(headers: list[str], row: tuple, original_headers: list[Any] | None = None) -> list[dict]:
    result = []
    # Excel data rows can extend beyond the detected header. Retain those cells
    # with stable positional names; a synthetic header is never source evidence.
    for i in range(max(len(headers), len(row))):
        original_header = headers[i] if i < len(headers) else f"column_{i + 1}"
        raw = row[i] if i < len(row) else None
        if i >= len(headers):
            raw_header = None
        else:
            raw_header = original_headers[i] if original_headers is not None and i < len(original_headers) else original_header
        normalized = clean_text(raw) if isinstance(raw, str) else json_value(raw)
        result.append({"column_index": i + 1, "column_name": original_header,
                       "original_header": json_value(raw_header),
                       "original_value": json_value(raw), "normalized_value": normalized})
    return result


def source_row_fingerprint(fields: list[dict]) -> str:
    """SHA-256 over ordered original header/value pairs, excluding normalized values."""
    pairs = []
    for cell in fields:
        header = cell.get("original_header")
        if "original_header" not in cell:  # Legacy candidates predate explicit raw headers.
            header = cell.get("column_name")
            if isinstance(header, str) and re.fullmatch(r"column_\d+", header):
                header = None
        pairs.append({"original_header": header, "original_value": cell.get("original_value")})
    canonical = json.dumps(pairs, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def value_map(fields: list[dict]) -> dict[str, Any]:
    # Use first occurrence; raw cell list remains lossless if a workbook repeats header names.
    out = {}
    for cell in fields:
        k = key_text(cell["column_name"])
        if k and k not in out:
            out[k] = cell["original_value"]
    return out


def pick(values: dict[str, Any], *names: str):
    for name in names:
        v = values.get(key_text(name))
        if v not in (None, ""):
            return v
    return None


def category_candidate(source_category: Any, product_name: Any) -> tuple[str | None, str, str]:
    cat, name = key_text(source_category), key_text(product_name)
    if not cat:
        return None, "requires_review", "Source category is missing."
    if cat in {"biscuits and cookies", "cookies"}:
        return "biscuits_cookies", "mapped_requires_review", "Source category mapped to nearest taxonomy leaf; verify from package."
    if cat in {"biscuits and snacks", "biscuits"}:
        if any(t in name.split() for t in ("bhujia", "namkeen", "sev")):
            return "namkeen", "mapped_requires_review", "Product name suggests namkeen; confirm product form from package evidence."
        if any(t in name.split() for t in ("chips", "kurkure", "angles", "snack", "crisps")):
            return "chips_savoury_snacks", "mapped_requires_review", "Source category is broad; product-name cue used only as a candidate mapping."
        if any(t in name.split() for t in ("biscuit", "biscuits", "cookie", "cookies", "wafer", "wafers")):
            return "biscuits_cookies", "mapped_requires_review", "Product-name cue suggests biscuits/cookies; verify exact form."
        return None, "requires_review", "Broad Biscuits & Snacks source label is insufficient to choose a taxonomy leaf."
    if cat in {"fruit juices", "beverages", "health drinks", "drink mixes", "juice"}:
        reason = "Source label is broader/market-facing; verify whether this is a beverage, powder or concentrate."
        return "packaged_beverages", "mapped_requires_review", reason
    if cat in {"breakfast cereals", "breakfast cereal", "cereals"}:
        if "oat" in name or "millet" in name:
            return "oats_millet_products", "mapped_requires_review", "Product-name cue suggests oats/millet; verify primary form."
        return "breakfast_cereals_muesli", "mapped_requires_review", "Mapped from source category; verify product form."
    if cat in {"instant noodles", "noodles", "pasta"}:
        return "noodles_pasta", "mapped_requires_review", "Mapped from source category; verify product form."
    if cat in {"ready to eat", "ready to eat foods", "ready to cook"}:
        return "ready_to_eat_ready_to_cook", "mapped_requires_review", "Mapped from source category; verify package preparation form."
    if cat in {"protein bars", "protein bar", "protein snacks"}:
        return "protein_bars_snacks", "mapped_requires_review", "Mapped from source category; verify product positioning/form."
    if cat in {"dairy", "dairy alternatives", "dairy alternative"}:
        return "dairy_dairy_alternatives", "mapped_requires_review", "Source uses dairy/dairy-alternative wording; verify product composition and category."
    if cat in {"sauces and condiments", "sauces", "condiments", "spreads"}:
        if any(t in name.split() for t in ("jam", "spread")):
            return "spreads", "mapped_requires_review", "Product-name cue suggests a spread; verify."
        if "soup" in name:
            return "ready_to_eat_ready_to_cook", "mapped_requires_review", "Soup classification needs product-form review."
        return "sauces_condiments_dips", "mapped_requires_review", "Mapped from source category; verify product form."
    if cat in {"staples", "spices and staples", "staple"}:
        if "spice" in name or cat == "spices and staples":
            return None, "requires_review", "Spices have no dedicated leaf here; do not silently classify as staples."
        return "packaged_staples_mixes", "mapped_requires_review", "Mapped from source category; verify that it is a packaged staple."
    if cat == "spices":
        return None, "requires_review", "Spices have no dedicated taxonomy leaf; no forced mapping."
    if cat == "honey and sweeteners":
        return None, "requires_review", "Honey/sweeteners do not have a dedicated taxonomy leaf; review taxonomy fit."
    return None, "requires_review", f"No documented mapping for source category {clean_text(source_category)!r}."


def source_record(workbook_name: str, sheet: str, row_num: int, product_id: Any,
                  source_role: str = "other") -> dict:
    external = clean_text(product_id) or f"{sheet}:row:{row_num}"
    src_id = stable_id("src", workbook_name, sheet, str(row_num), external)
    return {"source_record_id": src_id, "source_name": workbook_name,
            "external_id": external, "uri": None, "snapshot_or_retrieved_at": "unknown",
            "license": "unknown", "attribution": "unknown", "source_role": source_role,
            "derived_from": []}


def research_assertions(values: dict[str, Any]) -> dict:
    return {
        "front_of_pack_marketing_claim": json_value(pick(values, "front-of-pack claim", "front of pack claim", "claim", "FOP claim")),
        "reported_ingredient_or_reality_description": json_value(pick(values, "actual ingredients / reality", "actual ingredients", "ingredients / reality", "ingredient description", "ingredients")),
        "alleged_misleading_concern": json_value(pick(values, "primary misleading concern", "misleading concern", "concern", "allegation")),
        "reported_regulatory_or_scrutiny_statement": json_value(pick(values, "regulatory / scrutiny status", "regulatory status", "scrutiny status", "regulatory scrutiny")),
        "reported_evidence_reference_text": json_value(pick(values, "evidence source", "evidence reference", "source reference")),
        "source_claimed_verification_status": json_value(pick(values, "verification status", "verification")),
        "pipeline_verification_status": "unverified",
        "assertion_note": "Preserved source assertion; not independently verified by this importer.",
    }


def make_annotation(candidate_id: str, source_rows: list[dict], import_time: str,
                    original_fields: list[dict], values: dict[str, Any], category_map: tuple,
                    source_row_no: int, extra: dict | None = None) -> dict:
    product_name = pick(values, "product name", "name", "product")
    brand = pick(values, "brand", "brand name")
    source_cat = pick(values, "category", "product category")
    mapped_cat, map_status, map_reason = category_map
    refs = [s["source_record_id"] for s in source_rows]
    def candidate_field(value):
        if value in (None, ""):
            return field()
        return field(clean_text(value), "requires_review", refs, "Source workbook value only; package/manufacturer evidence has not been reviewed.")

    nutrients = {}
    for nutrient in NUTRIENTS:
        nutrients[nutrient] = {
            "original_value": field(), "normalized_value": field(),
            "original_unit": None, "normalized_unit": None, "normalized_basis": None,
        }
    product_id = pick(values, "product id", "id", "record id")
    annotation = {
        "schema_version": "1.0", "record_type": "annotation", "record_id": candidate_id,
        "dataset_version": DATASET_VERSION, "taxonomy_version": TAXONOMY_VERSION,
        "annotation_status": "pending_review",
        "identity": {
            "product_name": candidate_field(product_name),
            "brand": {"name": candidate_field(brand), "brand_id": None},
            "family": {"name": field(), "family_id": None},
            "variant": {"name": field(), "flavour": field(), "formulation": field(), "variant_id": None},
            "pack": {"pack_id": None, "gtin": field(), "declared_quantity": field(), "multipack_count": field()},
            "category": field(mapped_cat, "requires_review", refs,
                               f"{map_status}: {map_reason}; original category preserved separately."),
        },
        "label": {
            "ingredients_original": field(),
            "ingredients_normalized": [],
            "nutrition": {"basis": field(), "panel_source_text": field(), "nutrients": nutrients},
            "serving": {"size": field(), "servings_per_pack": field()},
            "claims": field(),
            "allergens": {"contains": field(), "precautionary": field(), "other_text": field()},
        },
        "evidence": {"source_records": source_rows, "package_items": []},
        "verification": {"status": "unverified", "notes": "Research candidate import; no package evidence or manual review asserted."},
        "review": {"primary_reviewer_id": None, "primary_reviewed_at": None, "second_reviewer_id": None,
                   "second_reviewed_at": None, "disagreements": [], "adjudication": None, "log_refs": []},
        "revision": {"number": 1, "previous_record_sha256": None, "change_reason": "Initial source-workbook candidate import."},
        "source_locations": [{"workbook": s["source_name"], "worksheet": s["worksheet"], "row_number": s["row_number"],
                              "source_record_id": s["source_record_id"]} for s in source_rows],
        "source_fields": original_fields,
        "normalized_fields": {"product_name_whitespace_normalized": clean_text(product_name),
                              "brand_whitespace_normalized": clean_text(brand),
                              "source_category_whitespace_normalized": clean_text(source_cat),
                              "candidate_category": mapped_cat, "category_mapping_status": map_status,
                              "category_mapping_reason": map_reason},
        "research_assertions": research_assertions(values),
        "import_metadata": {"imported_at": import_time, "script_version": SCRIPT_VERSION,
                            "source_row_number": source_row_no, "source_record_identifier": json_value(product_id)},
        "duplicate_review": {"candidate_duplicate_group_id": None, "duplicate_status": "unresolved",
                             "duplicate_reason": "No identity decision has been made.", "review_required": True},
        "malformed_flags": extra or {},
    }
    return annotation


def is_checklist_sheet(headers: list[str]) -> bool:
    normalized = {key_text(x) for x in headers}
    return any("photo" in h for h in normalized) and any(h in {"product id", "product name"} for h in normalized)


def extract_sheet(path: Path, sheet_name: str, rows: list[tuple], import_time: str) -> dict:
    header_index, headers, original_headers = find_header(rows)
    result = {"workbook": path.name, "sheet": sheet_name, "header_row": header_index + 1,
              "headers": headers, "records": [], "empty_rows": 0, "checklist": is_checklist_sheet(headers)}
    for row_num, row in enumerate(rows[header_index + 1:], header_index + 2):
        fields = cell_fields(headers, row, original_headers)
        if not any(x["original_value"] not in (None, "") for x in fields):
            result["empty_rows"] += 1
            continue
        values = value_map(fields)
        name = pick(values, "product name", "name", "product")
        brand = pick(values, "brand", "brand name")
        source_id = pick(values, "product id", "id", "record id")
        candidate_id = stable_id("cand", path.name, sheet_name, str(row_num), clean_text(source_id))
        src = source_record(path.name, sheet_name, row_num, source_id)
        fingerprint = source_row_fingerprint(fields)
        src["source_row_fingerprint"] = fingerprint
        src.update({"worksheet": sheet_name, "row_number": row_num})
        result["records"].append({"candidate_id": candidate_id, "row_number": row_num,
                                  "source_record": src, "source_fields": fields, "values": values,
                                  "source_row_fingerprint": fingerprint,
                                  "product_name": name, "brand": brand, "source_id": source_id})
    return result


def load_workbook_records(path: Path, import_time: str) -> tuple[list[dict], dict]:
    wb = load_workbook(path, read_only=True, data_only=True)
    sheets = [extract_sheet(path, ws.title, list(ws.iter_rows(values_only=True)), import_time) for ws in wb.worksheets]
    primary = [s for s in sheets if not s["checklist"]]
    aux = [s for s in sheets if s["checklist"]]
    candidates = []
    by_workbook_product = {}
    for sheet in primary:
        for row in sheet["records"]:
            mapped, status, reason = category_candidate(pick(row["values"], "category", "product category"), row["product_name"])
            extra = {}
            # Known misalignment in the unheaded final column: retain raw values and flag only.
            if "misleading_indian_food_products" in path.name.casefold() and "knorr classic mixed vegetable soup" in key_text(row["product_name"]):
                blank_claim = pick(row["values"], "front-of-pack claim", "front of pack claim") in (None, "")
                last_unheaded = next((f for f in reversed(row["source_fields"])
                                      if f["column_name"].startswith("column_") and f["original_value"] not in (None, "")), None)
                if blank_claim and last_unheaded:
                    extra = {"alignment_suspected": True,
                             "alignment_note": "Source claim is blank while an unheaded final cell contains text; preserve both positions and require human review. No value was moved."}
            ann = make_annotation(row["candidate_id"], [row["source_record"]], import_time, row["source_fields"],
                                  row["values"], (mapped, status, reason), row["row_number"], extra)
            ann["source_row_fingerprint"] = row["source_row_fingerprint"]
            ann["research_assertions"] = research_assertions(row["values"])
            candidates.append(ann)
            source_id_key = key_text(row["source_id"])
            name_key, brand_key = key_text(row["product_name"]), key_text(row["brand"])
            if source_id_key:
                by_workbook_product[(path.name, source_id_key)] = ann
            if name_key and brand_key:
                by_workbook_product[(path.name, name_key, brand_key)] = ann
    # Photo-checklist rows are auxiliary evidence/status, not duplicate product candidates.
    supplemental_count = 0
    for sheet in aux:
        for row in sheet["records"]:
            source_id_key = key_text(row["source_id"])
            name_key, brand_key = key_text(row["product_name"]), key_text(row["brand"])
            target = by_workbook_product.get((path.name, source_id_key)) if source_id_key else None
            target = target or by_workbook_product.get((path.name, name_key, brand_key))
            if target:
                target.setdefault("supplemental_source_rows", []).append({
                    "workbook": path.name, "worksheet": sheet["sheet"], "row_number": row["row_number"],
                    "source_record": row["source_record"], "source_fields": row["source_fields"],
                    "source_row_fingerprint": row["source_row_fingerprint"],
                    "note": "Photo checklist/status row linked by source ID and exact available product fields; not package evidence.",
                })
                target["evidence"]["source_records"].append(row["source_record"])
                target["source_locations"].append({"workbook": path.name, "worksheet": sheet["sheet"],
                                                    "row_number": row["row_number"],
                                                    "source_record_id": row["source_record"]["source_record_id"]})
                # Keep all checklist fields in preserved source fields with sheet/row metadata.
                target.setdefault("auxiliary_source_fields", []).append({"worksheet": sheet["sheet"],
                                                                           "row_number": row["row_number"],
                                                                           "fields": row["source_fields"]})
                supplemental_count += 1
            else:
                # Do not discard unmatched source rows. Preserve them as unclassified candidates.
                mapped, status, reason = None, "requires_review", "Checklist row could not be linked to the product sheet with exact source ID/name/brand."
                ann = make_annotation(row["candidate_id"], [row["source_record"]], import_time, row["source_fields"],
                                      row["values"], (mapped, status, reason), row["row_number"])
                ann["source_row_fingerprint"] = row["source_row_fingerprint"]
                ann["supplemental_only"] = True
                candidates.append(ann)
    sheet_summary = [{"worksheet": s["sheet"], "header_row": s["header_row"],
                      "nonempty_rows": len(s["records"]), "empty_rows": s["empty_rows"],
                      "treated_as_supplemental_checklist": s["checklist"]} for s in sheets]
    return candidates, {"sheets": sheet_summary, "supplemental_rows_linked": supplemental_count,
                        "empty_rows": sum(s["empty_rows"] for s in sheets)}


def distinct_variant_pair(a: dict, b: dict) -> tuple[bool, str]:
    brand_a = key_text(a["identity"]["brand"]["name"]["value"])
    brand_b = key_text(b["identity"]["brand"]["name"]["value"])
    name_a = key_text(a["identity"]["product_name"]["value"])
    name_b = key_text(b["identity"]["product_name"]["value"])
    if not brand_a or brand_a != brand_b:
        return False, ""
    tokens_a, tokens_b = set(name_a.split()), set(name_b.split())
    variant_terms = {"aloo", "nagpur", "sev", "classic", "masala", "mango", "orange", "mixed", "dark", "milk"}
    shared_product = tokens_a & tokens_b
    differing_modifiers = (tokens_a ^ tokens_b) & variant_terms
    if shared_product & {"bhujia"} and len(differing_modifiers) >= 1:
        return True, "Same brand and Bhujia product-family term, but explicit variant descriptors differ; retain as distinct candidates pending package review."
    return False, ""


def duplicate_analysis(records: list[dict]) -> tuple[list[dict], list[dict]]:
    parent = list(range(len(records)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri
    pair_info = []
    for i, a in enumerate(records):
        name_a = key_text(a["identity"]["product_name"]["value"])
        brand_a = key_text(a["identity"]["brand"]["name"]["value"])
        if not name_a or not brand_a:
            continue
        for j in range(i + 1, len(records)):
            b = records[j]
            name_b = key_text(b["identity"]["product_name"]["value"])
            brand_b = key_text(b["identity"]["brand"]["name"]["value"])
            if brand_a != brand_b or not name_b:
                continue
            ratio = SequenceMatcher(None, name_a, name_b).ratio()
            if name_a == name_b:
                union(i, j)
                pair_info.append((i, j, "possible_duplicate", "Exact normalized brand and product name across source rows; pack/GTIN unknown, human review required."))
            elif ratio >= 0.94:
                union(i, j)
                pair_info.append((i, j, "possible_duplicate", f"Same normalized brand and close product name (similarity {ratio:.2f}); pack/variant unknown, review required."))
            elif distinct_variant_pair(a, b)[0]:
                pair_info.append((i, j, "distinct_variant", distinct_variant_pair(a, b)[1]))
    groups = defaultdict(list)
    for i, j, status, reason in pair_info:
        if status == "possible_duplicate":
            groups[find(i)].extend([i, j])
    group_ids = {}
    for root, indexes in groups.items():
        unique_indexes = sorted(set(indexes))
        ids = sorted(records[i]["record_id"] for i in unique_indexes)
        group_ids[root] = stable_id("dup", *ids)
    for i, rec in enumerate(records):
        root = find(i)
        if root in group_ids:
            rec["duplicate_review"] = {"candidate_duplicate_group_id": group_ids[root],
                                       "duplicate_status": "possible_duplicate",
                                       "duplicate_reason": "At least one exact/close-name same-brand candidate; candidate groups may include different pack variants.",
                                       "review_required": True}
        else:
            rec["duplicate_review"] = {"candidate_duplicate_group_id": None, "duplicate_status": "unresolved",
                                       "duplicate_reason": "No merge/identity conclusion; product variant and pack identity remain unverified.",
                                       "review_required": True}
    for i, j, status, reason in pair_info:
        if status == "distinct_variant":
            for idx in (i, j):
                if records[idx]["duplicate_review"]["duplicate_status"] == "unresolved":
                    records[idx]["duplicate_review"]["duplicate_status"] = "distinct_variant"
                    records[idx]["duplicate_review"]["duplicate_reason"] = reason
    report_rows = []
    for i, j, status, reason in pair_info:
        report_rows.append({"candidate_a": records[i]["record_id"], "candidate_b": records[j]["record_id"],
                            "name_a": records[i]["identity"]["product_name"]["value"],
                            "brand_a": records[i]["identity"]["brand"]["name"]["value"],
                            "name_b": records[j]["identity"]["product_name"]["value"],
                            "brand_b": records[j]["identity"]["brand"]["name"]["value"],
                            "group_id": (records[i]["duplicate_review"].get("candidate_duplicate_group_id")
                                         if status == "possible_duplicate" and
                                         records[i]["duplicate_review"].get("candidate_duplicate_group_id") ==
                                         records[j]["duplicate_review"].get("candidate_duplicate_group_id") else None),
                            "duplicate_status": status, "reason": reason,
                            "review_required": True})
    possible_groups = {r["duplicate_review"]["candidate_duplicate_group_id"] for r in records
                       if r["duplicate_review"]["duplicate_status"] == "possible_duplicate"}
    return report_rows, [x for x in possible_groups if x]


def flatten_candidate(rec: dict) -> dict:
    loc = rec["source_locations"][0] if rec.get("source_locations") else {}
    assertions = rec.get("research_assertions", {})
    source_cells = {key_text(cell.get("column_name")): cell.get("original_value")
                    for cell in rec.get("source_fields", []) if isinstance(cell, dict)}
    def original_value(*names):
        for name in names:
            key = key_text(name)
            if key in source_cells:
                return source_cells[key]
        return None
    return {
        "candidate_record_id": rec["record_id"], "source_workbook": loc.get("workbook"),
        "source_row_fingerprint": rec.get("source_row_fingerprint"),
        "source_worksheet": loc.get("worksheet"), "source_row": loc.get("row_number"),
        "source_record_identifier": rec.get("import_metadata", {}).get("source_record_identifier"),
        "original_product_name": original_value("product name", "name", "product"),
        "normalized_product_name": rec["normalized_fields"]["product_name_whitespace_normalized"],
        "original_brand": original_value("brand", "brand name"),
        "normalized_brand": rec["normalized_fields"]["brand_whitespace_normalized"],
        "original_category": original_value("category", "product category"),
        "candidate_category": rec["normalized_fields"]["candidate_category"],
        "category_mapping_status": rec["normalized_fields"]["category_mapping_status"],
        "category_mapping_reason": rec["normalized_fields"]["category_mapping_reason"],
        "front_of_pack_claim_as_reported": assertions.get("front_of_pack_marketing_claim"),
        "ingredients_or_reality_as_reported": assertions.get("reported_ingredient_or_reality_description"),
        "alleged_concern_as_reported": assertions.get("alleged_misleading_concern"),
        "regulatory_statement_as_reported": assertions.get("reported_regulatory_or_scrutiny_statement"),
        "source_claimed_verification_status": assertions.get("source_claimed_verification_status"),
        "pipeline_verification_status": "unverified",
        "candidate_duplicate_group_id": rec["duplicate_review"].get("candidate_duplicate_group_id"),
        "duplicate_status": rec["duplicate_review"].get("duplicate_status"),
        "duplicate_reason": rec["duplicate_review"].get("duplicate_reason"),
        "review_required": rec["duplicate_review"].get("review_required"),
        "malformed_flags": json.dumps(rec.get("malformed_flags", {}), ensure_ascii=False),
        "source_fields_json": json.dumps(rec.get("source_fields", []), ensure_ascii=False),
        "source_locations_json": json.dumps(rec.get("source_locations", []), ensure_ascii=False),
        "supplemental_source_rows_json": json.dumps(rec.get("supplemental_source_rows", []), ensure_ascii=False),
    }


def write_csv(path: Path, rows: list[dict], headers: list[str] | None = None):
    headers = headers or (list(rows[0]) if rows else ["status"])
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_review_xlsx(path: Path, candidate_rows: list[dict], duplicate_rows: list[dict], category_rows: list[dict], claim_rows: list[dict]):
    wb = Workbook()
    wb.remove(wb.active)
    for title, rows in (("Candidates", candidate_rows), ("Duplicates", duplicate_rows),
                        ("Category Review", category_rows), ("Claim Queue", claim_rows)):
        ws = wb.create_sheet(title)
        headers = list(rows[0]) if rows else ["status"]
        ws.append(headers)
        for row in rows:
            ws.append([row.get(h) for h in headers])
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="274060")
        for column in ws.columns:
            width = min(60, max(12, max((len(str(c.value or "")) for c in column[:40]), default=12) + 2))
            ws.column_dimensions[column[0].column_letter].width = width
    wb.save(path)


def read_candidate_records(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def compare_source_rows(records: list[dict], previous_jsonl: Path | None) -> list[dict]:
    if previous_jsonl is None:
        return []
    prior_by_id = {r.get("record_id"): r for r in read_candidate_records(previous_jsonl)}
    changes = []
    for current in records:
        old = prior_by_id.get(current.get("record_id"))
        if old is None:
            continue
        old_fingerprint = old.get("source_row_fingerprint")
        basis = "stored_sha256"
        if old_fingerprint is None:
            old_fingerprint = source_row_fingerprint(old.get("source_fields", []))
            basis = "reconstructed_legacy_source_fields"
        new_fingerprint = current.get("source_row_fingerprint")
        if old_fingerprint != new_fingerprint:
            loc = current.get("source_locations", [{}])[0]
            changes.append({"candidate_record_id": current.get("record_id"),
                            "source_workbook": loc.get("workbook"), "source_worksheet": loc.get("worksheet"),
                            "source_row": loc.get("row_number"), "previous_fingerprint": old_fingerprint,
                            "current_fingerprint": new_fingerprint, "comparison_basis": basis,
                            "note": ("Prior candidate predates explicit raw-header fingerprints; blank/raw headers may not be recoverable."
                                     if basis.startswith("reconstructed") else "Source row values or headers changed while candidate ID stayed the same."),
                            "review_required": True})
    return changes


def consolidate(inputs: list[Path], out_dir: Path, import_time: str | None = None,
                compare_to: Path | None = None) -> dict:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"Output directory is not empty; refusing to overwrite generated or existing data: {out_dir}")
    for path in inputs:
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.suffix.casefold() != ".xlsx":
            raise ValueError(f"Only XLSX inputs are supported: {path}")
    if compare_to is not None and not compare_to.is_file():
        raise FileNotFoundError(compare_to)
    stamp = import_time or datetime.now(timezone.utc).isoformat(timespec="seconds")
    all_records, input_summary, malformed = [], [], []
    for path in inputs:
        records, summary = load_workbook_records(path, stamp)
        all_records.extend(records)
        input_summary.append({"workbook": path.name, "path": str(path), "sha256": file_sha(path),
                              "candidate_records_added": len(records), **summary})
        for rec in records:
            if rec.get("malformed_flags", {}).get("alignment_suspected"):
                malformed.append({"candidate_record_id": rec["record_id"],
                                  "workbook": rec["source_locations"][0]["workbook"],
                                  "worksheet": rec["source_locations"][0]["worksheet"],
                                  "source_row": rec["source_locations"][0]["row_number"],
                                  "issue": rec["malformed_flags"]["alignment_note"],
                                  "source_fields_json": json.dumps(rec["source_fields"], ensure_ascii=False)})
            if not rec["identity"]["product_name"]["value"]:
                malformed.append({"candidate_record_id": rec["record_id"],
                                  "workbook": rec["source_locations"][0]["workbook"],
                                  "worksheet": rec["source_locations"][0]["worksheet"],
                                  "source_row": rec["source_locations"][0]["row_number"],
                                  "issue": "Nonempty data row has no product name.",
                                  "source_fields_json": json.dumps(rec["source_fields"], ensure_ascii=False)})
    dup_rows, dup_groups = duplicate_analysis(all_records)
    flat = [flatten_candidate(r) for r in all_records]
    source_changes = compare_source_rows(all_records, compare_to)
    category_rows = [dict(candidate_record_id=r["record_id"],
                          source_workbook=r["source_locations"][0]["workbook"],
                          source_worksheet=r["source_locations"][0]["worksheet"],
                          source_row=r["source_locations"][0]["row_number"],
                          original_category=r["normalized_fields"]["source_category_whitespace_normalized"],
                          candidate_category=r["normalized_fields"]["candidate_category"],
                          category_mapping_status=r["normalized_fields"]["category_mapping_status"],
                          category_mapping_reason=r["normalized_fields"]["category_mapping_reason"],
                          review_required=True) for r in all_records
                     if r["normalized_fields"]["category_mapping_status"] in {"requires_review", "mapped_requires_review"}]
    claim_rows = []
    for rec in all_records:
        assertion = rec["research_assertions"]
        if any(assertion.get(k) not in (None, "") for k in (
                "front_of_pack_marketing_claim", "reported_ingredient_or_reality_description",
                "alleged_misleading_concern", "reported_regulatory_or_scrutiny_statement")):
            loc = rec["source_locations"][0]
            claim_rows.append({"candidate_record_id": rec["record_id"], "source_workbook": loc["workbook"],
                               "source_worksheet": loc["worksheet"], "source_row": loc["row_number"],
                               "product_name_as_reported": rec["identity"]["product_name"]["value"],
                               "brand_as_reported": rec["identity"]["brand"]["name"]["value"],
                               "front_of_pack_claim_as_reported": assertion.get("front_of_pack_marketing_claim"),
                               "reported_ingredients_or_reality": assertion.get("reported_ingredient_or_reality_description"),
                               "alleged_concern": assertion.get("alleged_misleading_concern"),
                               "reported_regulatory_statement": assertion.get("reported_regulatory_or_scrutiny_statement"),
                               "source_claimed_status": assertion.get("source_claimed_verification_status"),
                               "pipeline_verification_status": "unverified", "review_required": True})
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "jsonl": "consolidated_annotation_candidates.jsonl",
        "csv": "consolidated_product_candidates.csv",
        "xlsx": "consolidated_product_candidates.xlsx",
        "duplicates": "duplicate_candidates.csv",
        "categories": "category_mapping_review.csv",
        "claims": "claim_verification_queue.csv",
        "malformed": "malformed_suspicious_records.csv",
        "source_row_changes": "source_row_changes.csv",
        "validation_report": "annotation_validation_report.json",
    }
    with (out_dir / outputs["jsonl"]).open("w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
    write_csv(out_dir / outputs["csv"], flat)
    write_review_xlsx(out_dir / outputs["xlsx"], flat, dup_rows, category_rows, claim_rows)
    write_csv(out_dir / outputs["duplicates"], dup_rows)
    write_csv(out_dir / outputs["categories"], category_rows)
    write_csv(out_dir / outputs["claims"], claim_rows)
    write_csv(out_dir / outputs["malformed"], malformed)
    write_csv(out_dir / outputs["source_row_changes"], source_changes,
              ["candidate_record_id", "source_workbook", "source_worksheet", "source_row",
               "previous_fingerprint", "current_fingerprint", "comparison_basis", "note", "review_required"])
    category_counts = defaultdict(int)
    for rec in all_records:
        category_counts[rec["normalized_fields"]["category_mapping_status"]] += 1
    status_counts = defaultdict(int)
    for rec in all_records:
        status_counts[rec["duplicate_review"]["duplicate_status"]] += 1
    manifest = {
        "manifest_version": "1.0", "pipeline": "scripts/consolidate_product_datasets.py",
        "script_version": SCRIPT_VERSION, "imported_at": stamp,
        "annotation_schema_version": "1.0", "candidate_dataset_version": DATASET_VERSION,
        "taxonomy_version": TAXONOMY_VERSION,
        "inputs": input_summary, "candidate_records_total": len(all_records),
        "possible_duplicate_group_count": len(dup_groups), "duplicate_pair_count": sum(x["duplicate_status"] == "possible_duplicate" for x in dup_rows),
        "duplicate_status_counts": dict(status_counts),
        "uncertain_category_mapping_count": sum(r["normalized_fields"]["category_mapping_status"] == "requires_review" for r in all_records),
        "category_review_queue_count": len(category_rows),
        "category_mapping_status_counts": dict(category_counts),
        "claim_verification_queue_count": len(claim_rows), "malformed_or_suspicious_count": len(malformed),
        "all_candidates_annotation_status": "pending_review",
        "all_candidates_pipeline_verification_status": "unverified",
        "no_automatic_merges": True,
        "outputs": outputs,
        "source_row_comparison_input": str(compare_to) if compare_to else None,
        "source_row_change_count": len(source_changes),
        "source_row_fingerprint": "sha256 of ordered original header/value pairs; independent of candidate record ID",
        "limitations": ["Workbook statements are research assertions, not independent verification or package transcription.",
                        "Input licenses/attribution were not established by importing workbook cells and are marked unknown.",
                        "Category mappings are candidates and require review; no category is marked verified.",
                        "No GTIN, pack size, nutrition, serving size, package photo, source URL or reviewer was invented."],
    }
    (out_dir / "import_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Run the project's actual v1 validator on generated candidates.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from validate_annotation_dataset import validate_file
    validation = validate_file(out_dir / outputs["jsonl"])
    (out_dir / outputs["validation_report"]).write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest["annotation_validator"] = {"status": validation["status"], "errors_count": validation["errors_count"],
                                         "warnings_count": validation["warnings_count"],
                                         "report": "annotation_validation_report.json"}
    (out_dir / "import_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if validation["status"] != "ok":
        raise ValueError(f"Generated candidate JSONL failed annotation validator: {validation['errors_count']} errors")
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=Path, required=True,
                        help="XLSX path; repeat for each input workbook")
    parser.add_argument("--out-dir", type=Path, required=True,
                        help="New/empty output directory; existing content is never overwritten")
    parser.add_argument("--import-timestamp", help="Optional fixed ISO timestamp for reproducible reruns")
    parser.add_argument("--compare-to", type=Path,
                        help="Read a prior candidate JSONL and report same-ID source-row fingerprint changes")
    args = parser.parse_args(argv)
    try:
        result = consolidate(args.input, args.out_dir, args.import_timestamp, args.compare_to)
    except Exception as exc:
        print(f"consolidation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "ok", "candidate_records_total": result["candidate_records_total"],
                      "possible_duplicate_group_count": result["possible_duplicate_group_count"],
                      "uncertain_category_mapping_count": result["uncertain_category_mapping_count"],
                      "claim_verification_queue_count": result["claim_verification_queue_count"],
                      "malformed_or_suspicious_count": result["malformed_or_suspicious_count"],
                      "annotation_validator": result["annotation_validator"],
                      "output_directory": str(args.out_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
