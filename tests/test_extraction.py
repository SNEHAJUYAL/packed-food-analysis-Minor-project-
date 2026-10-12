from pathlib import Path

import pytest

from core.schema import EvidenceLabel
from extract.html_parser import extract_html, nutrient_key
from extract.jsonld import extract_jsonld
from normalise.build import build_product

FIX = Path(__file__).parent / "fixtures"


def html(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def test_jsonld_product_fields():
    ex = extract_jsonld(html("cereal_jsonld.html"), "https://example.test/cereal")
    assert ex["name"] == "Choco Crunch Whole Grain Cereal - High Protein"
    assert ex["brand"] == "Example Foods"
    assert ex["price"] == "180.00" and ex["currency"] == "INR"
    assert ex["pack_size_text"] == "375 g"
    assert ex["ingredients_text"].startswith("Whole Grain Wheat")
    assert ex["nutrition_basis_text"] == "100 g"
    assert ex["nutrition"]["total_sugars"] == "28 g"
    assert ex["nutrition"]["sodium"] == "400 mg"


def test_jsonld_graph_and_per_serving_scaling():
    url = "https://example.test/noodles"
    p = build_product([extract_jsonld(html("noodles_per_serving.html"), url)], url)
    assert p.pack_size.value == 280 and p.pack_unit.value == "g"
    assert p.price_inr.value == 56
    assert p.nutrition_basis == "per_100g"
    sugars = p.nutrition["total_sugars"]
    assert sugars.value == pytest.approx(2.0) and sugars.label == EvidenceLabel.DERIVED
    # 1290 kJ per 70 g -> 308.3 kcal per 70 g -> 440.4 kcal per 100 g
    assert p.nutrition["energy"].value == pytest.approx(1290 / 4.184 * 100 / 70, abs=0.01)
    # salt 2.1 g per 70 g -> 3 g per 100 g -> sodium 1200 mg
    assert p.nutrition["sodium"].value == pytest.approx(1200, abs=0.01)
    assert p.nutrition["sodium"].label == EvidenceLabel.DERIVED


def test_html_fallback_table_and_ingredients():
    ex = extract_html(html("biscuit_html_only.html"), "https://example.test/biscuit")
    assert ex["price"] == "120"
    assert ex["pack_size_text"] == "200 g"
    assert ex["nutrition_basis_text"] == "100 g"
    assert ex["nutrition"]["energy"] == "495 kcal"
    assert ex["nutrition"]["added_sugars"] == "22.0 g"
    assert ex["nutrition"]["total_sugars"] == "24.5 g"
    assert ex["nutrition"]["saturated_fat"] == "11.2 g"
    assert ex["ingredients_text"].startswith("Refined Wheat Flour")
    assert "No Added Sugar" in ex["claims_text"]


@pytest.mark.parametrize("label,key", [
    ("Energy (kcal)", "energy"), ("Total Sugars (g)", "total_sugars"), ("Added Sugars", "added_sugars"),
    ("of which saturated fat", "saturated_fat"), ("Saturated Fatty Acids", "saturated_fat"),
    ("Trans Fat", "trans_fat"), ("Total Fat", "total_fat"), ("Dietary Fibre", "fibre"),
    ("Sodium (mg)", "sodium"), ("Salt", "salt"), ("Vitamin C", None),
])
def test_nutrient_label_mapping(label, key):
    assert nutrient_key(label) == key


def test_missing_values_stay_missing_not_zero():
    url = "https://example.test/biscuit"
    p = build_product([extract_html(html("biscuit_html_only.html"), url)], url)
    assert p.nutrition["fibre"].value is None
    assert p.nutrition["fibre"].label == EvidenceLabel.UNKNOWN
    # Added and total sugars are kept separately.
    assert p.nutrition["added_sugars"].value == 22.0 and p.nutrition["total_sugars"].value == 24.5


def test_conflicting_sources_are_flagged():
    a = {"source": "json-ld", "price": "180", "nutrition": {"total_sugars": "28 g"}, "nutrition_basis_text": "100 g"}
    b = {"source": "html", "price": "175", "nutrition": {"total_sugars": "26 g"}, "nutrition_basis_text": "100 g"}
    p = build_product([a, b])
    assert p.conflict_flag
    assert p.price_inr.value == 180  # first source kept, disagreement listed
    assert any("price_inr" in c for c in p.conflicts) and any("total_sugars" in c for c in p.conflicts)


def test_panel_without_basis_is_not_used():
    p = build_product([{"source": "json-ld", "nutrition": {"total_sugars": "10 g"}}])
    assert p.nutrition_basis is None and p.nutrition["total_sugars"].value is None
    assert any("basis" in w for w in p.warnings)


def test_pack_size_is_removed_from_name():
    from normalise.build import build_product
    p = build_product([{"source": "html", "name": "Sample Bakes Butter Cookies 200 g", "pack_size_text": "200 g"}])
    assert p.name.value == "Sample Bakes Butter Cookies" and "pack size removed" in p.name.note
    assert build_product([{"source": "html", "name": "7 Grain Cereal"}]).name.value == "7 Grain Cereal"
