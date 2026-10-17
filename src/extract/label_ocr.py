"""Read a pack photo or a shop screenshot offline with Tesseract OCR (free, no API key).

Needs the Tesseract program (macOS: `brew install tesseract`) and the pytesseract package. The OCR text is
parsed with fixed rules: the ingredient list after "Ingredients:", nutrient rows by their label, the net
quantity, and the price. Every value comes from the OCR text; nothing is estimated. OCR misreads curved,
shiny or blurred packs, so the text is shown in the extraction log for checking against the pack.
"""
from __future__ import annotations

import io
import re
from typing import Optional

from extract.html_parser import _BASIS_RE, _INGREDIENTS_RE, _PACK_RE, _SERVING_RE, nutrient_key
from extract.jsonld import empty_extracted

UNITS = {"energy": "kcal", "sodium": "mg"}  # default unit when the row shows none
_NUM = r"(\d+(?:[.,]\d+)?)"
_VALUE_RE = re.compile(_NUM + r"\s*(kcal|kj|mg|mcg|µg|g)?\b", re.IGNORECASE)
_MRP_RE = re.compile(r"m\.?\s*r\.?\s*p\.?[^\d\n]{0,20}" + _NUM, re.IGNORECASE)
_RUPEE_RE = re.compile(r"(?:₹|rs\.?|inr)\s*" + _NUM, re.IGNORECASE)


def available() -> bool:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
    except Exception:  # package missing, or the tesseract program is not installed
        return False
    return True


def read_text(data: bytes) -> str:
    """OCR an image. Small images are enlarged and converted to greyscale, which helps Tesseract."""
    import pytesseract
    from PIL import Image, ImageOps

    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img).convert("L")
    if img.width < 1600:
        scale = 1600 / img.width
        img = img.resize((1600, int(img.height * scale)), Image.LANCZOS)
    img = ImageOps.autocontrast(img)
    return pytesseract.image_to_string(img)


def _serving_first(text: str) -> bool:
    """True when the table header lists the per-serving column before the per-100 column."""
    for line in text.splitlines():
        b, s = _BASIS_RE.search(line), _SERVING_RE.search(line)
        if b and s:
            return s.start() < b.start()
    return False


def parse_nutrition(text: str) -> dict[str, str]:
    """Nutrient rows such as 'Protein (g) 9.1 2.3' or 'Energy 512 kcal' -> {'protein': '9.1 g', ...}."""
    pick = 1 if _serving_first(text) else 0
    out: dict[str, str] = {}
    for line in text.splitlines():
        m = re.search(r"\d", line)
        if not m:
            continue
        label, rest = line[:m.start()], line[m.start():]
        key = nutrient_key(label.strip(" :-|"))
        if key is None or key in out:
            continue
        unit_in_label = re.search(r"\(\s*(kcal|kj|mg|mcg|g)\s*\)", label, re.IGNORECASE)
        if key == "energy":
            kcal = re.search(_NUM + r"\s*kcal", rest, re.IGNORECASE)
            if kcal:
                out[key] = f"{kcal.group(1).replace(',', '.')} kcal"
                continue
        values = _VALUE_RE.findall(rest)
        if not values:
            continue
        num, unit = values[min(pick, len(values) - 1)]
        unit = (unit or (unit_in_label.group(1) if unit_in_label else None) or UNITS.get(key, "g")).lower()
        if key == "energy" and unit == "kj":
            continue  # kJ only: leave energy unknown rather than convert
        out[key] = f"{num.replace(',', '.')} {unit}"
    return out


def parse_label_text(text: str) -> dict:
    """Turn OCR text into an Extracted dict (source 'label-ocr'). Fields not found stay empty."""
    out = empty_extracted("label-ocr")
    m = _INGREDIENTS_RE.search(text)
    if m:
        out["ingredients_text"] = re.sub(r"\s+", " ", m.group(1)).strip(" .")
    m = _PACK_RE.search(text)
    if m:
        out["pack_size_text"] = m.group(1)
    m = _MRP_RE.search(text) or _RUPEE_RE.search(text)
    if m:
        out["price"] = m.group(1).replace(",", "")
        out["currency"] = "INR"
    out["nutrition"] = parse_nutrition(text)
    b = _BASIS_RE.search(text)
    out["nutrition_basis_text"] = f"100 {b.group(1)}" if b else None
    out["claims_text"] = [ln.strip() for ln in text.splitlines() if 3 <= len(ln.strip()) <= 60][:60]
    return out


def extract_ocr(data: bytes) -> tuple[Optional[dict], str]:
    """Returns (extraction or None if no text was read, the OCR text)."""
    text = read_text(data)
    if not text.strip():
        return None, ""
    return parse_label_text(text), text
