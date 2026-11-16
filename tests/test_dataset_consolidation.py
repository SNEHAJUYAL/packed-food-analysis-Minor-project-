"""Synthetic-workbook tests only; no real dataset rows or package assertions are fixtures here."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from scripts.consolidate_product_datasets import category_candidate, consolidate


def make_workbook(path: Path, sheet_name: str, headers: list, records: list[list], title: str = "SYNTHETIC TEST WORKBOOK"):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append([title])
    ws.append(["SYNTHETIC FIXTURE ONLY — not real product evidence"])
    ws.append([])
    ws.append(headers)
    for row in records:
        ws.append(row)
    ws.append([])  # empty row must be ignored
    wb.save(path)


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_imports_two_sources_flags_duplicates_and_preserves_knorr_alignment(tmp_path):
    a = tmp_path / "misleading_indian_food_products.xlsx"
    b = tmp_path / "indian_packaged_food_annotation_records.xlsx"
    headers_a = ["Product Name", "Brand", "Category", "Front-of-Pack Claim", "Actual Ingredients / Reality",
                 "Primary Misleading Concern", "Regulatory / Scrutiny Status", None]
    make_workbook(a, "Misleading Food Claims", headers_a, [
        ["Maggi 2-Minute Noodles", "Nestlé India", "Instant Noodles", "Source of Iron", "source assertion",
         "unverified concern", "reported scrutiny", None],
        ["Knorr Classic Mixed Vegetable Soup", "Unilever", "Sauces & Condiments", None, "reported ingredients",
         "reported concern", "reported scrutiny", "Chef's Best / 100% Real Vegetables"],
        ["Haldiram's Nagpur Bhujia", "Haldiram's", "Biscuits & Snacks", "claim", "reported list", None, None, None],
    ])
    headers_b = ["Product Name", "Brand", "Category", "Front-of-Pack Claim", "Actual Ingredients / Reality"]
    make_workbook(b, "Dataset Annotation Records", headers_b, [
        ["Maggi 2-Minute Noodles", "Nestlé India", "Instant Noodles", "another source claim", "another source description"],
        ["Haldiram's Bhujia Sev", "Haldiram's", "Biscuits & Snacks", "claim", "description"],
        ["Everest Garam Masala", "Everest", "Spices", "claim", "description"],
    ])
    out = tmp_path / "output"
    result = consolidate([a, b], out, "2026-11-16T00:00:00Z")
    records = read_jsonl(out / "consolidated_annotation_candidates.jsonl")
    assert len(records) == 6
    assert result["candidate_records_total"] == 6
    assert result["annotation_validator"]["status"] == "ok"
    maggi = [r for r in records if r["identity"]["product_name"]["value"] == "Maggi 2-Minute Noodles"]
    assert len(maggi) == 2
    assert maggi[0]["duplicate_review"]["duplicate_status"] == "possible_duplicate"
    assert maggi[0]["duplicate_review"]["candidate_duplicate_group_id"] == maggi[1]["duplicate_review"]["candidate_duplicate_group_id"]
    assert all(r["verification"]["status"] == "unverified" for r in records)
    assert all(r["annotation_status"] == "pending_review" for r in records)
    assert all(s["snapshot_or_retrieved_at"] == "unknown" for r in records for s in r["evidence"]["source_records"])
    assert all(r["label"]["ingredients_original"]["state"] == "missing" for r in records)
    assert result["malformed_or_suspicious_count"] == 1
    knorr = next(r for r in records if "Knorr Classic" in (r["identity"]["product_name"]["value"] or ""))
    assert knorr["malformed_flags"]["alignment_suspected"] is True
    assert knorr["research_assertions"]["front_of_pack_marketing_claim"] is None
    assert knorr["source_fields"][-1]["original_value"] == "Chef's Best / 100% Real Vegetables"
    assert knorr["source_fields"][-1]["column_name"] == "column_8"
    assert "Chef's Best" not in str(knorr["research_assertions"]["front_of_pack_marketing_claim"])
    haldiram_rows = [r for r in records if "Haldiram's" in (r["identity"]["product_name"]["value"] or "")]
    assert len({r["identity"]["product_name"]["value"] for r in haldiram_rows}) == 2
    assert any(r["duplicate_review"]["duplicate_status"] == "distinct_variant" for r in haldiram_rows)
    assert result["claim_verification_queue_count"] == 6
    assert (out / "consolidated_product_candidates.xlsx").exists()
    assert (out / "duplicate_candidates.csv").exists()
    assert (out / "category_mapping_review.csv").exists()
    assert (out / "claim_verification_queue.csv").exists()


def test_missing_optional_fields_uncertain_category_and_repeatable_ids(tmp_path):
    workbook = tmp_path / "spices_only.xlsx"
    make_workbook(workbook, "Sheet1", ["Product Name", "Brand", "Category", "Verification Status"], [
        ["Synthetic Garam Masala Example", "Example Brand", "Spices", "Verified Misleading"],
    ])
    one, two = tmp_path / "out-one", tmp_path / "out-two"
    first = consolidate([workbook], one, "2026-11-16T00:00:00Z")
    second = consolidate([workbook], two, "2026-11-16T00:00:00Z")
    rec1 = read_jsonl(one / "consolidated_annotation_candidates.jsonl")[0]
    rec2 = read_jsonl(two / "consolidated_annotation_candidates.jsonl")[0]
    assert rec1["record_id"] == rec2["record_id"]
    assert rec1["identity"]["pack"]["gtin"]["state"] == "missing"
    assert rec1["identity"]["pack"]["declared_quantity"]["state"] == "missing"
    assert rec1["normalized_fields"]["candidate_category"] is None
    assert rec1["normalized_fields"]["category_mapping_status"] == "requires_review"
    assert rec1["research_assertions"]["source_claimed_verification_status"] == "Verified Misleading"
    assert rec1["research_assertions"]["pipeline_verification_status"] == "unverified"
    assert first["uncertain_category_mapping_count"] == second["uncertain_category_mapping_count"] == 1
    with pytest.raises(FileExistsError):
        consolidate([workbook], one, "2026-11-16T00:00:00Z")


def test_photo_checklist_is_joined_as_supplemental_provenance_not_duplicate_product(tmp_path):
    workbook = tmp_path / "master.xlsx"
    wb = Workbook()
    products = wb.active
    products.title = "Verified Research Corpus"
    products.append(["title"])
    products.append([])
    products.append([])
    products.append(["Product ID", "Product Name", "Brand", "Category", "Front-of-Pack Claim"])
    products.append(["PRD-001", "Synthetic Biscuit Example", "Example Brand", "Biscuits & Snacks", "claim text"])
    check = wb.create_sheet("Data Collection Checklist")
    check.append(["title"])
    check.append([])
    check.append([])
    check.append(["Product ID", "Product Name", "Brand", "Front Photo", "Back/Ingredients Photo"])
    check.append(["PRD-001", "Synthetic Biscuit Example", "Example Brand", "Pending", "Pending"])
    wb.save(workbook)
    out = tmp_path / "out"
    summary = consolidate([workbook], out, "2026-11-16T00:00:00Z")
    records = read_jsonl(out / "consolidated_annotation_candidates.jsonl")
    assert len(records) == 1
    assert summary["inputs"][0]["supplemental_rows_linked"] == 1
    assert len(records[0]["source_locations"]) == 2
    assert records[0]["evidence"]["package_items"] == []


def test_output_candidate_csv_contains_original_and_normalized_data(tmp_path):
    workbook = tmp_path / "whitespace.xlsx"
    make_workbook(workbook, "Sheet1", ["Product Name", "Brand", "Category", "Research Notes"], [
        ["  Synthetic   Example  ", " Example  Brand ", "Spices", "source note remains exact"],
    ])
    out = tmp_path / "out"
    consolidate([workbook], out, "2026-11-16T00:00:00Z")
    with (out / "consolidated_product_candidates.csv").open(encoding="utf-8-sig", newline="") as f:
        row = next(csv.DictReader(f))
    fields = json.loads(row["source_fields_json"])
    assert row["normalized_product_name"] == "Synthetic Example"
    assert row["original_product_name"] == "  Synthetic   Example  "
    assert fields[0]["original_value"] == "  Synthetic   Example  "
    assert fields[3]["original_value"] == "source note remains exact"


@pytest.mark.parametrize(("category", "name", "expected", "status"), [
    ("Biscuits & Cookies", "Digestive Delight", "biscuits_cookies", "mapped_requires_review"),
    ("Biscuits & Snacks", "Mixed Savoury Bites", None, "requires_review"),
    ("Biscuits & Snacks", "Haldiram Aloo Bhujia", "namkeen", "mapped_requires_review"),
    ("Spices", "Garam Masala", None, "requires_review"),
])
def test_conservative_category_candidates(category, name, expected, status):
    mapped, actual_status, _ = category_candidate(category, name)
    assert (mapped, actual_status) == (expected, status)


def test_source_fingerprint_stable_and_changed_rows_reported_without_mutating_prior(tmp_path):
    workbook = tmp_path / "fingerprint.xlsx"
    headers = ["Product Name", "Brand", "Category"]
    row = ["Synthetic Example", "Example Brand", "Spices", None, None, None, None, None, "initial trailing cell"]
    make_workbook(workbook, "Sheet1", headers, [row])
    first_dir, repeat_dir, changed_dir = (tmp_path / x for x in ("first", "repeat", "changed"))
    first = consolidate([workbook], first_dir, "2026-11-16T00:00:00Z")
    first_jsonl = first_dir / first["outputs"]["jsonl"]
    before = first_jsonl.read_bytes()
    original = read_jsonl(first_jsonl)[0]
    fingerprint = original["source_row_fingerprint"]
    assert len(fingerprint) == 64
    assert len(original["source_fields"]) == 9
    assert original["source_fields"][-1]["column_name"] == "column_9"
    assert original["source_fields"][-1]["original_header"] is None
    assert original["source_fields"][-1]["original_value"] == "initial trailing cell"
    with (first_dir / "consolidated_product_candidates.csv").open(encoding="utf-8-sig", newline="") as f:
        flattened = next(csv.DictReader(f))
    assert json.loads(flattened["source_fields_json"])[-1]["original_value"] == "initial trailing cell"
    from openpyxl import load_workbook as read_workbook
    review = read_workbook(first_dir / "consolidated_product_candidates.xlsx", read_only=True)
    review_sheet = review["Candidates"]
    review_headers = [cell.value for cell in next(review_sheet.iter_rows(min_row=1, max_row=1))]
    review_values = [cell.value for cell in next(review_sheet.iter_rows(min_row=2, max_row=2))]
    review_fields = json.loads(review_values[review_headers.index("source_fields_json")])
    assert review_fields[-1]["original_value"] == "initial trailing cell"

    second = consolidate([workbook], repeat_dir, "2026-11-16T00:00:00Z")
    unchanged = read_jsonl(repeat_dir / second["outputs"]["jsonl"])[0]
    assert unchanged["record_id"] == original["record_id"]
    assert unchanged["source_row_fingerprint"] == fingerprint

    from openpyxl import load_workbook
    wb = load_workbook(workbook)
    wb["Sheet1"]["I5"] = "changed trailing cell"
    wb.save(workbook)
    third = consolidate([workbook], changed_dir, "2026-11-16T00:00:00Z", compare_to=first_jsonl)
    changed = read_jsonl(changed_dir / third["outputs"]["jsonl"])[0]
    assert changed["record_id"] == original["record_id"]
    assert changed["source_row_fingerprint"] != fingerprint
    assert third["source_row_change_count"] == 1
    with (changed_dir / third["outputs"]["source_row_changes"]).open(encoding="utf-8-sig", newline="") as f:
        report = list(csv.DictReader(f))
    assert report[0]["candidate_record_id"] == original["record_id"]
    assert report[0]["previous_fingerprint"] == fingerprint
    assert first_jsonl.read_bytes() == before

    manifest = json.loads((changed_dir / "import_manifest.json").read_text())
    assert manifest["outputs"]["validation_report"] == "annotation_validation_report.json"
    assert (changed_dir / manifest["outputs"]["validation_report"]).is_file()
