"""Read a pack photo or an app screenshot with Claude's vision and turn it into an extraction.

Runs only when an Anthropic credential is configured (see llm_fallback.available). The model first
transcribes every piece of text it can read, then fills the schema; a value is kept only when it appears
in that transcript, so the model can locate label text but cannot add values that are not on the image.
Values the model cannot read stay empty and the report lists them as missing.
"""
from __future__ import annotations

import base64
from typing import Optional

from pydantic import BaseModel, Field

from extract.llm_fallback import MODEL, LlmProduct, available, grounded, to_extracted

MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024


class LabelReading(LlmProduct):
    transcript: str = Field(..., description="Every piece of text readable in the image, copied verbatim, "
                                             "line by line, including the nutrition table and ingredient list")
    product_type: Optional[str] = Field(None, description="What kind of food this is, in a few words, only if "
                                                          "the image says so (e.g. 'namkeen', 'breakfast cereal')")
    unreadable: list[str] = Field(default_factory=list, description="Fields that are on the image but could "
                                                                     "not be read with confidence")


PROMPT = """This image is a packaged-food label, a pack photo or a shopping-app screenshot.
First write a verbatim transcript of all text you can read. Then fill the other fields by copying text and
numbers exactly as they appear. If a value is not visible or not legible, leave it empty and name it in
`unreadable`: do not estimate, convert, or fill anything from general knowledge about the product."""


def available_for_images() -> bool:
    return available()


def extract_image(data: bytes, media_type: str, client=None) -> Optional[dict]:
    """Return an Extracted dict (source 'label-photo') or None when not configured or the model declines."""
    if media_type not in MEDIA_TYPES:
        raise ValueError(f"unsupported image type {media_type}")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("image larger than 8 MB")
    if client is None and not available():
        return None
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    response = client.beta.messages.parse(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                         "data": base64.standard_b64encode(data).decode("ascii")}},
            {"type": "text", "text": PROMPT},
        ]}],
        output_format=LabelReading,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        return None
    reading: LabelReading = response.parsed_output
    out = to_extracted(reading, reading.transcript)
    out["source"] = "label-photo"
    out["description"] = reading.transcript[:4000] or None
    if reading.product_type and grounded(reading.product_type, reading.transcript):
        out["category_hint"] = reading.product_type
    out["unreadable"] = reading.unreadable
    return out
