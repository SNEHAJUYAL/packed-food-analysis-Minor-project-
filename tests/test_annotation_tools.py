"""Tooling tests use only explicitly synthetic, temporary records; no product facts are asserted."""
from __future__ import annotations

import json

from scripts.create_grouped_splits import SplitError, create_manifest, leakage_audit
from scripts.validate_annotation_dataset import gtin_check_digit_ok, validate_file


def field(value=None, state="missing"):
    return {"value": value, "state": state, "evidence_refs": [], "note": "Synthetic tooling fixture; not package evidence."}


def synthetic_record(index: int, brand: int, family: int, variant: int | None = None, name: str | None = None):
    variant = family if variant is None else variant
    nutrient_missing = {"value": None, "state": "missing", "evidence_refs": [], "note": None}
    nutrients = {key: {"original_value": dict(nutrient_missing), "normalized_value": dict(nutrient_missing),
                       "original_unit": None, "normalized_unit": None, "normalized_basis": None}
                 for key in ("energy", "protein", "carbohydrate", "total_sugars", "added_sugars", "total_fat",
                             "saturated_fat", "trans_fat", "fibre", "sodium", "salt")}
    return {
        "schema_version": "1.0",
        "record_type": "synthetic_fixture",
        "record_id": f"SYNTHETIC_FIXTURE_{index:03d}",
        "dataset_version": "test-only",
        "taxonomy_version": "india-packaged-food-v1",
        "identity": {
            "product_name": field(name, state="requires_review" if name else "missing"),
            "brand": {"name": field(), "brand_id": f"brand:test-{brand}"},
            "family": {"name": field(), "family_id": f"family:test-{family}"},
            "variant": {"name": field(), "flavour": field(state="not_applicable"),
                        "formulation": field(state="not_applicable"), "variant_id": f"variant:test-{variant}"},
            "pack": {"pack_id": None, "gtin": field(),
                     "declared_quantity": field(),
                     "multipack_count": field(state="not_applicable")},
            "category": field(),
        },
        "label": {
            "ingredients_original": field(), "ingredients_normalized": [],
            "nutrition": {"basis": field(), "panel_source_text": field(), "nutrients": nutrients},
            "serving": {"size": field(), "servings_per_pack": field()},
            "claims": field(),
            "allergens": {"contains": field(), "precautionary": field(), "other_text": field()},
        },
        "evidence": {"source_records": [], "package_items": []},
        "verification": {"status": "unverified", "notes": "Synthetic tooling fixture only."},
        "review": {"primary_reviewer_id": None, "primary_reviewed_at": None, "second_reviewer_id": None,
                   "second_reviewed_at": None, "disagreements": [], "adjudication": None, "log_refs": []},
        "revision": {"number": 1, "previous_record_sha256": None, "change_reason": "Synthetic tooling fixture only."},
    }


def write_jsonl(path, records):
    path.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")


def test_template_is_skipped_and_not_counted(tmp_path):
    path = tmp_path / "template.jsonl"
    template = json.loads((__import__("pathlib").Path(__file__).parents[1] / "data/annotation/annotation_template.jsonl").read_text())
    write_jsonl(path, [template])
    result = validate_file(path)
    assert result["status"] == "ok"
    assert result["records_included"] == 0
    assert result["records_skipped"] == {"template": 1}


def test_synthetic_fixture_validates_without_becoming_verified_data(tmp_path):
    path = tmp_path / "synthetic.jsonl"
    write_jsonl(path, [synthetic_record(1, 1, 1)])
    skipped = validate_file(path)
    included = validate_file(path, include_examples=True)
    assert skipped["records_included"] == 0
    assert included["status"] == "ok"
    assert included["records_included"] == 1
    assert included["warnings_count"] == 0


def test_family_and_brand_held_out_splits_are_repeatable_and_leak_free(tmp_path):
    path = tmp_path / "synthetic_groups.jsonl"
    rows = []
    index = 1
    for brand in range(1, 7):
        for family in range(1, 3):
            rows.append(synthetic_record(index, brand, brand * 10 + family, name=f"Synthetic name b{brand} family{family}"))
            index += 1
    write_jsonl(path, rows)
    family = create_manifest(path, seed=19, mode="family", include_synthetic=True)
    family_again = create_manifest(path, seed=19, mode="family", include_synthetic=True)
    brand = create_manifest(path, seed=19, mode="brand_held_out", include_synthetic=True)
    assert family["record_to_partition"] == family_again["record_to_partition"]
    assert family["leakage_audit"]["status"] == "pass"
    assert brand["leakage_audit"]["status"] == "pass"
    assert sum(brand["record_counts"].values()) == 12
    assert all(value > 0 for value in brand["record_counts"].values())


def test_group_leakage_audit_detects_family_crossing_partitions():
    a, b = synthetic_record(1, 1, 1), synthetic_record(2, 2, 1)
    result = leakage_audit([a, b], {a["record_id"]: "train", b["record_id"]: "test"}, "family")
    assert result["status"] == "fail"
    assert any(row["key_type"] == "family_id" for row in result["leaks"])


def test_gtin_check_digit_and_duplicate_candidates_are_reported_not_merged(tmp_path):
    assert gtin_check_digit_ok("036000291452")
    path = tmp_path / "duplicate_gtin.jsonl"
    a, b = synthetic_record(1, 1, 1), synthetic_record(2, 2, 2)
    for row in (a, b):
        row["identity"]["pack"]["gtin"] = {"value": "036000291452", "state": "verified",
                                            "evidence_refs": ["package-1"], "note": None}
        row["evidence"]["package_items"] = [{"evidence_id": "package-1", "kind": "synthetic_fixture",
                                              "reference": "test-only", "captured_at": "2026-01-01T00:00:00Z",
                                              "license_or_permission": "test-only",
                                              "fields_supported": ["identity.pack.gtin"]}]
    write_jsonl(path, [a, b])
    result = validate_file(path, include_examples=True)
    assert result["errors_count"] == 0
    assert sum(item["code"] == "duplicate_gtin_candidate" for item in result["warnings"]) == 2


def test_invalid_quantity_unit_is_rejected(tmp_path):
    path = tmp_path / "invalid_unit.jsonl"
    record = synthetic_record(1, 1, 1)
    record["identity"]["pack"]["declared_quantity"] = {
        "value": {"original": "12 blargs", "amount": 12, "unit": "blargs"},
        "state": "verified", "evidence_refs": ["package-1"], "note": None,
    }
    record["evidence"]["package_items"] = [{"evidence_id": "package-1", "kind": "synthetic_fixture",
                                               "reference": "test-only", "captured_at": "2026-01-01T00:00:00Z",
                                               "license_or_permission": "test-only",
                                               "fields_supported": ["identity.pack.declared_quantity"]}]
    write_jsonl(path, [record])
    result = validate_file(path, include_examples=True)
    assert result["status"] == "error"
    assert any(item["code"] == "invalid_unit" for item in result["errors"])


def test_split_refuses_too_few_independent_groups(tmp_path):
    path = tmp_path / "too_small.jsonl"
    write_jsonl(path, [synthetic_record(1, 1, 1), synthetic_record(2, 1, 1, variant=2)])
    try:
        create_manifest(path, include_synthetic=True)
    except SplitError as exc:
        assert "at least 3 independent" in str(exc)
    else:
        raise AssertionError("Expected insufficient groups to fail")
