"""Search, Open Food Facts import, micronutrients, prices and generic weights. No network: httpx is mocked."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import api.main as api_main
import catalog
from database.ingest import ingest_records, read_jsonl
from database.models import Base

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample" / "synthetic_products.jsonl"

OFF_PRODUCT = {
    "code": "8900000000017", "product_name": "Test Ragi Biscuits", "brands": "Test Brand",
    "quantity": "200 g", "categories_tags": ["en:biscuits"], "ingredients_text": "Ragi flour, sugar, palm oil, salt",
    "nutriscore_grade": "d", "image_front_url": "https://images.openfoodfacts.org/x.jpg",
    "nutriments": {"energy-kcal_100g": 480, "proteins_100g": 7, "carbohydrates_100g": 68, "sugars_100g": 22,
                   "fat_100g": 20, "saturated-fat_100g": 9, "fiber_100g": 4, "sodium_100g": 0.3,
                   "calcium_100g": 0.12, "iron_100g": 0.0035, "vitamin-d_100g": 0.0000025},
}
SPREAD = {"code": "8900000000024", "product_name": "Test Peanut Butter", "brands": "Test Brand",
          "quantity": "340 g", "categories_tags": ["en:spreads"], "ingredients_text": "Peanuts, salt",
          "nutriments": {"energy-kcal_100g": 600, "proteins_100g": 25, "sugars_100g": 5, "fat_100g": 50,
                         "saturated-fat_100g": 9, "fiber_100g": 7, "sodium_100g": 0.4}}


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.host == "search.openfoodfacts.org":
        return httpx.Response(200, json={"hits": [{"code": OFF_PRODUCT["code"], "product_name": "Test Ragi Biscuits",
                                                   "brands": ["Test Brand"], "nutriscore_grade": "d"}]})
    if request.url.path.endswith(f"{OFF_PRODUCT['code']}.json"):
        return httpx.Response(200, json={"status": 1, "product": OFF_PRODUCT})
    if request.url.path.endswith(f"{SPREAD['code']}.json"):
        return httpx.Response(200, json={"status": 1, "product": SPREAD})
    return httpx.Response(200, json={"status": 0})


@pytest.fixture(scope="module")
def client():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    factory = sessionmaker(bind=eng, expire_on_commit=False)
    with factory() as s:
        ingest_records(s, read_jsonl(SAMPLE))
        s.commit()
    mock = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(api_main, "session_factory", lambda *a, **k: factory)
        mp.setattr(api_main, "RATE_LIMIT", 1000)
        mp.setattr(catalog, "_client", lambda c: mock)
        catalog._search_cache.clear()
        yield TestClient(api_main.app)


def test_micronutrients_are_converted_and_missing_stays_missing():
    m = catalog.micronutrients_from(OFF_PRODUCT["nutriments"])
    assert m["calcium"]["value"] == 120.0 and m["calcium"]["unit"] == "mg"
    assert m["iron"]["value"] == 3.5
    assert m["vitamin-d"]["value"] == 2.5 and m["vitamin-d"]["unit"] == "µg"
    assert "zinc" not in m


def test_search_returns_online_results(client):
    r = client.get("/api/search", params={"q": "ragi biscuits"})
    assert r.status_code == 200
    body = r.json()
    assert body["online"][0]["barcode"] == OFF_PRODUCT["code"]
    assert body["online"][0]["stored"] is False


def test_search_needs_two_characters(client):
    assert client.get("/api/search", params={"q": "a"}).status_code == 422


def test_import_off_stores_minerals_and_scores(client):
    r = client.post("/api/products/import-off", json={"barcode": OFF_PRODUCT["code"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"]["source_type"] == "open_food_facts"
    assert body["extras"]["micronutrients"]["calcium"]["value"] == 120.0
    assert body["extras"]["image_url"].startswith("https://")
    assert body["report"]["overall"]["score"] is not None
    # now stored: search marks it
    found = client.get("/api/search", params={"q": "ragi biscuits"}).json()
    imported = next(x for x in found["stored"] if x["barcode"] == OFF_PRODUCT["code"])
    assert imported["source_url"].endswith(OFF_PRODUCT["code"])
    assert imported["image_url"].startswith("https://")


def test_import_unknown_barcode_is_404(client):
    r = client.post("/api/products/import-off", json={"barcode": "1234567890123"})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "not_found"


def test_product_outside_five_categories_gets_generic_weights(client):
    body = client.post("/api/products/import-off", json={"barcode": SPREAD["code"]}).json()
    nut = body["report"]["dimensions"]["nutrition"]
    assert nut["weights"] == "generic"
    assert nut["score"] is not None
    assert any("generic equal weights" in e for e in nut["explanation"])


def test_prices_history_cheapest_and_change(client):
    pid = client.post("/api/products/import-off", json={"barcode": OFF_PRODUCT["code"]}).json()["product_id"]
    empty = client.get(f"/api/products/{pid}/prices").json()
    assert empty["observations"] == [] and any("No price recorded" in n for n in empty["notes"])
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    assert client.post(f"/api/products/{pid}/prices",
                       json={"retailer": "blinkit", "price_inr": 40, "observed_at": old}).status_code == 200
    client.post(f"/api/products/{pid}/prices", json={"retailer": "blinkit", "price_inr": 45})
    out = client.post(f"/api/products/{pid}/prices",
                      json={"retailer": "zepto", "price_inr": 42, "place": "110001"}).json()
    blinkit = next(r for r in out["retailers"] if r["retailer"] == "blinkit")
    assert blinkit["observations"] == 2 and blinkit["trend"] == "up" and blinkit["change_inr"] == 5
    assert out["cheapest"] == "Zepto"
    assert out["spread"]["difference_per_100"] == 1.5  # 22.5 vs 21.0 per 100 g
    assert all(o["evidence"] == "hand" for o in out["observations"])
    # value for money now uses the latest price
    report = client.get(f"/api/products/{pid}").json()["report"]
    assert report["dimensions"]["value"]["price_per_100"] is not None


def test_price_validation(client):
    pid = client.post("/api/products/import-off", json={"barcode": OFF_PRODUCT["code"]}).json()["product_id"]
    assert client.post(f"/api/products/{pid}/prices", json={"retailer": "nowhere", "price_inr": 10}).status_code == 422
    future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    assert client.post(f"/api/products/{pid}/prices",
                       json={"retailer": "zepto", "price_inr": 10, "observed_at": future}).status_code == 422
    assert client.post("/api/products/99999/prices", json={"retailer": "zepto", "price_inr": 10}).status_code == 404


def test_synthetic_products_refuse_real_prices_and_are_labelled(client):
    products = client.get("/api/products", params={"q": "Sample"}).json()["products"]
    syn = next(p for p in products if p["is_synthetic"])
    summary = client.get(f"/api/products/{syn['product_id']}/prices").json()
    assert summary["is_synthetic"] is True
    assert all(o["evidence"] == "synthetic" for o in summary["observations"])
    r = client.post(f"/api/products/{syn['product_id']}/prices", json={"retailer": "zepto", "price_inr": 10})
    assert r.status_code == 422
