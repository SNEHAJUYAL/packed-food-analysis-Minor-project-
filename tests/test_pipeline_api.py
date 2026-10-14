from pathlib import Path

from normalise.build import build_product
from normalise.matcher import best_match
from pipeline import analyse_html, extract_all
from recommend.ranker import compare
from recommend.similarity import similar

FIX = Path(__file__).parent / "fixtures"


def page(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def test_end_to_end_cereal_report():
    r = analyse_html(page("cereal_jsonld.html"), "https://example.test/cereal")
    p = r["product"]
    assert p["category"]["value"] == "breakfast_cereals" and p["category"]["label"] == "interpreted"
    n = r["dimensions"]["nutrition"]
    assert n["traffic_lights"] == {"total_sugars": "red", "saturated_fat": "yellow", "total_fat": "yellow",
                                   "sodium": "yellow", "fibre": "green", "protein": "green"}
    assert n["detail"]["missing"] == ["energy"]  # no sourced benchmark yet
    assert n["score"] is not None
    claim = r["dimensions"]["claims"]["claims"][0]
    assert claim["claim_id"] == "high_protein" and claim["status"] == "potential inconsistency for review"
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
