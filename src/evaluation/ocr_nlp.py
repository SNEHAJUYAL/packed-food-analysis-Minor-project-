"""Reproducible OCR and ingredient-parser benchmarks.

The OCR fixture is rendered text, not a camera photograph. Results from it
validate the benchmark harness and baseline plumbing, not real-label accuracy.
"""
from __future__ import annotations

import io
import time
from typing import Any, Sequence

from PIL import Image, ImageDraw, ImageFont

from extract.label_ocr import read_text
from normalise.ingredients import normalise_ingredients

OCR_GOLD_TEXT = """TEST SNACKS SPICED OKRA CRISPS
Net Wt. 60 g
MRP Rs. 99.00
Ingredients: Okra (62%), Rice Bran Oil, Gram Flour, Spices, Salt."""

INGREDIENT_GOLD = [
    "whole wheat flour",
    "sugar",
    "maltodextrin",
    "soy lecithin",
    "salt",
    "permitted flavouring",
]
INGREDIENT_SAMPLE = "Whole Wheat Flour, Sugar, Maltodextrin, Soy Lecithin, Salt, Permitted Flavouring."


def _edit_distance(left: Sequence[Any], right: Sequence[Any]) -> int:
    previous = list(range(len(right) + 1))
    for i, left_item in enumerate(left, 1):
        current = [i]
        for j, right_item in enumerate(right, 1):
            current.append(min(
                current[-1] + 1,
                previous[j] + 1,
                previous[j - 1] + (left_item != right_item),
            ))
        previous = current
    return previous[-1]


def _rate(distance: int, denominator: int) -> float:
    return distance / max(1, denominator)


def _render_ocr_fixture() -> bytes:
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 28)
    except OSError:
        font = ImageFont.load_default(size=28)
    image = Image.new("RGB", (1400, 240), "white")
    draw = ImageDraw.Draw(image)
    for index, line in enumerate(OCR_GOLD_TEXT.splitlines()):
        draw.text((30, 20 + index * 48), line, fill="black", font=font)
    output = io.BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def evaluate_ocr() -> dict[str, Any]:
    """Measure the current Tesseract path on the reproducible rendered fixture."""
    data = _render_ocr_fixture()
    started = time.perf_counter()
    predicted = read_text(data).strip()
    elapsed_ms = (time.perf_counter() - started) * 1000
    return {
        "status": "complete",
        "data": "reproducible rendered label fixture; not a camera photograph",
        "bytes": len(data),
        "latency_ms": round(elapsed_ms, 2),
        "cer": round(_rate(_edit_distance(OCR_GOLD_TEXT, predicted), len(OCR_GOLD_TEXT)), 4),
        "wer": round(_rate(_edit_distance(OCR_GOLD_TEXT.split(), predicted.split()),
                           len(OCR_GOLD_TEXT.split())), 4),
        "expected_text": OCR_GOLD_TEXT,
        "predicted_text": predicted,
    }


def evaluate_ingredient_sample() -> dict[str, Any]:
    """Check record extraction separately from dictionary classification."""
    normalised = normalise_ingredients(INGREDIENT_SAMPLE)
    predicted = [item["name"] for item in normalised["items"]]
    gold = set(INGREDIENT_GOLD)
    predicted_set = set(predicted)
    true_positive = len(gold & predicted_set)
    precision = true_positive / len(predicted_set) if predicted_set else 0.0
    recall = true_positive / len(gold) if gold else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return {
        "status": "complete",
        "data": "six-item ingredient sample supplied for the audit",
        "n_records": len(predicted),
        "record_precision": round(precision, 4),
        "record_recall": round(recall, 4),
        "record_f1": round(f1, 4),
        "dictionary_matched": sum(item["status"] == "matched" for item in normalised["items"]),
        "uncertain": sum(item["status"] == "uncertain" for item in normalised["items"]),
        "unmatched": normalised["unmatched"],
        "allergens": normalised["allergens"],
        "items": normalised["items"],
    }
