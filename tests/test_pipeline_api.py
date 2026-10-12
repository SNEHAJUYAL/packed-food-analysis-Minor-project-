from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from api.main import app
from normalise.build import build_product
from normalise.matcher import best_match
from pipeline import analyse_html, extract_all
from recommend.ranker import compare
from recommend.similarity import similar

FIX = Path(__file__).parent / "fixtures"
client = TestClient(app)


def page(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def test_end_to_end_cereal_report():
    r = analyse_html(page("cereal_jsonld.html"), "https://example.test/cereal")
    p = r["product"]
    assert p["category"]["value"] == "breakfast_cereals" and p["category"]["label"] == "interpreted"
    n = r["dimensions"]["nutrition"]
    assert n["traffic_lights"] == {"total_sugars": "red", "saturated_fat": "yellow", "total_fat": "yellow",
                                   "sodium": "yellow", "fibre": "green"}
    assert set(n["detail"]["missing"]) == {"energy", "protein"}  # no sourced benchmark yet
    assert n["score"] is not None
    claim = r["dimensions"]["claims"]["claims"][0]
    assert claim["claim_id"] == "high_protein" and "6.8% of energy" in claim["facts"][0]
    assert r["dimensions"]["value"]["price_per_100"] == 48.0  # ₹180 / 375 g
    assert r["dimensions"]["value"]["score"] is None  # no comparison set
    assert r["overall"]["grade"] in "ABCDE"
    assert "value" in r["overall"]["missing"]
    assert r["fop_warning_simulation"]["status"] == "not simulated"
    assert "not a medical" in r["disclaimer"]


def test_compare_and_recommend():
    url = "https://example.test/"
    biscuit = build_product(extract_all(page("biscuit_html_only.html"), url), url)
    cheaper = biscuit.model_copy(deep=True)
    cheaper.name.value = "Other Cookies"
    cheaper.price_inr.value = 110
    cheaper.pack_size.value = 300
    out = compare([biscuit, cheaper])
    assert out["picks"]["lowest_price_per_100"]["name"] == "Other Cookies"
    assert "₹36.67" in out["picks"]["lowest_price_per_100"]["reason"]
    assert out["reports"][0]["dimensions"]["value"]["score"] is not None
    sims = similar(biscuit, [cheaper, biscuit])
    assert len(sims) == 2


def test_off_matcher_with_canned_candidates():
    cands = [{"code": "1", "product_name": "Masala Noodles", "brands": "Demo Brand"},
             {"code": "2", "product_name": "Butter Cookies", "brands": "Other"}]
    m = best_match("Demo Masala Instant Noodles", "Demo Brand", cands)
    assert m["code"] == "1"
    assert best_match("Choco Crunch", None, cands) is None


def test_api_endpoints():
    assert client.get("/health").json() == {"status": "ok"}
    meth = client.get("/methodology").json()
    assert meth["scoring"]["dimension_weights"]["nutrition"] == 0.40
    r = client.post("/analyse/html", json={"url": "https://example.test/b", "html": page("biscuit_html_only.html"),
                                           "category": "biscuits_cookies"})
    assert r.status_code == 200
    body = r.json()
    claims = {c["claim_id"]: c["status"] for c in body["dimensions"]["claims"]["claims"]}
    assert claims["no_added_sugar"] == "potential inconsistency for review"  # sugar is ingredient #2
    assert client.post("/analyse/html", json={"url": "x", "html": "", "category": "soup"}).status_code == 422


def test_api_product_with_partial_nutrition():
    body = {"category": {"value": "breakfast_cereals", "label": "declared", "source": "user"},
            "nutrition_basis": "per_100g",
            "nutrition": {"total_sugars": {"value": 28, "label": "declared"},
                          "saturated_fat": {"value": 5, "label": "declared"},
                          "sodium": {"value": 400, "label": "declared"},
                          "fibre": {"value": 4, "label": "declared"}}}
    r = client.post("/analyse/product", json=body)
    assert r.status_code == 200
    d = r.json()
    assert d["product"]["nutrition"]["protein"]["label"] == "unknown"
    assert d["dimensions"]["nutrition"]["score"] is not None
    assert client.post("/analyse/product", json={"nutrition": {"vitamin_x": {"value": 1}}}).status_code == 422
