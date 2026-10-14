"""Use cases behind the API: analyse a URL into the database, read stored analyses, compare.

Order for a URL (spec, extraction workflow): validate URL and destination -> fetch with
limits -> JSON-LD -> HTML -> optional LLM fallback (grounded, schema-checked) ->
normalise -> match against stored Open Food Facts records -> record source, method
and time per field -> flag missing and conflicting data -> partial result if needed.
"""
from __future__ import annotations

import logging
from typing import Optional

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import scoring_config
from database import repository as repo
from database.models import ProductRow, ProductSource
from extract.fetch import fetch, validate_url
from extract.html_parser import extract_html
from extract.jsonld import extract_jsonld
from extract import llm_fallback
from normalise.build import build_product
from pipeline import analyse_product

log = logging.getLogger("fdi.services")
OFF_MATCH_CUTOFF = 85


def _filled(ex: Optional[dict]) -> list[str]:
    if not ex:
        return []
    keys = [k for k in ("name", "brand", "price", "pack_size_text", "ingredients_text") if ex.get(k)]
    if ex.get("nutrition"):
        keys.append(f"nutrition ({len(ex['nutrition'])} values)")
    if ex.get("claims_text"):
        keys.append("claims text")
    return keys


def run_extraction(html: str, url: str) -> tuple[list[dict], list[dict], str]:
    """Run the extractors in order. Returns (extractions, log, method summary)."""
    steps, found = [], []
    for name, fn in (("json-ld", extract_jsonld), ("html", extract_html)):
        ex = fn(html, url)
        fields = _filled(ex)
        steps.append({"step": name, "outcome": "ok" if fields else "nothing found",
                      "detail": ", ".join(fields) if fields else "no usable fields"})
        if fields:
            found.append(ex)
    if any(f.get("nutrition") or f.get("ingredients_text") for f in found):
        steps.append({"step": "llm-fallback", "outcome": "skipped",
                      "detail": "structured data or a nutrition table was found"})
    elif not llm_fallback.available():
        steps.append({"step": "llm-fallback", "outcome": "skipped",
                      "detail": "no ANTHROPIC_API_KEY set; deterministic extractors only"})
    else:
        try:
            ex = llm_fallback.extract_llm(html, url)
        except Exception as e:  # the fallback is optional; never fail the request because of it
            ex = None
            steps.append({"step": "llm-fallback", "outcome": "failed", "detail": type(e).__name__})
        else:
            fields = _filled(ex)
            steps.append({"step": "llm-fallback", "outcome": "ok" if fields else "nothing found",
                          "detail": (", ".join(fields) + "; every value checked against the page text")
                          if fields else "no grounded values"})
            if fields:
                found.append(ex)
    method = "+".join(f["source"] for f in found) or "none"
    return found, steps, method


def match_open_food_facts(s: Session, name: Optional[str], brand: Optional[str],
                          category: Optional[str]) -> Optional[dict]:
    """Best stored Open Food Facts record by brand + name similarity (reference only, never merged)."""
    if not name:
        return None
    q = (select(ProductRow).join(ProductSource)
         .where(ProductSource.source_type == "open_food_facts"))
    if category:
        q = q.where(ProductRow.category == category)
    target = f"{brand or ''} {name}".strip().lower()
    best = None
    for row in s.scalars(q).unique():
        score = fuzz.token_set_ratio(target, f"{row.brand or ''} {row.name or ''}".strip().lower())
        if score >= OFF_MATCH_CUTOFF and (best is None or score > best["score"]):
            best = {"product_id": row.id, "barcode": row.barcode, "name": row.name, "brand": row.brand,
                    "score": round(score, 1)}
    return best


def analyse_row(s: Session, row: ProductRow) -> dict:
    """Score a stored product against the stored products of its category and keep the result."""
    product = repo.to_product(row)
    peers = repo.peer_unit_prices(s, row.category, row.nutrition_basis, exclude_id=row.id)
    report = analyse_product(product, peers)
    repo.save_analysis(s, row, report)
    return report


def payload(row: ProductRow, report: dict) -> dict:
    src = repo.source_info(row)
    log_steps = row.sources[-1].extraction_log if row.sources else []
    return {"product_id": row.id, "status": report["status"], "is_synthetic": repo.is_synthetic(row),
            "source": src, "missing_fields": report["missing_fields"], "conflicts": report["product"]["conflicts"],
            "extraction_log": log_steps, "methodology_version": report["methodology_version"], "report": report}


def analyze_url(s: Session, url: str, category: Optional[str] = None, refresh: bool = False) -> dict:
    validate_url(url)
    html = fetch(url, use_cache=not refresh)
    steps = [{"step": "fetch", "outcome": "ok", "detail": "SSRF checks, robots.txt and size limit passed"}]
    found, ex_steps, method = run_extraction(html, url)
    steps += ex_steps
    product = build_product(found, url=url, category_override=category)
    match = match_open_food_facts(s, product.name.value, product.brand.value, product.category.value)
    steps.append({"step": "open-food-facts-match",
                  "outcome": "ok" if match else "no match",
                  "detail": (f"stored record #{match['product_id']} ({match['brand']} {match['name']}), "
                             f"similarity {match['score']}; reference only, values not merged")
                  if match else "no stored Open Food Facts record above the similarity cutoff"})
    if product.conflicts:
        steps.append({"step": "conflicts", "outcome": "flagged", "detail": "; ".join(product.conflicts)})
    row = repo.save_product(s, product, source_type="url", extraction_method=method, extraction_log=steps)
    report = analyse_row(s, row)
    log.info("analysed url=%s product_id=%s status=%s method=%s", url, row.id, report["status"], method)
    return payload(row, report)


def get_analysis(s: Session, product_id: int) -> Optional[dict]:
    row = repo.get_row(s, product_id)
    if row is None:
        return None
    res = repo.latest_analysis(s, product_id)
    report = res.report if res is not None else analyse_row(s, row)
    return payload(row, report)


def summary(row: ProductRow, res) -> dict:
    return {"product_id": row.id, "name": row.name, "brand": row.brand, "category": row.category,
            "pack_size": row.pack_size, "pack_unit": row.pack_unit, "price_per_100": res.price_per_100,
            "overall": res.overall_score, "grade": res.grade, "status": res.status,
            "source_type": row.sources[-1].source_type if row.sources else "manual",
            "is_synthetic": repo.is_synthetic(row),
            "source_url": row.sources[-1].source_url if row.sources else None,
            "collected_at": repo._iso(row.sources[-1].collected_at) if row.sources else None}


def list_products(s: Session, category: Optional[str] = None, q: Optional[str] = None, limit: int = 50) -> dict:
    rows = repo.latest_analyses(s, category)
    if q:
        ql = q.lower()
        rows = [(r, a) for r, a in rows if ql in f"{r.brand or ''} {r.name or ''}".lower()]
    return {"products": [summary(r, a) for r, a in rows[:limit]], "total": len(rows)}


def rescore_all(s: Session) -> int:
    """Recompute every stored analysis (after ingestion, or after a methodology change)."""
    n = 0
    for row in s.scalars(select(ProductRow).order_by(ProductRow.id)):
        analyse_row(s, row)
        n += 1
    return n


def methodology_version() -> str:
    return scoring_config()["methodology_version"]
