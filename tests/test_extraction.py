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


def test_image_metadata_is_extracted_and_normalised():
    jsonld = """
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Product","name":"Demo","image":"/images/demo.jpg"}
    </script>
    """
    ex = extract_jsonld(jsonld, "https://example.test/products/demo")
    assert ex["image_url"] == "https://example.test/images/demo.jpg"
    assert ex["image_source"] == "json-ld"

    html_ex = extract_html(
        '<meta property="og:image" content="/images/demo.png">'
        '<h1>Demo</h1>',
        "https://example.test/products/demo",
    )
    assert html_ex["image_url"] == "https://example.test/images/demo.png"
    assert html_ex["image_source"] == "open-graph"

    product = build_product([ex, html_ex], "https://example.test/products/demo")
    assert product.image_url.value == "https://example.test/images/demo.jpg"
    assert product.image_url.source == "json-ld"


def test_image_metadata_rejects_unsafe_schemes_and_credentials():
    from extract.image_validation import image_url_from_metadata

    assert image_url_from_metadata("javascript:alert(1)", "https://shop.example/item") is None
    assert image_url_from_metadata("http://cdn.example/item.jpg", "https://shop.example/item") is None
    assert image_url_from_metadata("https://user:pass@cdn.example/item.jpg", "https://shop.example/item") is None
    assert image_url_from_metadata("https://127.0.0.1/image.jpg", "https://shop.example/item") is None
    assert image_url_from_metadata("https://localhost/image.jpg", "https://shop.example/item") is None
    assert image_url_from_metadata("/images/item.webp", "https://shop.example/item") == \
        "https://shop.example/images/item.webp"


def test_image_mime_probe_uses_head_and_rejects_non_image(monkeypatch):
    from extract import fetch
    from extract import image_validation

    class Response:
        is_redirect = False
        status_code = 200
        headers = {"content-type": "image/webp"}

    class Client:
        def __init__(self, **kwargs):
            assert kwargs["follow_redirects"] is False

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def head(self, url):
            assert url.startswith("https://")
            return Response()

    monkeypatch.setattr(fetch, "validate_url", lambda url: url)
    monkeypatch.setattr(fetch, "_space_out", lambda host: None)
    monkeypatch.setattr(image_validation.httpx, "Client", Client)
    assert image_validation.probe_image_content_type("https://cdn.example/item.webp")
    Response.headers = {"content-type": "text/html"}
    assert not image_validation.probe_image_content_type("https://cdn.example/not-image")


def test_image_mime_probe_timeout_is_non_fatal(monkeypatch):
    from extract import fetch
    from extract import image_validation
    import httpx

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def head(self, url):
            raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(fetch, "validate_url", lambda url: url)
    monkeypatch.setattr(fetch, "_space_out", lambda host: None)
    monkeypatch.setattr(image_validation.httpx, "Client", Client)
    assert not image_validation.probe_image_content_type("https://cdn.example/slow.jpg")


def test_commercial_fields_are_normalised_without_fabricating_missing_values():
    raw = '''<script type="application/ld+json">
      {"@type":"Product","name":"Oat Bites","brand":{"@type":"Brand","name":"Grain Co"},
       "additionalProperty":[{"name":"Flavour","value":"Cocoa"}],
       "offers":{"@type":"Offer","price":"180","priceCurrency":"INR",
       "availability":"https://schema.org/InStock",
       "priceSpecification":{"price":"200","priceCurrency":"INR",
       "priceType":"https://schema.org/ListPrice"}},"weight":{"value":4,"unitText":"x 50 g"}}
    </script>'''
    extracted = extract_jsonld(raw, "https://www.blinkit.com/product")
    # Quantity is provided through the supported, explicit pack text form below.
    extracted["pack_size_text"] = "4 x 50 g"
    product = build_product([extracted], "https://www.blinkit.com/product")
    assert product.name.value == "Oat Bites"
    assert product.variant.value == "Cocoa"
    assert product.price_inr.value == 180
    assert product.mrp_inr.value == 200
    assert product.discount_percent.value == 10
    assert product.availability.value == "instock"
    assert product.pack_size.value == 200 and product.pack_unit.value == "g"
    assert product.multipack_count.value == 4
    assert product.retailer.value == "Blinkit"

    missing = build_product([{"source": "html", "name": "Plain item"}], "https://unknown.example/item")
    assert not missing.mrp_inr.known and not missing.availability.known
    assert not missing.multipack_count.known and not missing.retailer.known


def test_list_price_without_selling_price_is_not_duplicated_as_a_sale():
    extracted = extract_jsonld('''<script type="application/ld+json">
      {"@type":"Product","name":"Example","offers":{"@type":"Offer",
       "priceSpecification":{"price":"200","priceCurrency":"INR",
       "priceType":"https://schema.org/ListPrice"}}}
    </script>''', "https://www.bigbasket.com/item")
    product = build_product([extracted], "https://www.bigbasket.com/item")
    assert not product.price_inr.known
    assert product.mrp_inr.value == 200
    assert not product.discount_percent.known


def test_generic_retailer_heading_is_not_product_identity():
    ex = extract_html("<h1>Adding to Cart...</h1><title>Product details</title>",
                     "https://amazon.example/dp/demo")
    assert ex["name"] is None


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
