"""Importing hand-recorded prices. Rows are made up for the test, not observed prices."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.ingest import ingest_records
from database.models import Base, PriceObservation
from database.prices import import_rows
from services import rescore_all

OFF_RECORD = {"code": "0000000000001", "product_name": "Test Masala Noodles", "brands": "Test Brand",
              "quantity": "70 g", "categories_tags": ["en:instant-noodles"],
              "nutriments": {"energy_100g": 1800, "proteins_100g": 9, "fat_100g": 15, "salt_100g": 2.5}}


def _row(**kw):
    base = {"off_code": "0000000000001", "platform": "zepto", "observed_at": "2026-10-17 10:30",
            "city_pincode": "Delhi 110058", "listing_pack_size": "4 x 70 g", "selling_price_inr": "₹56",
            "matches_product": "exact", "listing_url": "not a url"}
    return base | kw


def test_price_import_validates_and_computes_unit_price():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    with sessionmaker(bind=eng)() as s:
        ingest_records(s, [OFF_RECORD])
        rows = [_row(), _row(),  # second is a duplicate
                _row(platform="blinkit", selling_price_inr="", matches_product="exact"),
                _row(platform="blinkit", matches_product="different variant"),
                _row(platform="blinkit", observed_at=""),
                _row(platform="blinkit", listing_pack_size="family pack"),
                _row(platform="blinkit", off_code="999"),
                _row(platform="blinkit", listing_pack_size="70 g", selling_price_inr="15",
                     matches_product="different size", observed_at="2026-10-17")]
        stats = import_rows(s, rows)
        assert stats["imported"] == 2 and stats["already_stored"] == 1
        assert stats["skipped"] == {"no price recorded": 1, "listing not confirmed as the same product": 1,
                                    "no observation date": 1, "pack size missing or unreadable": 1,
                                    "product not in the database": 1}
        zepto = s.query(PriceObservation).filter(PriceObservation.source.like("zepto%")).one()
        assert zepto.pack_size == 280 and zepto.pack_unit == "g" and zepto.price_per_100g_or_ml == 20.0
        assert zepto.source == "zepto (Delhi 110058), recorded by hand" and zepto.source_url is None
        assert rescore_all(s) == 1
