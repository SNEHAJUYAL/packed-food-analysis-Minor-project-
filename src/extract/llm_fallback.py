"""LLM fallback for pages with no structured metadata or readable table (doc section 8.5).

Uses Claude with schema-constrained output. Runs only when an Anthropic credential is
configured (ANTHROPIC_API_KEY or `ant auth login`) and the `anthropic` package is installed;
otherwise returns None and the pipeline reports the fields as unknown.

Never-invent rule: every value the model returns must appear literally in the page text.
Values that do not are dropped, so the LLM can locate data but cannot create it.
"""
from __future__ import annotations

import os
import re
from typing import Optional

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from extract.jsonld import empty_extracted

MODEL = os.environ.get("FDI_LLM_MODEL", "claude-opus-5-5")
MAX_PAGE_CHARS = 60_000


class LlmProduct(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    price: Optional[str] = Field(None, description="Price exactly as written, e.g. '₹120'")
    pack_size: Optional[str] = Field(None, description="Net quantity exactly as written, e.g. '200 g'")
    ingredients: Optional[str] = Field(None, description="Ingredient list copied verbatim")
    nutrition_basis: Optional[str] = Field(None, description="Basis of the nutrition values as written, "
                                                              "e.g. '100 g', '100 ml' or '30 g serving'")
    nutrition: dict[str, str] = Field(default_factory=dict, description=(
        "Nutrient name -> value with unit, exactly as written. Keys from: energy, protein, carbohydrate, "
        "total_sugars, added_sugars, total_fat, saturated_fat, trans_fat, fibre, sodium, salt"))
    claims: list[str] = Field(default_factory=list, description="Front-of-pack or marketing claims, verbatim")


PROMPT = """Extract the packaged food product on this web page into the schema.
Copy text and numbers exactly as they appear. If a field is not on the page, leave it empty:
do not estimate, convert, or fill from general knowledge.

<page_text>
{text}
</page_text>"""


def page_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s).lower()


def grounded(value: Optional[str], text: str) -> bool:
    """True when every number in value appears in the page text (whitespace-insensitive)."""
    if not value:
        return False
    flat = _norm(text)
    numbers = re.findall(r"\d+(?:[.,]\d+)?", value)
    if numbers:
        return all(n in flat for n in numbers)
    return _norm(value) in flat


def to_extracted(result: LlmProduct, text: str) -> dict:
    """Convert a model result to an Extracted dict, keeping only grounded values."""
    out = empty_extracted("llm")
    for field, key in (("name", "name"), ("brand", "brand"), ("price", "price"),
                       ("pack_size", "pack_size_text"), ("ingredients", "ingredients_text"),
                       ("nutrition_basis", "nutrition_basis_text")):
        v = getattr(result, field)
        if grounded(v, text):
            out[key] = v
    allowed = {"energy", "protein", "carbohydrate", "total_sugars", "added_sugars", "total_fat",
               "saturated_fat", "trans_fat", "fibre", "sodium", "salt"}
    out["nutrition"] = {k: v for k, v in result.nutrition.items() if k in allowed and grounded(v, text)}
    out["claims_text"] = [c for c in result.claims if _norm(c) in _norm(text)]
    return out


def available() -> bool:
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or os.environ.get("FDI_LLM_ENABLED"))


def extract_llm(html: str, url: str, client=None) -> Optional[dict]:
    """Return an Extracted dict or None when the fallback is not configured or the model declines."""
    if client is None and not available():
        return None
    text = page_text(html)[:MAX_PAGE_CHARS]
    if not text:
        return None
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    response = client.beta.messages.parse(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": "low"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": PROMPT.format(text=text)}],
        output_format=LlmProduct,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        return None
    return to_extracted(response.parsed_output, text)
