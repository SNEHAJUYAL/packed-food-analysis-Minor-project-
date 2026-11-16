#!/usr/bin/env python3
"""Read-only validator for the isolated research annotation JSONL dataset."""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TAXONOMY = {
    "biscuits_cookies", "chips_savoury_snacks", "namkeen", "breakfast_cereals_muesli",
    "oats_millet_products", "noodles_pasta", "ready_to_eat_ready_to_cook",
    "protein_bars_snacks", "spreads", "nuts_makhana_trail_mix", "dairy_dairy_alternatives",
    "packaged_beverages", "sauces_condiments_dips", "packaged_staples_mixes",
    "childrens_packaged_foods", "bakery_confectionery",
}
STATES = {"verified", "missing", "illegible", "not_declared", "not_applicable", "requires_review"}
GTIN_LENGTHS = {8, 12, 13, 14}
PACK_UNITS = {"g", "kg", "mg", "µg", "mcg", "ml", "l", "L", "count", "piece", "pieces", "pack"}
NUTRIENT_UNITS = {"energy": "kcal", "sodium": "mg", "salt": "g", "protein": "g",
                  "carbohydrate": "g", "total_sugars": "g", "added_sugars": "g", "total_fat": "g",
                  "saturated_fat": "g", "trans_fat": "g", "fibre": "g"}
BASES = {"per_100g", "per_100ml", "per_serving", "per_pack", "other"}
RECORD_TYPES = {"annotation", "template", "synthetic_fixture"}
VERIFICATION = {"unverified", "partially_verified", "verified", "requires_review"}


def get(obj: Any, path: str, default=None):
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def normalized_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(re.findall(r"[\w]+", text, flags=re.UNICODE))


def gtin_check_digit_ok(digits: str) -> bool:
    if len(digits) not in GTIN_LENGTHS or not digits.isdigit():
        return False
    body = digits[:-1]
    total = sum(int(ch) * (3 if (len(body) - i) % 2 else 1) for i, ch in enumerate(body))
    return (10 - total % 10) % 10 == int(digits[-1])


class Validator:
    def __init__(self):
        self.errors: list[dict] = []
        self.warnings: list[dict] = []
        self.state_counts: Counter = Counter()
        self.records: list[dict] = []
        self.skipped = Counter()

    def issue(self, severity: str, record_id: str | None, path: str, code: str, message: str):
        row = {"record_id": record_id, "path": path, "code": code, "message": message}
        (self.errors if severity == "error" else self.warnings).append(row)

    def field(self, record: dict, record_id: str, path: str, *, required: bool = True, value_type=None):
        item = get(record, path)
        if not isinstance(item, dict):
            if required:
                self.issue("error", record_id, path, "field_shape", "Expected field object with value/state/evidence_refs/note.")
            return None
        state = item.get("state")
        if state not in STATES:
            self.issue("error", record_id, path + ".state", "invalid_state", f"Expected one of {sorted(STATES)}.")
        else:
            self.state_counts[f"{path}:{state}"] += 1
        value = item.get("value")
        if state == "verified" and value is None:
            self.issue("error", record_id, path + ".value", "verified_without_value", "Verified fields need a value (use [] for verified empty lists).")
        if state in {"missing", "illegible", "not_declared", "not_applicable"} and value is not None:
            self.issue("error", record_id, path + ".value", "value_for_empty_state", f"State {state} requires null value.")
        if value_type and value is not None and not isinstance(value, value_type):
            self.issue("error", record_id, path + ".value", "invalid_type", f"Expected {value_type}, got {type(value).__name__}.")
        refs = item.get("evidence_refs", [])
        if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
            self.issue("error", record_id, path + ".evidence_refs", "invalid_type", "Expected a list of evidence ID strings.")
        elif state == "verified" and not refs:
            self.issue("error", record_id, path + ".evidence_refs", "verified_without_evidence", "Verified fields need at least one evidence reference.")
        return item

    def validate_record(self, rec: dict):
        rid = rec.get("record_id") if isinstance(rec.get("record_id"), str) else None
        for key in ("schema_version", "record_type", "record_id", "dataset_version", "taxonomy_version",
                    "identity", "label", "evidence", "verification", "review", "revision"):
            if key not in rec:
                self.issue("error", rid, key, "required", "Required top-level field is absent.")
        if rec.get("schema_version") != "1.0":
            self.issue("error", rid, "schema_version", "unsupported_version", "Expected schema version 1.0.")
        if rec.get("record_type") not in RECORD_TYPES:
            self.issue("error", rid, "record_type", "invalid_record_type", f"Expected one of {sorted(RECORD_TYPES)}.")
        if rec.get("record_type") == "annotation" and not rid:
            self.issue("error", rid, "record_id", "missing_record_id", "Annotation records need a stable ID.")
        if not isinstance(rec.get("dataset_version"), str) or not rec.get("dataset_version"):
            self.issue("error", rid, "dataset_version", "invalid_type", "Expected nonempty string.")
        if not isinstance(rec.get("taxonomy_version"), str) or not rec.get("taxonomy_version"):
            self.issue("error", rid, "taxonomy_version", "invalid_type", "Expected nonempty string.")
        elif rec.get("taxonomy_version") != "india-packaged-food-v1":
            self.issue("error", rid, "taxonomy_version", "unsupported_taxonomy", "Validator currently supports india-packaged-food-v1 only.")

        identity_fields = {
            "identity.product_name": str,
            "identity.brand.name": str,
            "identity.family.name": str,
            "identity.variant.name": str,
            "identity.variant.flavour": str,
            "identity.variant.formulation": str,
            "identity.pack.gtin": str,
            "identity.category": str,
        }
        for path, typ in identity_fields.items():
            self.field(rec, rid or "", path, value_type=typ)
        for path in ("identity.brand.brand_id", "identity.family.family_id", "identity.variant.variant_id", "identity.pack.pack_id"):
            v = get(rec, path)
            if v is not None and (not isinstance(v, str) or not v.strip()):
                self.issue("error", rid, path, "invalid_id", "ID must be a nonempty string or null.")

        cat_field = get(rec, "identity.category")
        if isinstance(cat_field, dict) and cat_field.get("state") == "verified" and cat_field.get("value") not in TAXONOMY:
            self.issue("error", rid, "identity.category.value", "unknown_category", f"Not in india-packaged-food-v1 taxonomy: {cat_field.get('value')!r}.")

        qty = self.field(rec, rid or "", "identity.pack.declared_quantity")
        if isinstance(qty, dict) and qty.get("state") == "verified":
            val = qty.get("value")
            if not isinstance(val, dict):
                self.issue("error", rid, "identity.pack.declared_quantity.value", "invalid_quantity", "Expected original/amount/unit object.")
            else:
                amount, unit = val.get("amount"), val.get("unit")
                if amount is not None and (isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0):
                    self.issue("error", rid, "identity.pack.declared_quantity.value.amount", "invalid_quantity", "Quantity amount must be positive numeric.")
                if unit is not None and unit not in PACK_UNITS:
                    self.issue("error", rid, "identity.pack.declared_quantity.value.unit", "invalid_unit", f"Unsupported unit {unit!r}.")
                if amount is not None and not unit:
                    self.issue("error", rid, "identity.pack.declared_quantity.value.unit", "unit_required", "A numeric quantity needs its original unit.")
        mp = self.field(rec, rid or "", "identity.pack.multipack_count", required=False)
        if isinstance(mp, dict) and mp.get("state") == "verified":
            v = mp.get("value")
            if isinstance(v, bool) or not isinstance(v, int) or v < 1:
                self.issue("error", rid, "identity.pack.multipack_count.value", "invalid_count", "Multipack count must be a positive integer.")

        barcode = get(rec, "identity.pack.gtin", {})
        if isinstance(barcode, dict) and barcode.get("state") == "verified":
            raw = barcode.get("value")
            digits = re.sub(r"[ -]", "", raw) if isinstance(raw, str) else ""
            if not digits.isdigit() or len(digits) not in GTIN_LENGTHS:
                self.issue("error", rid, "identity.pack.gtin.value", "invalid_gtin_format", "GTIN must contain 8, 12, 13 or 14 digits (preserve leading zeroes).")
            elif not gtin_check_digit_ok(digits):
                self.issue("warning", rid, "identity.pack.gtin.value", "gtin_check_digit", "GTIN check digit does not validate; review against package evidence.")

        label_paths = {
            "label.ingredients_original": str,
            "label.nutrition.basis": str,
            "label.nutrition.panel_source_text": str,
            "label.serving.servings_per_pack": (int, float),
            "label.claims": list,
            "label.allergens.contains": list,
            "label.allergens.precautionary": list,
            "label.allergens.other_text": str,
        }
        for path, typ in label_paths.items():
            self.field(rec, rid or "", path, value_type=typ)
        serving = self.field(rec, rid or "", "label.serving.size")
        if isinstance(serving, dict) and serving.get("state") == "verified":
            sv = serving.get("value")
            if not isinstance(sv, dict) or not isinstance(sv.get("amount"), (int, float)) or sv.get("amount", 0) <= 0 or sv.get("unit") not in PACK_UNITS:
                self.issue("error", rid, "label.serving.size.value", "invalid_serving", "Expected positive amount and supported original unit.")

        basis = get(rec, "label.nutrition.basis")
        basis_value = basis.get("value") if isinstance(basis, dict) else None
        if isinstance(basis, dict) and basis.get("state") == "verified" and basis_value not in BASES:
            self.issue("error", rid, "label.nutrition.basis.value", "invalid_basis", f"Expected one of {sorted(BASES)}.")
        nutrients = get(rec, "label.nutrition.nutrients", {})
        norm_bases = set()
        if not isinstance(nutrients, dict):
            self.issue("error", rid, "label.nutrition.nutrients", "invalid_type", "Expected nutrient object keyed by canonical nutrient name.")
        else:
            absent_nutrients = sorted(set(NUTRIENT_UNITS) - set(nutrients))
            if absent_nutrients:
                self.issue("error", rid, "label.nutrition.nutrients", "nutrient_states_missing",
                           f"Include explicit value/state objects for every canonical nutrient; absent keys: {absent_nutrients}.")
            for nutrient, detail in nutrients.items():
                p = f"label.nutrition.nutrients.{nutrient}"
                if nutrient not in NUTRIENT_UNITS:
                    self.issue("error", rid, p, "unknown_nutrient", "Unknown canonical nutrient key.")
                    continue
                if not isinstance(detail, dict):
                    self.issue("error", rid, p, "invalid_type", "Expected nutrient object.")
                    continue
                original = detail.get("original_value")
                normalized = detail.get("normalized_value")
                self.field(rec, rid or "", p + ".original_value", value_type=(str, int, float))
                self.field(rec, rid or "", p + ".normalized_value", required=False, value_type=(int, float))
                for attr in ("original_unit", "normalized_unit"):
                    if detail.get(attr) is not None and not isinstance(detail.get(attr), str):
                        self.issue("error", rid, p + "." + attr, "invalid_type", "Expected string or null.")
                original_unit = detail.get("original_unit")
                if isinstance(original, dict) and original.get("state") == "verified":
                    allowed_original_units = {"kcal", "kj", "g", "mg", "µg", "mcg", "ml", "l", "%", ""}
                    if not isinstance(original_unit, str) or original_unit.casefold() not in {u.casefold() for u in allowed_original_units}:
                        self.issue("error", rid, p + ".original_unit", "invalid_original_unit", "Use the original printed unit (kcal/kJ/g/mg/µg/ml/L/%); do not normalize this field.")
                if isinstance(normalized, dict) and normalized.get("state") == "verified":
                    nval = normalized.get("value")
                    if isinstance(nval, bool) or not isinstance(nval, (int, float)) or nval < 0:
                        self.issue("error", rid, p + ".normalized_value.value", "invalid_numeric", "Normalized nutrient must be nonnegative numeric.")
                    unit = detail.get("normalized_unit")
                    if unit != NUTRIENT_UNITS[nutrient]:
                        self.issue("error", rid, p + ".normalized_unit", "invalid_nutrient_unit", f"Expected {NUTRIENT_UNITS[nutrient]}.")
                    nb = detail.get("normalized_basis")
                    if nb not in {"per_100g", "per_100ml"}:
                        self.issue("error", rid, p + ".normalized_basis", "invalid_normalized_basis", "Normalized value must state per_100g or per_100ml.")
                    else:
                        norm_bases.add(nb)
                    if original is None or original.get("state") != "verified":
                        self.issue("warning", rid, p + ".original_value", "normalized_without_original", "Normalized value has no verified original label value.")
        if len(norm_bases) > 1:
            self.issue("error", rid, "label.nutrition.nutrients", "mixed_normalized_basis", "Normalized nutrients mix per_100g and per_100ml bases.")
        if norm_bases and (not isinstance(basis, dict) or basis.get("state") != "verified"):
            self.issue("error", rid, "label.nutrition.basis", "normalized_without_verified_basis", "Normalized nutrients require a verified original panel basis.")
        if basis_value == "per_100g" and norm_bases and norm_bases != {"per_100g"}:
            self.issue("error", rid, "label.nutrition", "basis_mismatch", "Normalized nutrient basis conflicts with panel basis.")
        if basis_value == "per_100ml" and norm_bases and norm_bases != {"per_100ml"}:
            self.issue("error", rid, "label.nutrition", "basis_mismatch", "Normalized nutrient basis conflicts with panel basis.")

        normalized_ingredients = get(rec, "label.ingredients_normalized", [])
        if not isinstance(normalized_ingredients, list):
            self.issue("error", rid, "label.ingredients_normalized", "invalid_type", "Expected ordered list.")
        else:
            for i, item in enumerate(normalized_ingredients):
                p = f"label.ingredients_normalized[{i}]"
                if not isinstance(item, dict):
                    self.issue("error", rid, p, "invalid_type", "Expected ingredient object.")
                    continue
                if not isinstance(item.get("sequence"), int) or item.get("sequence") != i + 1:
                    self.issue("error", rid, p + ".sequence", "ingredient_order", "Sequence must be consecutive, starting at 1.")
                if not isinstance(item.get("original_text"), str) or not item.get("original_text").strip():
                    self.issue("error", rid, p + ".original_text", "required", "Original ingredient mention is required.")
                if item.get("state") not in STATES:
                    self.issue("error", rid, p + ".state", "invalid_state", f"Expected one of {sorted(STATES)}.")
                if item.get("state") == "verified" and (not item.get("canonical_name") or not item.get("canonical_id")):
                    self.issue("error", rid, p, "canonical_required", "Verified normalization requires canonical name and ID.")
                if item.get("state") == "requires_review" and item.get("canonical_id"):
                    self.issue("warning", rid, p, "unresolved_canonical", "Review-state ingredient has a proposed canonical ID; do not use as gold until adjudicated.")

        # Evidence IDs, source/license provenance, reviewer state.
        evidence = rec.get("evidence") if isinstance(rec.get("evidence"), dict) else {}
        sources, packages = evidence.get("source_records", []), evidence.get("package_items", [])
        if not isinstance(sources, list):
            self.issue("error", rid, "evidence.source_records", "invalid_type", "Expected list.")
            sources = []
        if not isinstance(packages, list):
            self.issue("error", rid, "evidence.package_items", "invalid_type", "Expected list.")
            packages = []
        evidence_ids, source_ids = set(), set()
        if rec.get("record_type") == "annotation" and not sources:
            self.issue("error", rid, "evidence.source_records", "source_provenance_required", "Annotation records need at least one source record, including manual package evidence when no external record exists.")
        for i, src in enumerate(sources):
            p = f"evidence.source_records[{i}]"
            if not isinstance(src, dict):
                self.issue("error", rid, p, "invalid_type", "Expected source record object.")
                continue
            for req in ("source_name", "external_id", "license", "attribution", "snapshot_or_retrieved_at", "source_role"):
                if not isinstance(src.get(req), str) or not src[req].strip():
                    self.issue("error", rid, p + "." + req, "required", "Source provenance field must be a nonempty string; use 'unknown' when genuinely unknown.")
            if src.get("source_role") not in {"primary", "derivative", "crowdsourced", "other"}:
                self.issue("error", rid, p + ".source_role", "invalid_source_role", "Expected primary, derivative, crowdsourced or other.")
            sid = src.get("source_record_id")
            if isinstance(sid, str):
                source_ids.add(sid)
                evidence_ids.add(sid)
        for i, ev in enumerate(packages):
            p = f"evidence.package_items[{i}]"
            if not isinstance(ev, dict):
                self.issue("error", rid, p, "invalid_type", "Expected package evidence object.")
                continue
            eid = ev.get("evidence_id")
            if not isinstance(eid, str) or not eid:
                self.issue("error", rid, p + ".evidence_id", "required", "Stable evidence ID is required.")
            else:
                evidence_ids.add(eid)
            for req in ("kind", "reference", "captured_at", "license_or_permission", "fields_supported"):
                if req not in ev or ev[req] in (None, ""):
                    self.issue("error", rid, p + "." + req, "required", "Package evidence provenance is required.")
            if "fields_supported" in ev and not isinstance(ev["fields_supported"], list):
                self.issue("error", rid, p + ".fields_supported", "invalid_type", "Expected a list of field paths.")
            captured_at = ev.get("captured_at")
            if captured_at:
                try:
                    datetime.fromisoformat(str(captured_at).replace("Z", "+00:00"))
                except ValueError:
                    self.issue("error", rid, p + ".captured_at", "invalid_timestamp", "Expected ISO 8601 timestamp with timezone.")
        # Verify that every verified scalar cites an evidence or source ID.
        evidence_paths = (list(identity_fields) + ["identity.pack.declared_quantity", "identity.pack.multipack_count"]
                          + list(label_paths) + ["label.serving.size"])
        for nutrient in nutrients if isinstance(nutrients, dict) else {}:
            evidence_paths.extend([f"label.nutrition.nutrients.{nutrient}.original_value",
                                   f"label.nutrition.nutrients.{nutrient}.normalized_value"])
        for path in evidence_paths:
            fld = get(rec, path)
            if isinstance(fld, dict) and fld.get("state") == "verified":
                refs = fld.get("evidence_refs", [])
                for ref in refs if isinstance(refs, list) else []:
                    if ref not in evidence_ids:
                        self.issue("error", rid, path + ".evidence_refs", "unknown_evidence_ref", f"Evidence reference {ref!r} is not declared.")

        vstatus = get(rec, "verification.status")
        if vstatus not in VERIFICATION:
            self.issue("error", rid, "verification.status", "invalid_verification_status", f"Expected one of {sorted(VERIFICATION)}.")
        if vstatus == "verified":
            reviewer = get(rec, "review.primary_reviewer_id")
            reviewed_at = get(rec, "review.primary_reviewed_at")
            if not reviewer or not reviewed_at:
                self.issue("error", rid, "review", "verified_without_reviewer", "Verified record needs reviewer ID and review timestamp.")
            if reviewer and not isinstance(reviewer, str):
                self.issue("error", rid, "review.primary_reviewer_id", "invalid_type", "Reviewer ID must be an approved stable string ID.")
            if reviewed_at:
                try:
                    datetime.fromisoformat(str(reviewed_at).replace("Z", "+00:00"))
                except ValueError:
                    self.issue("error", rid, "review.primary_reviewed_at", "invalid_timestamp", "Expected ISO 8601 timestamp with timezone.")
            if not packages:
                self.issue("error", rid, "evidence.package_items", "verified_without_package_evidence", "Verified record needs package/manufacturer evidence.")

        revision = rec.get("revision", {})
        if not isinstance(revision, dict) or not isinstance(revision.get("number"), int) or revision.get("number", 0) < 1:
            self.issue("error", rid, "revision.number", "invalid_revision", "Revision number must be a positive integer.")

    def cross_record_checks(self):
        seen_ids, by_gtin, by_identity = {}, defaultdict(list), defaultdict(list)
        for rec in self.records:
            rid = rec.get("record_id")
            if rid in seen_ids:
                self.issue("error", rid, "record_id", "duplicate_record_id", f"Record ID already appears on line {seen_ids[rid]}.")
            else:
                seen_ids[rid] = rec.get("_line", 0)
            gtin = get(rec, "identity.pack.gtin.value")
            if isinstance(gtin, str) and gtin:
                by_gtin[re.sub(r"[ -]", "", gtin)].append(rec)
            keys = [normalized_text(get(rec, p + ".value")) for p in ("identity.brand.name", "identity.product_name", "identity.variant.name")]
            qty = get(rec, "identity.pack.declared_quantity.value", {})
            if isinstance(qty, dict):
                qkey = (str(qty.get("amount")), normalized_text(qty.get("unit")))
            else:
                qkey = ("", "")
            if all(keys):
                by_identity[tuple(keys) + qkey].append(rec)
        for gtin, rows in by_gtin.items():
            if len(rows) > 1:
                ids = [x.get("record_id") for x in rows]
                for rec in rows:
                    self.issue("warning", rec.get("record_id"), "identity.pack.gtin", "duplicate_gtin_candidate",
                               f"GTIN {gtin} occurs in records {ids}; inspect identity/source lineage, do not auto-merge.")
        for key, rows in by_identity.items():
            if len(rows) > 1:
                ids = [x.get("record_id") for x in rows]
                for rec in rows:
                    self.issue("warning", rec.get("record_id"), "identity", "duplicate_variant_candidate",
                               f"Exact normalized brand/name/variant/quantity match in records {ids}; adjudicate manually.")

        # Conservative fuzzy candidates: same normalized brand, close name/variant and same or unknown quantity.
        annotated = [r for r in self.records if r.get("record_type") == "annotation"]
        for i, left in enumerate(annotated):
            lb = normalized_text(get(left, "identity.brand.name.value"))
            lname = normalized_text(get(left, "identity.product_name.value"))
            lvar = normalized_text(get(left, "identity.variant.name.value"))
            lq = get(left, "identity.pack.declared_quantity.value") or {}
            for right in annotated[i + 1:]:
                if lb != normalized_text(get(right, "identity.brand.name.value")) or not lb:
                    continue
                rname = normalized_text(get(right, "identity.product_name.value"))
                rvar = normalized_text(get(right, "identity.variant.name.value"))
                rq = get(right, "identity.pack.declared_quantity.value") or {}
                if lq.get("amount") and rq.get("amount") and (lq.get("amount"), lq.get("unit")) != (rq.get("amount"), rq.get("unit")):
                    continue
                sim = max(SequenceMatcher(None, lname, rname).ratio(), SequenceMatcher(None, lvar, rvar).ratio())
                if 0.90 <= sim < 1.0:
                    for rec in (left, right):
                        self.issue("warning", rec.get("record_id"), "identity", "near_duplicate_candidate",
                                   f"Possible same-brand close-name candidate with {right.get('record_id') if rec is left else left.get('record_id')} (similarity {sim:.2f}); manual review only.")


def validate_file(path: Path, include_examples: bool = False) -> dict:
    v = Validator()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return {"status": "error", "errors": [{"code": "file_error", "message": str(exc)}], "warnings": []}
    for line_no, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            v.issue("error", None, f"line:{line_no}", "invalid_json", str(exc))
            continue
        if not isinstance(rec, dict):
            v.issue("error", None, f"line:{line_no}", "invalid_record", "Each JSONL line must be an object.")
            continue
        rec["_line"] = line_no
        kind = rec.get("record_type")
        if kind == "template":
            v.skipped["template"] += 1
            continue
        if kind == "synthetic_fixture" and not include_examples:
            v.skipped["synthetic_fixture"] += 1
            continue
        v.records.append(rec)
        v.validate_record(rec)
    v.cross_record_checks()
    counts = Counter(get(r, "identity.category.value") or "unassigned" for r in v.records)
    missingness = Counter()
    state_paths = ["identity.product_name", "identity.brand.name", "identity.family.name", "identity.variant.name",
                   "identity.variant.flavour", "identity.variant.formulation", "identity.pack.gtin",
                   "identity.pack.declared_quantity", "identity.pack.multipack_count", "identity.category",
                   "label.ingredients_original", "label.nutrition.basis", "label.serving.size", "label.claims",
                   "label.allergens.contains", "label.allergens.precautionary"]
    for rec in v.records:
        for p in state_paths:
            fld = get(rec, p)
            state = fld.get("state", "invalid") if isinstance(fld, dict) else "absent"
            missingness[f"{p}:{state}"] += 1
        for name in NUTRIENT_UNITS:
            fld = get(rec, f"label.nutrition.nutrients.{name}.original_value")
            state = fld.get("state", "absent") if isinstance(fld, dict) else "absent"
            missingness[f"label.nutrition.nutrients.{name}.original_value:{state}"] += 1
    return {
        "status": "ok" if not v.errors else "error",
        "file": str(path),
        "records_included": len(v.records),
        "records_skipped": dict(v.skipped),
        "category_distribution": dict(counts),
        "missingness_by_field_state": dict(missingness),
        "errors_count": len(v.errors),
        "warnings_count": len(v.warnings),
        "errors": v.errors,
        "warnings": v.warnings,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, help="Annotation JSONL; input is never modified")
    parser.add_argument("--include-examples", action="store_true", help="Validate synthetic_fixture records explicitly")
    parser.add_argument("--report", type=Path, help="Write JSON report to this path (default prints to stdout)")
    args = parser.parse_args(argv)
    result = validate_file(args.dataset, args.include_examples)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
