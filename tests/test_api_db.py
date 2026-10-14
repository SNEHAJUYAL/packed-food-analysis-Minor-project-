"""API endpoints backed by the database: ingestion, URL analysis, products, compare, alternatives, errors.

Runs against TEST_DATABASE_URL (PostgreSQL, migrated with Alembic) when set, otherwise against an
in-memory SQLite database created from the same models. Pages come from tests/fixtures; no network.
"""
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import api.main as api_main
import services
from database import repository as repo
from database.ingest import ingest_records, read_jsonl, to_extraction
from extract.fetch import validate_url
from database.models import Base, NutrientValue, ProductRow, Recommendation, RegulatoryRule

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).parent / "fixtures"
SAMPLE = ROOT / "data" / "sample" / "synthetic_products.jsonl"


@pytest.fixture(scope="module")
def engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        from alembic import command
        from alembic.config import Config
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        eng = create_engine(url)
        with eng.begin() as c:
            c.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
        cfg = Config(str(ROOT / "alembic.ini"))
        cfg.set_main_option("script_location", str(ROOT / "migrations"))
        cfg.attributes["url"] = url
        command.upgrade(cfg, "head")
    else:
        eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(eng)
    Session = sessionmaker(bind=eng, expire_on_commit=False)
    with Session() as s:
        ingest_records(s, read_jsonl(SAMPLE))
        s.commit()
    return eng


@pytest.fixture(scope="module")
def client(engine):
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    pages = {f"https://shop.example/{p.stem}": p.read_text(encoding="utf-8") for p in FIX.glob("*.html")}
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(api_main, "session_factory", lambda *a, **k: factory)
        mp.setattr(api_main, "RATE_LIMIT", 1000)
        mp.setattr(services, "fetch", lambda url, use_cache=True: pages[url])
        # shop.example resolves to a public address; everything else goes through the real checks
        mp.setattr(services, "validate_url", lambda url: validate_url(url, lambda host: ["93.184.216.34"]))
        yield TestClient(api_main.app)


def test_sample_is_labelled_synthetic():
    recs = read_jsonl(SAMPLE)
    assert len(recs) == 40
    assert all(r["_synthetic"] and r["code"].startswith("SYN-") and r["product_name"].startswith("Sample ")
               for r in recs)
    assert to_extraction(recs[0])["source"] == "synthetic-sample"


def test_health_and_reference(client):
    h = client.get("/api/health").json()
    assert h["database"] == "ok" and h["product_count"] >= 40
    cats = client.get("/api/reference/categories").json()["categories"]
    assert {c["id"] for c in cats} == {"biscuits_cookies", "breakfast_cereals", "instant_noodles", "beverages",
                                       "namkeen_chips"}
    m = client.get("/api/reference/methodology").json()
    assert m["version"] == "0.1.0" and m["dimension_weights"]["nutrition"] == 0.40
    assert all(r["source_url"].startswith("https://www.fssai.gov.in/") for r in m["claim_rules"])
    assert set(m["evidence_labels"]) == {"declared", "derived", "interpreted", "verified", "unknown"}
    assert len(m["claim_statuses"]) == 4


def test_analyze_url_stores_traceable_record(client, engine):
    r = client.post("/api/analyze-url", json={"url": "https://shop.example/cereal_jsonld"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["is_synthetic"] is False and d["source"]["source_type"] == "url"
    assert d["source"]["extraction_method"] == "json-ld+html"
    steps = [s["step"] for s in d["extraction_log"]]
    assert steps[:4] == ["fetch", "json-ld", "html", "llm-fallback"]
    assert "added_sugars" in d["missing_fields"]
    rep = d["report"]
    assert rep["product"]["nutrition"]["added_sugars"] == {"value": None, "label": "unknown", "source": None,
                                                           "note": None}
    assert rep["dimensions"]["value"]["peer_count"] == 8  # scored against the stored cereals
    assert rep["dimensions"]["value"]["score"] is not None
    claim = rep["dimensions"]["claims"]["claims"][0]
    assert claim["status"] == "potential inconsistency for review" and claim["missing_information"]
    pid = d["product_id"]
    Session = sessionmaker(bind=engine)
    with Session() as s:
        nv = s.get(NutrientValue, (pid, "added_sugars"))
        assert nv.normalized_value is None and nv.evidence_status == "unknown"  # missing stays NULL
        sugar = s.get(NutrientValue, (pid, "total_sugars"))
        assert sugar.normalized_value == 28 and sugar.original_value == "28 g" and sugar.source == "json-ld"
        row = s.get(ProductRow, pid)
        assert [i.sequence for i in row.ingredients] == [1, 2, 3, 4, 5, 6]
        assert row.ingredients[0].declared_percent == 62
        assert row.prices[-1].price_per_100g_or_ml == 48.0
        assert row.claims[0].applicable_rule_id is not None


def test_get_product_matches_stored_and_is_deterministic(client):
    pid = client.post("/api/analyze-url", json={"url": "https://shop.example/biscuit_html_only"}).json()["product_id"]
    a = client.get(f"/api/products/{pid}").json()
    b = client.get(f"/api/products/{pid}").json()
    assert a["report"]["overall"] == b["report"]["overall"]
    assert client.get("/api/products/999999").json()["detail"]["code"] == "not_found"


def test_per_serving_panel_is_partial_and_derived(client):
    d = client.post("/api/analyze-url", json={"url": "https://shop.example/noodles_per_serving"}).json()
    assert d["status"] in ("partial", "complete")
    sodium = d["report"]["product"]["nutrition"]["sodium"]
    assert sodium["label"] == "derived"
    assert d["report"]["product"]["nutrition_original"]["sodium"]["basis_text"]


def test_unstructured_page_returns_insufficient_data(client):
    d = client.post("/api/analyze-url", json={"url": "https://shop.example/beverage_unstructured"}).json()
    assert d["status"] == "insufficient_data" and d["report"]["overall"]["score"] is None
    llm = next(s for s in d["extraction_log"] if s["step"] == "llm-fallback")
    assert llm["outcome"] == "skipped"


@pytest.mark.parametrize("url,code", [
    ("http://169.254.169.254/latest/meta-data/", "blocked_destination"),
    ("http://127.0.0.1/admin", "blocked_destination"),
    ("file:///etc/passwd", "blocked_destination"),
    ("not a url at all", "invalid_url"),
])
def test_analyze_url_refuses_unsafe_destinations(client, url, code):
    r = client.post("/api/analyze-url", json={"url": url})
    assert r.status_code in (400, 422)
    assert r.json()["detail"]["code"] == code


def test_validation_errors_have_one_shape(client):
    r = client.post("/api/analyze-url", json={"url": "https://shop.example/x", "category": "soup"})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "validation_error"
    big = client.post("/api/analyze-url", content=b"x" * 70000, headers={"content-type": "application/json"})
    assert big.status_code == 413


def test_list_products_filters(client):
    d = client.get("/api/products", params={"category": "beverages"}).json()
    assert d["total"] >= 8 and all(p["category"] == "beverages" for p in d["products"])
    assert all(p["is_synthetic"] for p in d["products"] if p["source_type"] == "synthetic_sample")


def test_alternatives_come_from_stored_records(client, engine):
    pid = client.post("/api/analyze-url", json={"url": "https://shop.example/cereal_jsonld"}).json()["product_id"]
    stored = {p["product_id"] for p in client.get("/api/products", params={"category": "breakfast_cereals",
                                                                           "limit": 500}).json()["products"]}
    for pref in ("balanced", "nutrition", "price", "transparency"):
        d = client.get(f"/api/products/{pid}/alternatives", params={"preference": pref}).json()
        assert d["preference"] == pref
        assert d["alternatives"] or d["message"]
        for a in d["alternatives"]:
            assert a["product_id"] in stored and a["product_id"] != pid
            assert a["rationale"] and "same category (breakfast cereals)" in a["matching_attributes"]
        if pref == "price":
            assert all(a["price_per_100"] < 48.0 for a in d["alternatives"])
    with sessionmaker(bind=engine)() as s:
        assert s.scalars(select(Recommendation).where(Recommendation.source_product_id == pid)).first()
    assert client.get(f"/api/products/{pid}/alternatives", params={"preference": "cheap"}).status_code == 422


def test_best_product_gets_no_fake_alternative(client):
    prods = client.get("/api/products", params={"category": "breakfast_cereals", "limit": 500}).json()["products"]
    top = max((p for p in prods if p["overall"] is not None), key=lambda p: p["overall"])
    d = client.get(f"/api/products/{top['product_id']}/alternatives").json()
    assert d["alternatives"] == [] and "No stored product" in d["message"]


def test_compare(client):
    prods = client.get("/api/products", params={"category": "biscuits_cookies"}).json()["products"][:3]
    ids = [p["product_id"] for p in prods]
    d = client.post("/api/products/compare", json={"product_ids": ids}).json()
    assert [p["product_id"] for p in d["products"]] == ids
    assert d["basis"] == "per_100g" and set(d["ingredient_differences"]["only_in"]) == {str(i) for i in ids}
    assert d["picks"]["best_nutrition"]["product_id"] in ids
    other = client.get("/api/products", params={"category": "beverages"}).json()["products"][0]["product_id"]
    bad = client.post("/api/products/compare", json={"product_ids": [ids[0], other]})
    assert bad.status_code == 422 and "one category" in bad.json()["detail"]["message"]
    assert client.post("/api/products/compare", json={"product_ids": [ids[0]]}).status_code == 422


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(api_main, "RATE_LIMIT", 1)
    api_main._hits.clear()
    first = client.post("/api/analyze-url", json={"url": "https://shop.example/cereal_jsonld"})
    second = client.post("/api/analyze-url", json={"url": "https://shop.example/cereal_jsonld"})
    assert first.status_code == 200 and second.status_code == 429
    assert second.json()["detail"]["code"] == "rate_limited"
    api_main._hits.clear()


def test_constraints_reject_bad_rows(engine):
    Session = sessionmaker(bind=engine)
    with Session() as s:
        pid = s.scalars(select(ProductRow.id)).first()
        s.add(NutrientValue(product_id=pid, nutrient_name="fake_unknown", normalized_value=0.0,
                            normalized_unit="g", basis="per_100g", evidence_status="unknown"))
        with pytest.raises(IntegrityError):
            s.flush()  # an unknown value must be NULL, never zero
        s.rollback()


def test_rules_seeded(engine):
    with sessionmaker(bind=engine)() as s:
        rules = s.scalars(select(RegulatoryRule)).all()
        assert len(rules) == 18 and all(r.jurisdiction == "IN" and r.source_url for r in rules)
        hp = next(r for r in rules if r.rule_key == "high_protein")
        assert hp.criteria["threshold_solid"] == 10.8 and "energy (kcal) per 100 g/ml" in hp.required_fields
