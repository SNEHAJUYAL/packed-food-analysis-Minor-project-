"""API surface tests for source-gated candidate extraction (network-free)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.main as api_main
from acquisition.product_url import ProductURLExtractionService
from extract.fetch import FetchBlocked, FetchError

FIX = Path(__file__).parent / "fixtures"


class SyntheticFetcher:
    def __init__(self):
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return url, (FIX / "cereal_jsonld.html").read_text(encoding="utf-8")


def test_candidate_endpoint_returns_structured_unverified_record(monkeypatch):
    service = ProductURLExtractionService(fetch_page=SyntheticFetcher())
    monkeypatch.setattr(api_main.repo, "save_product", lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("candidate preview must not persist products")))
    monkeypatch.setattr(api_main, "ProductURLExtractionService", lambda: service)
    monkeypatch.setattr(api_main, "RATE_LIMIT", 100)
    client = TestClient(api_main.app)
    response = client.post("/api/product-candidates/from-url", json={
        "url": "https://world.openfoodfacts.org/product/SYN-FIXTURE-001"
    })
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "candidate"
    assert result["candidate"]["status"] == "candidate"
    assert result["candidate"]["acquisition_record"]["verification_status"] == "candidate"
    assert result["candidate"]["normalized_product"]["name"]["value"] == \
        "Choco Crunch Whole Grain Cereal - High Protein"


def test_unauthorized_candidate_domain_triggers_no_fetch(monkeypatch):
    fetcher = SyntheticFetcher()
    service = ProductURLExtractionService(fetch_page=fetcher)
    monkeypatch.setattr(api_main, "ProductURLExtractionService", lambda: service)
    monkeypatch.setattr(api_main, "RATE_LIMIT", 100)
    client = TestClient(api_main.app)
    response = client.post("/api/product-candidates/from-url", json={
        "url": "https://retailer.unauthorized.example/product/1"
    })
    assert response.status_code == 403
    assert response.json()["error_code"] == "unsupported_source"
    assert fetcher.calls == []


def test_candidate_endpoint_returns_explicit_blocked_source_result(monkeypatch):
    monkeypatch.setattr(api_main, "RATE_LIMIT", 100)
    client = TestClient(api_main.app)
    response = client.post("/api/product-candidates/from-url", json={
        "url": "https://www.bigbasket.com/p/anything"
    })
    assert response.status_code == 403
    result = response.json()
    assert result["status"] == "blocked"
    assert result["error_code"] == "unsupported_source"


@pytest.mark.parametrize("failure,expected_code,expected_status", [
    (FetchBlocked("robots blocked fixture"), "robots_disallowed", 403),
    (FetchError("timeout", "timeout fixture", 504), "source_fetch_failed", 502),
])
def test_registered_source_fetch_errors_are_classified_without_retry(monkeypatch, failure, expected_code,
                                                                     expected_status):
    class FailureFetcher:
        def __init__(self):
            self.calls = []

        def __call__(self, url, **kwargs):
            self.calls.append(url)
            raise failure

    fetcher = FailureFetcher()
    service = ProductURLExtractionService(fetch_page=fetcher)
    monkeypatch.setattr(api_main, "ProductURLExtractionService", lambda: service)
    monkeypatch.setattr(api_main, "RATE_LIMIT", 100)
    response = TestClient(api_main.app).post("/api/product-candidates/from-url", json={
        "url": "https://world.openfoodfacts.org/product/SYN-FIXTURE-001"
    })
    assert response.status_code == expected_status
    assert response.json()["error_code"] == expected_code
    assert fetcher.calls == ["https://world.openfoodfacts.org/product/SYN-FIXTURE-001"]


def test_candidate_extraction_failure_is_distinct_from_fetch_failure(monkeypatch):
    service = ProductURLExtractionService(fetch_page=lambda url, **kwargs: (
        url, "<!doctype html><html><body>synthetic page without product fields</body></html>"))
    monkeypatch.setattr(api_main, "ProductURLExtractionService", lambda: service)
    monkeypatch.setattr(api_main, "RATE_LIMIT", 100)
    response = TestClient(api_main.app).post("/api/product-candidates/from-url", json={
        "url": "https://world.openfoodfacts.org/product/SYN-EMPTY-001"
    })
    assert response.status_code == 422
    assert response.json()["error_code"] == "product_extraction_failed"
