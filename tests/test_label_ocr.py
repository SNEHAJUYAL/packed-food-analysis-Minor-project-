"""Offline OCR of label photos. Parser tests need nothing; the end-to-end test runs only where Tesseract is
installed. The label text is made up for the test."""
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import api.main as api_main
import services
from database.models import Base
from extract import label_image, label_ocr

LABEL = """TEST SNACKS SPICED OKRA CRISPS
Net Wt. 60 g
MRP Rs. 99.00 (Incl. of all taxes)
Ingredients: Okra (62%), Rice Bran Oil, Gram Flour, Spices, Salt.
Nutritional Information Per 100 g Per Serving (30 g)
Energy (kcal) 512 154
Protein (g) 9.1 2.7
Carbohydrate (g) 48.2 14.5
Total Sugars (g) 3.4 1.0
Added Sugars (g) 0 0
Total Fat (g) 31.0 9.3
Saturated Fat (g) 6.2 1.9
Trans Fat (g) 0.1 0.0
Sodium (mg) 610 183
High Protein"""


def test_parser_reads_label_text():
    ex = label_ocr.parse_label_text(LABEL)
    assert ex["source"] == "label-ocr"
    assert ex["ingredients_text"] == "Okra (62%), Rice Bran Oil, Gram Flour, Spices, Salt"
    assert ex["pack_size_text"] == "60 g" and ex["price"] == "99.00"
    assert ex["nutrition_basis_text"] == "100 g"
    n = ex["nutrition"]
    assert n["energy"] == "512 kcal" and n["protein"] == "9.1 g" and n["sodium"] == "610 mg"
    assert n["saturated_fat"] == "6.2 g" and n["total_fat"] == "31.0 g" and n["added_sugars"] == "0 g"
    assert "fibre" not in n  # not on the label: stays unknown
    assert "High Protein" in ex["claims_text"]


def test_parser_takes_per_100_column_when_serving_comes_first():
    text = "Per serving (30 g) Per 100 g\nProtein (g) 2.7 9.1\nSodium (mg) 183 610"
    assert label_ocr.parse_nutrition(text) == {"protein": "9.1 g", "sodium": "610 mg"}


def test_parser_leaves_kj_only_energy_unknown():
    assert "energy" not in label_ocr.parse_nutrition("Energy 2140 kJ")
    assert label_ocr.parse_nutrition("Energy 2140 kJ / 512 kcal")["energy"] == "512 kcal"


def _label_png() -> bytes:
    from PIL import Image, ImageDraw, ImageFont
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 28)
    except OSError:
        font = ImageFont.load_default(size=28)
    lines = LABEL.splitlines()
    img = Image.new("RGB", (1400, 60 + 44 * len(lines)), "white")
    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        d.text((30, 30 + 44 * i), line, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


@pytest.mark.skipif(not label_ocr.available(), reason="Tesseract is not installed")
def test_photo_upload_with_offline_ocr(monkeypatch):
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    factory = sessionmaker(bind=eng, expire_on_commit=False)
    monkeypatch.setattr(api_main, "session_factory", lambda *a, **k: factory)
    monkeypatch.setattr(api_main, "RATE_LIMIT", 1000)
    monkeypatch.setattr(label_image, "available_for_images", lambda: False)  # no API key: OCR is used
    r = TestClient(api_main.app).post(
        "/api/analyze-upload", files={"file": ("okra.png", _label_png(), "image/png")},
        data={"site": "blinkit.com", "name": "Spiced Okra Crisps", "category": "namkeen_chips"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["source"]["extraction_method"] == "label-ocr" and d["source"]["site"] == "blinkit.com"
    p = d["report"]["product"]
    assert p["name"]["value"] == "Spiced Okra Crisps"
    assert p["nutrition"]["protein"]["value"] == 9.1 and p["nutrition"]["sodium"]["value"] == 610
    assert p["nutrition"]["protein"]["source"] == "label-ocr"
    assert d["status"] != "insufficient_data"
    assert any(s["step"] == "transcript" and "Okra" in s["detail"] for s in d["extraction_log"])
