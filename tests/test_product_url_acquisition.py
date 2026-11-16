"""Offline synthetic tests for policy-gated product URL candidates."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

from acquisition.models import AcquisitionContext
from acquisition.product_url import ProductURLExtractionService
from acquisition.registry import SourceRegistration, SourceRegistry
from extract.fetch import FetchError, fetch_page

FIX = Path(__file__).parent / "fixtures"
OFF_URL = "https://world.openfoodfacts.org/product/0000000000000/synthetic-product"


def _jsonld_page(*, image="https://images.example.test/synthetic.webp", pack="200 g",
                 name="SYNTHETIC Oat Bites"):
    return f'''<!doctype html><html><head><script type="application/ld+json">
    {{"@context":"https://schema.org","@type":"Product","name":"{name}",
     "brand":{{"@type":"Brand","name":"SYNTHETIC Grain Co"}},"category":"Biscuits",
     "description":"Synthetic fixture only", "image":"{image}","gtin13":"0000000000000",
     "weight":"{pack}","ingredients":"Synthetic oats, sugar",
     "allergens":"Contains synthetic wheat", "additionalProperty":[
       {{"@type":"PropertyValue","name":"Flavour","value":"Synthetic cocoa"}},
       {{"@type":"PropertyValue","name":"Multipack count","value":"2"}}],
     "nutrition":{{"@type":"NutritionInformation","servingSize":"100 g",
       "calories":"450 kcal","proteinContent":"12 g","sodiumContent":"300 mg"}},
     "offers":{{"@type":"Offer","price":"125.00","priceCurrency":"INR",
       "availability":"https://schema.org/InStock",
       "priceSpecification":{{"price":"150.00","priceCurrency":"INR",
       "priceType":"https://schema.org/ListPrice"}}}}}}
    </script></head><body><h1>{name}</h1></body></html>'''


class StaticFetcher:
    def __init__(self, html: str, final_url: str | None = None):
        self.html = html
        self.final_url = final_url
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.final_url or url, self.html


def _service(html: str, final_url: str | None = None):
    fetcher = StaticFetcher(html, final_url)
    return ProductURLExtractionService(fetch_page=fetcher), fetcher


def _context():
    return AcquisitionContext(run_id="synthetic-url-run",
                              started_at=datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc))


def test_jsonld_product_candidate_has_normalized_fields_provenance_and_images():
    service, fetcher = _service(_jsonld_page())
    result = service.acquire(OFF_URL, _context())
    assert result.status == "candidate"
    candidate = result.candidate
    assert candidate is not None
    assert candidate.normalized_product.name.value == "SYNTHETIC Oat Bites"
    assert candidate.normalized_product.brand.value == "SYNTHETIC Grain Co"
    assert candidate.normalized_product.pack_size.value == 200
    assert candidate.normalized_product.pack_unit.value == "g"
    assert candidate.normalized_product.multipack_count.value == 2
    assert candidate.normalized_product.price_inr.value == 125
    assert candidate.normalized_product.mrp_inr.value == 150
    assert candidate.normalized_product.availability.value == "instock"
    assert candidate.acquisition_record.product_identity.gtin.value == "0000000000000"
    assert candidate.acquisition_record.listing.retailer_name.value is None  # OFF is not a retailer.
    assert candidate.acquisition_record.observation.selling_price.value == 125
    assert candidate.acquisition_record.observation.mrp.value == 150
    assert candidate.acquisition_record.verification_status == "candidate"
    assert candidate.images[0].image_url == "https://images.example.test/synthetic.webp"
    assert candidate.images[0].product_association == "product_entity"
    assert candidate.images[0].validation_status == "url_syntax_valid_not_fetched"
    assert candidate.field_evidence
    name_evidence = next(e for e in candidate.field_evidence if e.field_path == "name")
    assert name_evidence.original_value == "SYNTHETIC Oat Bites"
    assert name_evidence.provenance.source_url == OFF_URL
    assert name_evidence.provenance.extraction_method == "json-ld"
    assert name_evidence.provenance.raw_value == "SYNTHETIC Oat Bites"
    assert fetcher.calls[0][1]["allowed_hosts"] == frozenset({"openfoodfacts.org"})


def test_html_fallback_extracts_candidate_fields_from_synthetic_fixture():
    service, _ = _service((FIX / "biscuit_html_only.html").read_text())
    result = service.acquire(OFF_URL, _context())
    assert result.status == "candidate"
    candidate = result.candidate
    assert candidate.normalized_product.name.value == "Sample Bakes Butter Cookies"
    assert candidate.normalized_product.ingredients_raw.value.startswith("Refined Wheat Flour")
    assert candidate.normalized_product.nutrition["energy"].value == 495
    assert candidate.normalized_product.price_inr.value == 120
    assert candidate.acquisition_record.product_identity.pack_quantity.value == 200
    assert any(e.field_path == "ingredients_text" for e in candidate.field_evidence)
    serving = next(e for e in candidate.field_evidence if e.field_path == "serving_size_text")
    assert serving.original_value == "25 g"
    allergens = next(e for e in candidate.field_evidence if e.field_path == "allergens_text")
    assert "Contains Wheat, Milk" in allergens.original_value
    assert "May contain Nuts" in allergens.original_value


def test_missing_attributes_remain_null_and_are_reported():
    service, _ = _service('<script type="application/ld+json">{"@context":"https://schema.org","@type":"Product","name":"SYNTHETIC Oat Squares"}</script>')
    result = service.acquire(OFF_URL, _context())
    candidate = result.candidate
    assert result.status == "candidate"
    assert candidate.normalized_product.name.value == "SYNTHETIC Oat Squares"
    assert candidate.normalized_product.brand.value is None
    assert candidate.acquisition_record.product_identity.gtin.value is None
    codes = {issue.code for issue in candidate.issues}
    assert {"missing_brand", "missing_ingredients"} <= codes


def test_invalid_url_and_unsupported_source_are_blocked_before_fetch_or_dns():
    fetcher = StaticFetcher(_jsonld_page())
    dns_calls = []
    service = ProductURLExtractionService(fetch_page=fetcher,
                                          resolver=lambda host: (dns_calls.append(host) or ["93.184.216.34"]))
    invalid = service.acquire("javascript:alert(1)", _context())
    unsupported = service.acquire("https://www.bigbasket.com/p/synthetic", _context())
    assert invalid.status == "invalid"
    assert unsupported.status == "blocked"
    assert unsupported.error_code == "unsupported_source"
    assert fetcher.calls == []
    assert dns_calls == []


def test_denied_source_registration_blocks_before_fetch():
    registry = SourceRegistry([SourceRegistration(
        source_id="denied_fixture", source_type="user_submitted_url", enabled=True,
        authorization_status="denied", authorization_evidence="synthetic denied fixture",
        network_acquisition=True, allowed_domains=frozenset({"denied.example.test"}),
    )])
    fetcher = StaticFetcher(_jsonld_page())
    service = ProductURLExtractionService(registry=registry, fetch_page=fetcher)
    result = service.acquire("https://denied.example.test/product/1", _context())
    assert result.status == "blocked"
    assert result.error_code == "unsupported_source"
    assert fetcher.calls == []


def test_supported_host_resolving_to_private_destination_is_blocked_without_http():
    requests = []
    client = httpx.Client(transport=httpx.MockTransport(
        lambda request: (requests.append(request) or httpx.Response(200, text="fixture"))))
    service = ProductURLExtractionService(client=client,
                                          resolver=lambda host: ["10.0.0.4"])
    result = service.acquire(OFF_URL, _context())
    assert result.status == "blocked"
    assert result.error_code == "blocked_destination"
    assert requests == []
    client.close()


def test_missing_product_image_is_retained_as_missing():
    service, _ = _service(_jsonld_page(image="javascript:alert(1)"))
    result = service.acquire(OFF_URL, _context())
    assert result.status == "candidate"
    assert result.candidate.images == []
    assert any(issue.code == "invalid_image_url" for issue in result.issues)


def test_absent_product_image_stays_empty():
    service, _ = _service(_jsonld_page(image=""))
    candidate = service.acquire(OFF_URL, _context()).candidate
    assert candidate.images == []
    assert candidate.acquisition_record.listing.image_refs == []
    assert any(issue.field_path == "image_url" and issue.code == "missing_extracted_field"
               for issue in candidate.issues)


def test_conflicting_pack_sizes_are_retained_and_flagged():
    page = _jsonld_page(pack="200 g").replace(
        "</body>", "<p>Net Weight: 250 g</p></body>")
    service, _ = _service(page)
    result = service.acquire(OFF_URL, _context())
    assert result.candidate.normalized_product.conflict_flag
    assert any(issue.code in {"conflicting_product_data", "conflicting_identity_attribute"}
               and "pack" in issue.message.lower() for issue in result.issues)
    pack_evidence = [e for e in result.candidate.field_evidence if e.field_path == "pack_size_text"]
    assert {e.original_value for e in pack_evidence} >= {"200 g", "250 g"}


def test_nutrition_evidence_keeps_original_units_and_normalized_values():
    service, _ = _service(_jsonld_page())
    candidate = service.acquire(OFF_URL, _context()).candidate
    evidence = next(e for e in candidate.field_evidence if e.field_path == "nutrition.sodium")
    assert evidence.original_value == "300 mg"
    assert evidence.normalized_value == 300
    assert evidence.provenance.raw_value == "300 mg"


def test_ambiguous_nutrition_unit_is_preserved_but_not_normalized():
    page = _jsonld_page().replace('"proteinContent":"12 g"', '"proteinContent":"12 scoops"')
    service, _ = _service(page)
    candidate = service.acquire(OFF_URL, _context()).candidate
    evidence = next(e for e in candidate.field_evidence if e.field_path == "nutrition.protein")
    assert evidence.original_value == "12 scoops"
    assert evidence.normalized_value is None
    assert evidence.validation_status == "invalid"
    assert any(issue.code == "invalid_nutrition_unit" for issue in candidate.issues)


def test_unstated_price_currency_is_not_normalized_as_inr():
    page = _jsonld_page().replace('"priceCurrency":"INR",', '')
    service, _ = _service(page)
    candidate = service.acquire(OFF_URL, _context()).candidate
    assert candidate.normalized_product.price_inr.value is None
    assert candidate.acquisition_record.observation.selling_price.value == 125
    assert candidate.acquisition_record.observation.currency is None
    assert any(issue.code == "price_currency_unconfirmed" for issue in candidate.issues)
    assert any(issue.code == "missing_currency" for issue in candidate.issues)


def test_multiple_distinct_product_entities_are_reported_not_exactly_matched():
    page = _jsonld_page().replace("</head>", f"<script type='application/ld+json'>{_jsonld_page(name='SYNTHETIC Different Product').split('<script type=\"application/ld+json\">',1)[1].split('</script>',1)[0]}</script></head>")
    service, _ = _service(page)
    result = service.acquire(OFF_URL, _context())
    assert any(issue.code == "duplicate_product_candidates" for issue in result.issues)
    assert result.candidate.additional_product_candidates


def test_unknown_image_association_is_not_overstated():
    page = '<meta property="og:image" content="https://cdn.unrelated.example.test/generic.jpg"><h1>Synthetic page title</h1>'
    service, _ = _service(page)
    result = service.acquire(OFF_URL, _context())
    image = result.candidate.images[0]
    assert image.product_association == "page_level_unverified"
    assert image.validation_status == "requires_review"
    assert any(issue.code == "image_association_requires_review" for issue in result.issues)
