"""FastAPI app. Run: uvicorn api.main:app --app-dir src --reload"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

from core.config import claim_rules, read_csv, scoring_config, thresholds
from core.schema import CATEGORIES, Product
from extract.fetch import FetchBlocked
from pipeline import analyse_html, analyse_product, analyse_url
from recommend.ranker import compare

app = FastAPI(title="Food Decision Intelligence", version=scoring_config()["methodology_version"])


class UrlRequest(BaseModel):
    url: HttpUrl
    category: Optional[str] = None
    use_cache: bool = True


class HtmlRequest(BaseModel):
    url: str
    html: str
    category: Optional[str] = None


class CompareRequest(BaseModel):
    products: list[Product]
    priorities: Optional[dict[str, float]] = None


def _check_category(cat: Optional[str]) -> None:
    if cat is not None and cat not in CATEGORIES:
        raise HTTPException(422, f"category must be one of {CATEGORIES}")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/methodology")
def methodology() -> dict:
    """Published, versioned methodology (doc section 13.4): weights, thresholds, claim rules."""
    return {"scoring": scoring_config(), "thresholds": thresholds(), "claim_rules": claim_rules(),
            "category_weights": read_csv("category_weights.csv"), "categories": CATEGORIES}


@app.post("/analyse/url")
def analyse_from_url(req: UrlRequest) -> dict:
    _check_category(req.category)
    try:
        return analyse_url(str(req.url), req.category, req.use_cache)
    except FetchBlocked as e:
        raise HTTPException(403, str(e))
    except Exception as e:  # network or HTTP errors from the target site
        raise HTTPException(502, f"could not fetch the page: {e}")


@app.post("/analyse/html")
def analyse_from_html(req: HtmlRequest) -> dict:
    """Analyse a page you already have (saved page, demo cache)."""
    _check_category(req.category)
    return analyse_html(req.html, req.url, req.category)


@app.post("/analyse/product")
def analyse_from_product(product: Product) -> dict:
    """Analyse a product entered as structured fields (e.g. from the verified set)."""
    return analyse_product(product)


@app.post("/compare")
def compare_products(req: CompareRequest) -> dict:
    try:
        return compare(req.products, req.priorities)
    except ValueError as e:
        raise HTTPException(422, str(e))
