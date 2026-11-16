"""Synthetic workbook tests; all fixture products and prices are invented for testing only."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import Workbook, load_workbook

from acquisition.catalog_workbook import IMAGE_COLUMNS, import_catalog_workbook, parse_nutrition
from acquisition.models import AcquisitionContext


HEADERS = [
    "Product Submission ID", "Product name", "Brand name", "Product category",
    "Product variant/flavour", "Pack size", "Barcode number", "Ingredients (copy from pack)",
    "Nutritional information (per 100 g/ml)", "Marketing claims (exact wording)",
    "Paste or insert a link to the original photo file. Google Form file uploads are stored in Drive. Front packaging photo",
    "Back packaging photo", "Ingredient-label photo", "Nutrition-table photo", "Barcode photo",
    "Product source URL",
    "Indicative planning range only, not a verified live quote. Replace with app prices for the selected delivery pin code and date. Price range (₹, indicative)",
    "Blinkit price (₹)", "Zepto price (₹)", "Swiggy Instamart price (₹)", "Price checked date", "Photo/source notes",
]


def image_json(product_id, i, image_type):
    return json.dumps({"product_id": product_id, "pvid": f"SYNTHETIC-PVID-{product_id}",
                       "image_type": image_type, "image_index": i, "source_platform": "SYNTHETIC RETAILER",
                       "image_url": f"https://images.example.test/{product_id}/{i}.jpg",
                       "mime_type": "image/jpeg", "status": "synthetic_fixture"})


def make_source_workbook(path: Path, product_count=2):
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(HEADERS)
    products = [(f"SYN-FP{i:03}", "0000000000000" if i != 2 else "0000000000001")
                for i in range(1, product_count + 1)]
    for product_id, gtin in products:
        # All content is synthetic, including names, quantities, GTINs and prices.
        ws.append([
            product_id, f"SYNTHETIC TEST ITEM {product_id}", "SYNTHETIC BRAND", "Instant noodles",
            "Synthetic Masala", "280 g (4 x 70 g)", gtin, "Synthetic ingredients, salt",
            "Per 100 g: Energy 300 kcal, Protein 8 g, Total Fat 10 g, Sodium 400 mg",
            "Synthetic claim; another synthetic claim",
            image_json(product_id, 1, "front_packaging_photo"),
            image_json(product_id, 2, "back_packaging_photo"),
            image_json(product_id, 3, "ingredient_label_photo"),
            image_json(product_id, 4, "nutrition_table_photo"),
            image_json(product_id, 5, "barcode_photo"),
            ("https://www.zepto.com/p/synthetic-test" if product_id == "SYN-FP002"
             else f"https://retailer.example.test/product/{product_id}"), "₹1–₹2 synthetic planning range",
            1, 1.5, 2, datetime(2026, 11, 16), "Synthetic fixture only; not verified",
        ])
    summary = wb.create_sheet("Price & Category Summary")
    summary.append(["Synthetic summary title"])
    summary.append([])
    summary.append(["Category", "Count", "Synthetic average"])
    summary.append(["Instant noodles", "=COUNTIF(Sheet1!D:D,A4)", "=AVERAGE(Sheet1!R:R)"])
    wb.save(path)
    return path


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_import_preserves_both_sheets_images_prices_dates_and_candidates(tmp_path):
    source = make_source_workbook(tmp_path / "synthetic_catalog.xlsx")
    original_bytes = source.read_bytes()
    out = tmp_path / "candidate_release"
    context = AcquisitionContext(run_id="synthetic-import", started_at=datetime(2026, 11, 17, 10, 0, tzinfo=timezone.utc))
    report = import_catalog_workbook(source, out, context=context)

    annotations = read_jsonl(out / "candidate_annotations.jsonl")
    observations = read_jsonl(out / "acquisition_observations.jsonl")
    images = read_jsonl(out / "image_references.jsonl")
    rows = read_jsonl(out / "source_workbook_rows.jsonl")
    assert len(annotations) == 2
    assert [a["import_metadata"]["source_record_identifier"] for a in annotations] == ["SYN-FP001", "SYN-FP002"]
    assert all(a["annotation_status"] == "pending_review" and a["verification"]["status"] == "unverified" for a in annotations)
    assert len(observations) == 8  # one product listing and three price observations per product
    product_listings = [r for r in observations if r["observation"] is None]
    price_observations = [r for r in observations if r["observation"] is not None]
    assert len(product_listings) == 2
    assert len(price_observations) == 6
    assert report["acquisition_record_count"] == 8
    assert report["product_listing_record_count"] == 2
    assert report["price_observation_record_count"] == 6
    assert len(images) == 2 * len(IMAGE_COLUMNS) == 10
    assert report["worksheets_preserved"] == ["Price & Category Summary", "Sheet1"]
    assert len(rows) == 3 + 3  # product header/data rows plus nonempty summary rows

    first_images = [img for img in images if img["source_product_id"] == "SYN-FP001"]
    assert {img["pvid"] for img in first_images} == {"SYNTHETIC-PVID-SYN-FP001"}
    assert {img["source_platform"] for img in first_images} == {"SYNTHETIC RETAILER"}
    assert {img["image_type"] for img in first_images} == {kind for _, kind, _ in IMAGE_COLUMNS}
    assert {img["image_index"] for img in first_images} == {1, 2, 3, 4, 5}
    assert all(img["image_url"].startswith("https://images.example.test/") for img in first_images)

    fp1_observations = [r for r in price_observations if r["product_identity"]["source_product_id"]["value"] == "SYN-FP001"]
    assert {r["listing"]["retailer_name"]["value"] for r in fp1_observations} == {"Blinkit", "Zepto", "Swiggy Instamart"}
    blinkit = next(r for r in fp1_observations if r["listing"]["retailer_name"]["value"] == "Blinkit")
    instamart = next(r for r in fp1_observations if r["listing"]["retailer_name"]["value"] == "Swiggy Instamart")
    assert blinkit["listing"]["listing_url"]["value"] is None
    assert instamart["listing"]["listing_url"]["value"] is None
    assert blinkit["observation"]["observed_date"] == "2026-11-16"
    assert blinkit["observation"]["observed_at"] is None
    assert blinkit["observation"]["location"]["pin_code"] is None
    assert blinkit["verification_status"] == "candidate"
    fp1_listing = next(r for r in product_listings if r["product_identity"]["source_product_id"]["value"] == "SYN-FP001")
    fp2_listing = next(r for r in product_listings if r["product_identity"]["source_product_id"]["value"] == "SYN-FP002")
    assert fp1_listing["listing"]["retailer_name"]["value"] is None
    assert fp2_listing["listing"]["retailer_name"]["value"] == "Zepto"
    retailer_provenance = fp2_listing["listing"]["retailer_name"]["provenance"]
    source_url = fp2_listing["listing"]["listing_url"]["value"]
    assert retailer_provenance["input_locator"] == "Sheet1!row:3 / Product source URL"
    assert retailer_provenance["raw_value"] == source_url
    assert retailer_provenance["source_url"] == source_url
    assert fp2_listing["listing"]["listing_url"]["provenance"]["raw_value"] == source_url
    assert fp1_listing["listing"]["image_refs"][0]["source_platform"] == "SYNTHETIC RETAILER"
    source_date_cell = next(cell for row in rows if row["worksheet"] == "Sheet1" and row["row_number"] == 2
                            for cell in row["cells"] if cell["column_name"] == "Price checked date")
    assert source_date_cell["original_value"] == "2026-11-16"

    invalid_barcode = next(a for a in annotations if a["record_id"] != annotations[0]["record_id"])
    assert invalid_barcode["source_fields"][6]["original_value"] == "0000000000001"
    assert invalid_barcode["identity"]["pack"]["gtin"]["value"] == "0000000000001"
    text_barcode_record = next(r for r in observations if r["product_identity"]["source_product_id"]["value"] == "SYN-FP001")
    assert text_barcode_record["product_identity"]["gtin"]["value"] == "0000000000000"
    assert isinstance(text_barcode_record["product_identity"]["gtin"]["value"], str)
    assert report["barcode_validation"]["invalid_format_or_checksum"] == 1
    assert report["retailer_price_candidates"]["prices_are_verified"] is False
    assert report["individual_product_url_missing_count"] == {"Blinkit": 2, "Swiggy Instamart": 2}
    assert report["annotation_schema_validation"]["status"] == "ok"
    assert source.read_bytes() == original_bytes

    summary_formula = next(row for row in rows if row["worksheet"] == "Price & Category Summary" and row["row_number"] == 4)
    assert any(cell["is_formula"] and str(cell["original_value"]).startswith("=") for cell in summary_formula["cells"])


def test_import_refuses_to_overwrite_candidate_release(tmp_path):
    source = make_source_workbook(tmp_path / "synthetic_catalog.xlsx")
    out = tmp_path / "candidate_release"
    out.mkdir()
    (out / "keep.json").write_text("preserve", encoding="utf-8")
    try:
        import_catalog_workbook(source, out)
    except FileExistsError:
        pass
    else:
        raise AssertionError("nonempty candidate output directory should not be overwritten")
    assert (out / "keep.json").read_text(encoding="utf-8") == "preserve"


def test_invalid_image_json_is_reported_without_network_or_download(tmp_path):
    source = make_source_workbook(tmp_path / "synthetic_catalog.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(HEADERS)
    product_id = "SYN-IMAGE-ERROR"
    row = [product_id, "SYNTHETIC ITEM", "SYNTHETIC BRAND", "Instant noodles", "Synthetic", "100 g",
           "0000000000000", "synthetic ingredients", "Per 100 g: Energy 100 kcal", "synthetic claim"]
    row += [image_json(product_id, i, kind) for i, (_, kind, _) in enumerate(IMAGE_COLUMNS, 1)]
    row += ["https://retailer.example.test/synthetic", "indicative only", 10, 11, 12,
            datetime(2026, 11, 16), "synthetic"]
    row[11] = "{not-json"
    ws.append(row)
    wb.save(source)
    out = tmp_path / "release"
    report = import_catalog_workbook(source, out)
    assert report["issues_by_code"]["invalid_image_json"] == 1
    assert report["image_references"]["count"] == 4
    assert (out / "source_workbook_rows.jsonl").exists()


def test_twenty_five_products_persist_100_deterministic_acquisition_records(tmp_path):
    source = make_source_workbook(tmp_path / "synthetic_catalog_25.xlsx", product_count=25)
    first = tmp_path / "first_release"
    second = tmp_path / "second_release"
    report = import_catalog_workbook(source, first)
    import_catalog_workbook(source, second)
    records = read_jsonl(first / "acquisition_observations.jsonl")
    repeated = read_jsonl(second / "acquisition_observations.jsonl")
    ids = [record["record_id"] for record in records]
    assert len(records) == 100
    assert len(set(ids)) == 100
    assert ids == [record["record_id"] for record in repeated]
    assert report["product_listing_record_count"] == 25
    assert report["price_observation_record_count"] == 75
    manifest = json.loads((first / "import_manifest.json").read_text(encoding="utf-8"))
    assert manifest["product_listing_records"] == 25
    assert manifest["populated_unverified_price_observations"] == 75
    assert manifest["price_candidate_records"] == 75
    assert manifest["acquisition_record_count"] == 100


def test_repeated_submission_ids_keep_distinct_stable_row_record_ids(tmp_path):
    source = make_source_workbook(tmp_path / "synthetic_duplicate_ids.xlsx")
    wb = load_workbook(source)
    wb["Sheet1"]["A3"] = "SYN-FP001"
    wb.save(source)
    first, second = tmp_path / "dup_first", tmp_path / "dup_second"
    report = import_catalog_workbook(source, first)
    import_catalog_workbook(source, second)
    records = read_jsonl(first / "acquisition_observations.jsonl")
    repeated = read_jsonl(second / "acquisition_observations.jsonl")
    product_records = [record for record in records if record["observation"] is None]
    assert len({record["record_id"] for record in records}) == 8
    assert [record["record_id"] for record in records] == [record["record_id"] for record in repeated]
    assert [record["product_identity"]["source_product_id"]["value"] for record in product_records] == ["SYN-FP001", "SYN-FP001"]
    assert report["duplicate_source_product_ids"] == ["SYN-FP001"]


def test_missing_and_invalid_prices_remain_null_and_date_only(tmp_path):
    source = make_source_workbook(tmp_path / "synthetic_prices.xlsx", product_count=1)
    wb = load_workbook(source)
    ws = wb["Sheet1"]
    ws["R2"] = None
    ws["S2"] = "not a price"
    wb.save(source)
    out = tmp_path / "price_release"
    report = import_catalog_workbook(source, out)
    records = read_jsonl(out / "acquisition_observations.jsonl")
    prices = [record for record in records if record["observation"] is not None]
    assert len(records) == 4
    assert prices[0]["observation"]["selling_price"]["value"] is None
    assert prices[1]["observation"]["selling_price"]["value"] is None
    assert prices[0]["observation"]["observed_date"] == "2026-11-16"
    assert prices[0]["observation"]["observed_at"] is None
    assert report["retailer_price_candidates"]["by_retailer"]["Blinkit:missing"] == 1
    assert report["retailer_price_candidates"]["by_retailer"]["Zepto:invalid"] == 1
    assert report["price_observation_record_count"] == 1
    assert report["missing_price_placeholder_count"] == 1
    assert report["invalid_price_placeholder_count"] == 1
    assert report["retailer_price_candidates"]["populated_unverified_count"] == 1


def test_identical_issues_are_deduplicated_per_row_not_across_rows(tmp_path):
    source = make_source_workbook(tmp_path / "synthetic_same_issues.xlsx")
    wb = load_workbook(source)
    ws = wb["Sheet1"]
    ws["D2"] = "Unknown synthetic category"
    ws["D3"] = "Unknown synthetic category"
    ws["G2"] = "0000000000001"
    ws["G3"] = "0000000000001"
    wb.save(source)
    report = import_catalog_workbook(source, tmp_path / "issue_release")
    category_issues = [issue for issue in report["issues"] if issue["code"] == "category_unmapped"]
    gtin_issues = [issue for issue in report["issues"] if issue["code"] == "invalid_gtin"]
    assert len(category_issues) == 2
    assert {issue["record_id"] for issue in category_issues} == {"SYN-FP001", "SYN-FP002"}
    assert len({issue["source_row_id"] for issue in category_issues}) == 2
    # Each bad GTIN is validated on the product listing and all three retailer records,
    # but issue aggregation retains one matching validation message per source row.
    assert len(gtin_issues) == 2
    assert len({issue["product_record_identity"] for issue in gtin_issues}) == 2


def test_numeric_barcode_is_preserved_and_flagged_without_padding(tmp_path):
    source = make_source_workbook(tmp_path / "synthetic_numeric_barcode.xlsx", product_count=1)
    wb = load_workbook(source)
    ws = wb["Sheet1"]
    ws["G2"] = 1234567890123
    wb.save(source)
    out = tmp_path / "numeric_release"
    report = import_catalog_workbook(source, out)
    record = next(r for r in read_jsonl(out / "acquisition_observations.jsonl") if r["observation"] is None)
    annotation = read_jsonl(out / "candidate_annotations.jsonl")[0]
    source_row = next(r for r in read_jsonl(out / "source_workbook_rows.jsonl")
                      if r["worksheet"] == "Sheet1" and r["row_number"] == 2)
    assert record["product_identity"]["gtin"]["value"] == 1234567890123
    assert isinstance(record["product_identity"]["gtin"]["value"], int)
    assert annotation["identity"]["pack"]["gtin"]["value"] is None
    assert annotation["source_fields"][6]["original_value"] == 1234567890123
    assert annotation["candidate_source_metadata"]["barcode_original_cell"] == {
        "value": 1234567890123,
        "excel_value_type": "numeric",
        "gtin_candidate_created": False,
        "reason": "Numeric Excel cells cannot preserve or establish barcode text.",
    }
    assert next(cell for cell in source_row["cells"] if cell["column_name"] == "Barcode number")["original_value"] == 1234567890123
    assert report["barcode_validation"]["numeric_requires_review"] == 1
    assert report["barcode_validation"].get("checksum_valid_candidate_only", 0) == 0
    assert report["issues_by_code"]["numeric_barcode_requires_review"] == 1
    assert not str(record["product_identity"]["gtin"]["value"]).startswith("0")


def test_missing_product_url_does_not_infer_retailer_from_image_metadata(tmp_path):
    source = make_source_workbook(tmp_path / "synthetic_missing_url.xlsx", product_count=1)
    wb = load_workbook(source)
    wb["Sheet1"]["P2"] = None
    wb.save(source)
    out = tmp_path / "missing_url_release"
    import_catalog_workbook(source, out)
    records = read_jsonl(out / "acquisition_observations.jsonl")
    listing = next(record for record in records if record["observation"] is None)
    assert listing["listing"]["retailer_name"]["value"] is None
    assert listing["listing"]["retailer_name"]["provenance"] is None
    assert listing["listing"]["listing_url"]["value"] is None
    assert listing["listing"]["image_refs"][0]["source_platform"] == "SYNTHETIC RETAILER"


def test_nutrition_preserves_original_mg_g_kj_kcal_without_normalizing():
    parsed, basis, issues = parse_nutrition(
        "Per 100 g: Energy 850 kJ, Protein 1200 mg, Carbohydrate 12 g, Total Fat 3.5 g; Energy 203 kcal"
    )
    assert basis == "per_100g"
    assert parsed["energy"]["amount"] == "850"
    assert parsed["energy"]["original_unit"] == "kJ"
    assert parsed["protein"]["amount"] == "1200"
    assert parsed["protein"]["original_unit"] == "mg"
    assert parsed["carbohydrate"]["original_unit"] == "g"
    assert parsed["energy"]["normalized_value"] is None
    assert parsed["energy"]["normalized_unit"] is None
    assert parsed["protein"]["normalized_value"] is None
    assert parsed["protein"]["normalized_unit"] is None
    kcal_values, _, kcal_issues = parse_nutrition("Per 100 g: Energy 203 kcal")
    assert kcal_values["energy"]["amount"] == "203"
    assert kcal_values["energy"]["original_unit"] == "kcal"
    assert kcal_values["energy"]["normalized_value"] is None
    assert not kcal_issues
    assert not issues
