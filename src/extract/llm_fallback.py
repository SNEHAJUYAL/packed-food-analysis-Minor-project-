"""LLM fallback for unstructured pages (doc section 8.5): schema-constrained output.

Not wired yet. The interface is fixed so the pipeline can call it later; until
then it returns None and the pipeline reports the fields as unknown.
"""
from __future__ import annotations

from typing import Optional


def extract_llm(html: str, url: str) -> Optional[dict]:
    """Return an Extracted dict (see extract.jsonld.empty_extracted) or None.

    TODO: call an LLM with the page text and a JSON schema matching Extracted,
    mark every field it returns with source "llm", and never let it fill numbers
    that are not literally present in the page text.
    """
    return None
