"""Audit permitted retailer product URLs through the existing extraction path.

This is deliberately separate from ``evaluation.run`` because retailer pages
are dynamic, location-dependent, and may change between runs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.config import ROOT
from extract.fetch import FetchError, allowed_by_robots, safe_get
from extract.html_parser import extract_html
from extract.jsonld import extract_jsonld

URLS = {
    "blinkit": "https://blinkit.com/prn/pran-potata-biscuit/prid/483702",
    "zepto": "https://www.zeptonow.com/pn/bonn-digestive-high-fiber-biscuits-healthy-and-high-fiber-cookies/pvid/55bf4658-d4b7-4d70-8bf7-0650e5b266d2",
    "swiggy_instamart": "https://www.swiggy.com/instamart/p/britannia-milk-bikis-biscuits-100-atta-730AM6ZNMK",
    "amazon_india": "https://www.amazon.in/dp/B0HLKTTP9Z",
}

FIELDS = ("name", "brand", "price", "currency", "pack_size_text",
          "ingredients_text", "nutrition_basis_text")


def _fields(extraction: dict[str, Any] | None) -> dict[str, Any]:
    return {field: extraction.get(field) if extraction else None for field in FIELDS}


def audit_url(retailer: str, url: str) -> dict[str, Any]:
    result: dict[str, Any] = {"retailer": retailer, "url": url}
    try:
        result["robots_allowed"] = allowed_by_robots(url)
        if not result["robots_allowed"]:
            result.update({"status": "blocked_by_robots", "error": None})
            return result
        final_url, html = safe_get(url)
        jsonld = extract_jsonld(html, final_url)
        html_extraction = extract_html(html, final_url)
        result.update({
            "status": "fetched",
            "final_url": final_url,
            "response_bytes": len(html.encode("utf-8")),
            "jsonld": _fields(jsonld),
            "html": _fields(html_extraction),
        })
    except FetchError as exc:
        result.update({
            "status": "error",
            "error": {"code": exc.code, "http_status": exc.http_status, "message": exc.message},
        })
    except Exception as exc:
        result.update({
            "status": "error",
            "error": {"code": "unexpected_error", "message": f"{type(exc).__name__}: {exc}"},
        })
    return result


def run(output: Path | None = None) -> dict[str, Any]:
    results = [audit_url(retailer, url) for retailer, url in URLS.items()]
    report = {
        "data": "Permitted public product URLs audited with the existing safe fetcher.",
        "extractors": ["json-ld", "html"],
        "retailers": results,
        "limitations": [
            "Results are time-, location-, cookie-, and bot-response dependent.",
            "A successful HTTP fetch does not prove product identity or field accuracy.",
            "No retailer internal APIs, browser-extension APIs, or access restrictions were bypassed.",
        ],
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    report = run(ROOT / "reports" / "retailer_audit.json")
    print(json.dumps(report, indent=2))
