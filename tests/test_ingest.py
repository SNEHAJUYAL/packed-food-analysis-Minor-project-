"""Open Food Facts records map to the schema without inventing values."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.ingest import category_for, ingest_records, purge_synthetic, to_extraction
from database.models import Base, NutrientValue, ProductRow

# Shape of an OFF API v2 product (values made up for the test, not a real product)
OFF_RECORD = {"code": "0000000000001", "product_name": "Test Masala Noodles", "brands": "Test Brand, Other",
              "quantity": "70 g", "categories_tags": ["en:meals", "en:instant-noodles"],
              "nutriments": {"energy_100g": 1800, "proteins_100g": 9, "fat_100g": 15, "salt_100g": 2.5},
              "ingredients_text": "Wheat flour, palm oil, salt", "labels": "", "last_modified_t": 1700000000}


def test_off_mapping_keeps_units_and_gaps():
    ex = to_extraction(OFF_RECORD)
    assert ex["source"] == "open-food-facts" and ex["brand"] == "Test Brand"
    assert ex["nutrition"]["energy"] == "1800 kJ"     # converted later, labelled by build_product
    assert ex["nutrition"]["salt"] == "2.5 g" and "sodium" not in ex["nutrition"]
    assert "total_sugars" not in ex["nutrition"]       # missing stays missing
    assert ex["price"] is None                         # OFF has no prices; none are invented
    assert category_for(OFF_RECORD["categories_tags"]) == "instant_noodles"
    assert category_for(["en:soups"]) is None


def test_ingest_and_purge():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    with sessionmaker(bind=eng)() as s:
        synthetic = dict(OFF_RECORD, code="SYN-T-1", _synthetic=True, product_name="Sample Noodles T")
        stats = ingest_records(s, [OFF_RECORD, synthetic, {"code": "x", "categories_tags": ["en:soups"]}])
        assert stats["loaded"] == 2 and stats["skipped_no_category"] == 1 and stats["analysed"] == 2
        off = s.query(ProductRow).filter_by(external_product_id="off:0000000000001").one()
        assert off.barcode == "0000000000001" and off.sources[0].source_type == "open_food_facts"
        assert off.sources[0].source_url == "https://world.openfoodfacts.org/product/0000000000001"
        sodium = s.get(NutrientValue, (off.id, "sodium"))
        assert sodium.normalized_value == 1000 and sodium.evidence_status == "derived"  # 2.5 g salt / 2.5
        energy = s.get(NutrientValue, (off.id, "energy"))
        assert round(energy.normalized_value) == 430 and energy.original_value == "1800 kJ"
        assert s.get(NutrientValue, (off.id, "total_sugars")).normalized_value is None
        assert not off.prices
        assert purge_synthetic(s) == 1
        assert s.query(ProductRow).count() == 1
