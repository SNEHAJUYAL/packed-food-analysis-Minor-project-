"""Uploads (pack photos, app screenshots, saved pages) and same-site alternatives.

Photos are read with a fake Anthropic client, so no network or API key is needed. Pages are the synthetic
fixtures in tests/fixtures with a canonical link added; nothing is fetched.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import api.main as api_main
import services
from database.ingest import ingest_records, read_jsonl
from database.models import Base, ProductRow
from database.repository import site_of
from extract import label_image
from extract.label_image import LabelReading, extract_image

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).parent / "fixtures"
BISCUIT = (FIX / "biscuit_html_only.html").read_text(encoding="utf-8")
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64  # content is never decoded here; the fake client reads nothing

TRANSCRIPT = """TBH To Be Honest Spiced Okra Namkeen
Net Wt. 60 g  MRP Rs 99
Ingredients: Okra (62%), Rice Bran Oil, Gram Flour, Spices, Salt
Nutritional information per 100 g: Energy 512 kcal, Protein 9.1 g, Total Fat 31 g, Saturated Fat 6.2 g,
Total Sugars 3.4 g, Sodium 610 mg"""


class FakeMessages:
    def __init__(self, result, stop_reason="end_turn"):
        self.result, self.stop_reason, self.calls = result, stop_reason, []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(stop_reason=self.stop_reason, parsed_output=self.result)


def fake_client(result, stop_reason="end_turn"):
    return SimpleNamespace(beta=SimpleNamespace(messages=FakeMessages(result, stop_reason)))


def okra_reading(**kw):
    base = dict(transcript=TRANSCRIPT, name="Spiced Okra Namkeen", brand="TBH", pack_size="60 g",
                price="Rs 99", ingredients="Okra (62%), Rice Bran Oil, Gram Flour, Spices, Salt",
                nutrition_basis="100 g",
                nutrition={"energy": "512 kcal", "protein": "9.1 g", "total_fat": "31 g", "saturated_fat": "6.2 g",
                           "total_sugars": "3.4 g", "sodium": "610 mg",
                           "fibre": "7.5 g"},  # fibre is not in the transcript: must be dropped
                claims=["High protein"],  # not on the label: must be dropped
                product_type="namkeen", unreadable=["trans fat"])
    return LabelReading(**(base | kw))


def page(url=None, **replace):
    html = BISCUIT
    for a, b in replace.items():
        html = html.replace(a.replace("_", " "), b)
    if url:
        html = html.replace("<head>", f'<head>\n<link rel="canonical" href="{url}">', 1)
    return html.encode()


# ------------------------------------------------------------------ the image reader on its own

def test_photo_values_must_be_in_the_transcript():
    client = fake_client(okra_reading())
    ex = extract_image(PNG, "image/png", client=client)
    assert ex["source"] == "label-photo" and ex["category_hint"] == "namkeen"
    assert ex["nutrition"]["total_sugars"] == "3.4 g" and "fibre" not in ex["nutrition"]
    assert ex["claims_text"] == [] and ex["unreadable"] == ["trans fat"]
    call = client.beta.messages.calls[0]
    image = call["messages"][0]["content"][0]
    assert call["output_format"] is LabelReading
    assert image["type"] == "image" and image["source"]["media_type"] == "image/png"


def test_photo_refusal_and_bad_input():
    assert extract_image(PNG, "image/png", client=fake_client(okra_reading(), "refusal")) is None
    with pytest.raises(ValueError):
        extract_image(PNG, "application/pdf", client=fake_client(okra_reading()))
    with pytest.raises(ValueError):
        extract_image(b"x" * (label_image.MAX_IMAGE_BYTES + 1), "image/png", client=fake_client(okra_reading()))


def test_site_of():
    assert site_of("https://www.Blinkit.com/prn/x/prid/1") == "blinkit.com"
    assert site_of("https://www.zeptonow.com/pn/x") == "zeptonow.com"
    assert site_of("blinkit.com/x") is None and site_of(None) is None


def test_canonical_url_is_read_from_a_saved_page():
    assert services.page_url_in(page("https://blinkit.com/prn/a/prid/1").decode()) == "https://blinkit.com/prn/a/prid/1"
    assert services.page_url_in('<meta property="og:url" content="https://www.zeptonow.com/pn/b">') \
        == "https://www.zeptonow.com/pn/b"
    assert services.page_url_in(BISCUIT) is None


# ------------------------------------------------------------------ through the API

@pytest.fixture(scope="module")
def client():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    factory = sessionmaker(bind=eng, expire_on_commit=False)
    with factory() as s:
        ingest_records(s, read_jsonl(ROOT / "data" / "sample" / "synthetic_products.jsonl"))
        s.commit()

    def no_fetch(*a, **k):
        raise AssertionError("uploads must not fetch anything")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(api_main, "session_factory", lambda *a, **k: factory)
        mp.setattr(api_main, "RATE_LIMIT", 1000)
        mp.setattr(services, "fetch", no_fetch)
        c = TestClient(api_main.app)
        c.factory = factory
        yield c


def upload(client, name, data, ctype, **form):
    return client.post("/api/analyze-upload", files={"file": (name, data, ctype)}, data=form)


def test_saved_page_is_read_without_fetching(client):
    r = upload(client, "Butter Cookies.html", page("https://www.blinkit.com/prn/cookies/prid/11"), "text/html")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["source"]["source_type"] == "saved_page" and d["source"]["site"] == "blinkit.com"
    assert d["source"]["source_url"] == "https://www.blinkit.com/prn/cookies/prid/11"
    assert d["extraction_log"][0]["step"] == "upload" and "nothing fetched" in d["extraction_log"][0]["detail"]
    assert d["report"]["product"]["nutrition"]["total_sugars"]["value"] == 24.5
    assert d["report"]["product"]["category"]["value"] == "biscuits_cookies"


def test_saved_page_without_address_uses_given_site(client):
    r = upload(client, "page.htm", page(Sample_Bakes="Other Bakes"), "application/octet-stream", site="Zeptonow.com")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["source"]["site"] == "zeptonow.com" and d["source"]["source_url"] is None
    with client.factory() as s:
        assert s.get(ProductRow, d["product_id"]).external_product_id.startswith("page:")


def test_photo_upload(client, monkeypatch):
    fake = fake_client(okra_reading())
    monkeypatch.setattr(label_image, "available_for_images", lambda: True)
    real = label_image.extract_image
    monkeypatch.setattr(label_image, "extract_image", lambda data, mt, client=None: real(data, mt, client=fake))
    r = upload(client, "okra.png", PNG, "image/png", page_url="https://blinkit.com/prn/okra/prid/721289")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["source"]["source_type"] == "photo" and d["source"]["site"] == "blinkit.com"
    rep = d["report"]["product"]
    assert rep["category"]["value"] == "namkeen_chips"
    assert rep["nutrition"]["sodium"]["value"] == 610 and rep["nutrition"]["sodium"]["source"] == "label-photo"
    assert rep["nutrition"]["fibre"]["value"] is None  # not in the transcript, so unknown
    steps = {s["step"]: s for s in d["extraction_log"]}
    assert "Okra (62%)" in steps["transcript"]["detail"] and steps["unreadable"]["outcome"] == "flagged"
    # the same photo again replaces the record instead of adding a second one
    again = upload(client, "okra.png", PNG, "image/png", page_url="https://blinkit.com/prn/okra/prid/721289")
    assert again.json()["product_id"] == d["product_id"]


def test_photo_without_api_key_says_so(client, monkeypatch):
    monkeypatch.setattr(label_image, "available_for_images", lambda: False)
    r = upload(client, "pack.jpg", PNG, "image/jpeg")
    assert r.status_code == 503 and r.json()["detail"]["code"] == "vision_not_configured"


def test_upload_rejections(client):
    assert upload(client, "label.pdf", b"%PDF", "application/pdf").status_code == 415
    assert upload(client, "empty.html", b"", "text/html").json()["detail"]["code"] == "empty_file"
    r = upload(client, "p.html", page(), "text/html", page_url="ftp://x")
    assert r.status_code == 422
    big = client.post("/api/analyze-upload", files={"file": ("big.png", b"x" * (api_main.MAX_UPLOAD_BYTES + 10),
                                                             "image/png")})
    assert big.status_code == 413
    # the larger limit applies only to uploads
    assert client.post("/api/products/compare", content=b"x" * 70000,
                       headers={"content-type": "application/json"}).status_code == 413


def test_alternatives_stay_on_the_same_site(client):
    better = page("https://blinkit.com/prn/light-cookies/prid/12", Butter_Cookies="Light Cookies",
                  **{"<td>24.5</td>": "<td>4.5</td>", "<td>22.0</td>": "<td>2.0</td>",
                     "<td>11.2</td>": "<td>2.2</td>", "No Added Sugar": "Crisp"})
    worse = page("https://blinkit.com/prn/cream-cookies/prid/13", Butter_Cookies="Cream Cookies")
    assert upload(client, "a.html", better, "text/html").status_code == 200
    src = upload(client, "b.html", worse, "text/html").json()["product_id"]
    d = client.get(f"/api/products/{src}/alternatives").json()
    assert d["site"] == "blinkit.com" and d["scope"] == "same_site" and d["message"] is None
    assert d["alternatives"] and all(a["site"] == "blinkit.com" for a in d["alternatives"])
    assert "Light Cookies" in d["alternatives"][0]["name"]
    wide = client.get(f"/api/products/{src}/alternatives", params={"scope": "all"}).json()
    assert wide["scope"] == "all" and wide["eligible_count"] > d["eligible_count"]


def test_same_site_falls_back_and_says_so(client):
    only = upload(client, "c.html", page("https://www.zeptonow.com/pn/zz-cookies/pvid/1", Butter_Cookies="ZZ Cookies"),
                  "text/html").json()["product_id"]
    d = client.get(f"/api/products/{only}/alternatives").json()
    assert d["site"] == "zeptonow.com" and d["scope"] == "all"
    assert d["message"].startswith("No other product analysed from zeptonow.com does better")
    assert d["alternatives"]  # drawn from all stored biscuits instead
