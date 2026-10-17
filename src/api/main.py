"""FastAPI app. Run: uvicorn api.main:app --app-dir src --reload  (OpenAPI docs at /docs)."""
from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque
from typing import Any, Literal, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import OperationalError

import services
from core.config import claim_rules, read_csv, scoring_config, thresholds
from core.schema import CATEGORIES
from database import repository as repo
from database.session import DatabaseNotConfigured, session_factory
from extract.fetch import FetchError
from recommend.alternatives import PREFERENCES, alternatives, compare_stored

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("fdi.api")

MAX_BODY_BYTES = int(os.environ.get("MAX_REQUEST_BYTES", 65536))
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 9 * 1024 * 1024))  # photos up to 8 MB plus form fields
UPLOAD_PATHS = {"/api/analyze-upload"}
RATE_LIMIT = int(os.environ.get("RATE_LIMIT_PER_MINUTE", 10))
VERSION = scoring_config()["methodology_version"]

app = FastAPI(title="Food Decision Intelligence API", version=VERSION,
              description="Understand. Evaluate. Compare. Decide. Consumer decision support for packaged food "
                          "in India. Not a medical or clinical score.")
app.add_middleware(CORSMiddleware,
                   allow_origins=[o for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if o],
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


# ------------------------------------------------------------------ errors, limits, logging

def error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status, {"code": code, "message": message})


@app.exception_handler(RequestValidationError)
async def _validation(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(x) for x in first.get("loc", []) if x != "body")
    return JSONResponse(status_code=422, content={"detail": {
        "code": "validation_error", "message": f"{where}: {first.get('msg', 'invalid request')}".strip(": ")}})


@app.exception_handler(FetchError)
async def _fetch_error(request: Request, exc: FetchError):
    log.info("fetch refused code=%s message=%s", exc.code, exc.message)
    return JSONResponse(status_code=exc.http_status, content={"detail": {"code": exc.code, "message": exc.message}})


@app.exception_handler(DatabaseNotConfigured)
@app.exception_handler(OperationalError)
async def _db_error(request: Request, exc: Exception):
    log.warning("database unavailable: %s", type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": {
        "code": "database_unavailable",
        "message": "The API is running but cannot reach the database. Check that PostgreSQL is running and that "
                   "DATABASE_URL in .env is right, then run ./run.sh migrate and ./run.sh seed."}})


@app.exception_handler(Exception)
async def _unexpected(request: Request, exc: Exception):
    # Anything not handled above: log the traceback, answer with the usual error shape instead of a bare 500.
    log.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": {
        "code": "internal_error",
        "message": f"The analysis failed with an unexpected error ({type(exc).__name__}). "
                   "The API terminal shows the details."}})


@app.middleware("http")
async def limits_and_logging(request: Request, call_next):
    started = time.perf_counter()
    length = request.headers.get("content-length")
    limit = MAX_UPLOAD_BYTES if request.url.path in UPLOAD_PATHS else MAX_BODY_BYTES
    if request.url.path in UPLOAD_PATHS and not (length and length.isdigit()):
        return JSONResponse(status_code=411, content={"detail": {
            "code": "length_required", "message": "Uploads need a Content-Length header."}})
    if length and length.isdigit() and int(length) > limit:
        return JSONResponse(status_code=413, content={"detail": {
            "code": "too_large", "message": f"Request body over {limit} bytes."}})
    response = await call_next(request)
    log.info("%s %s -> %s in %.0f ms", request.method, request.url.path, response.status_code,
             (time.perf_counter() - started) * 1000)
    return response


_hits: dict[str, deque] = defaultdict(deque)


def rate_limited(request: Request) -> None:
    """Simple per-client sliding window for the endpoint that fetches external pages."""
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    q = _hits[key]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        raise error(429, "rate_limited", f"At most {RATE_LIMIT} analyses per minute. Please wait and try again.")
    q.append(now)


def db():
    s = session_factory()()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


# ------------------------------------------------------------------ schemas

Category = Literal["biscuits_cookies", "breakfast_cereals", "instant_noodles", "beverages", "namkeen_chips"]


class AnalyzeUrlRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=2048, examples=["https://brand.example/products/cereal"])
    category: Optional[Category] = None
    refresh: bool = Field(False, description="Fetch again instead of using the cached page")


class SourceInfo(BaseModel):
    source_type: str
    source_url: Optional[str]
    site: Optional[str] = None
    extraction_method: Optional[str]
    collected_at: Optional[str]
    last_verified_at: Optional[str]
    source_reliability: str


class LogStep(BaseModel):
    step: str
    outcome: str
    detail: str


class ProductAnalysis(BaseModel):
    product_id: int
    status: Literal["complete", "partial", "insufficient_data"]
    is_synthetic: bool
    source: SourceInfo
    missing_fields: list[str]
    conflicts: list[str]
    extraction_log: list[LogStep]
    methodology_version: str
    report: dict[str, Any] = Field(description="Full explainable report; see docs/api.md")


class ProductSummary(BaseModel):
    product_id: int
    name: Optional[str]
    brand: Optional[str]
    category: Optional[str]
    pack_size: Optional[float]
    pack_unit: Optional[str]
    price_per_100: Optional[float]
    overall: Optional[int]
    grade: Optional[str]
    status: str
    source_type: str
    is_synthetic: bool
    source_url: Optional[str]
    collected_at: Optional[str]


class ProductList(BaseModel):
    products: list[ProductSummary]
    total: int


class CompareRequest(BaseModel):
    product_ids: list[int] = Field(..., min_length=2, max_length=6)
    priorities: Optional[dict[Literal["nutrition", "ingredients", "transparency", "claims", "value"],
                              float]] = None


class Pick(BaseModel):
    product_id: int
    reason: str
    name: Optional[str] = None
    brand: Optional[str] = None
    is_synthetic: Optional[bool] = None


class CompareResponse(BaseModel):
    category: Optional[str]
    basis: Optional[str]
    methodology_version: str
    priorities: dict[str, float]
    products: list[dict[str, Any]]
    ingredient_differences: dict[str, Any]
    picks: dict[str, Optional[Pick]]
    rationale: list[str]


class Alternative(BaseModel):
    product_id: int
    rank: int
    name: Optional[str]
    brand: Optional[str]
    is_synthetic: bool
    overall: Optional[int]
    grade: Optional[str]
    nutrition: Optional[float]
    transparency: Optional[float]
    price_per_100: Optional[float]
    similarity: Optional[float]
    preference_score: Optional[float]
    matching_attributes: list[str]
    rationale: str
    source_url: Optional[str]
    site: Optional[str] = None
    collected_at: Optional[str]


class AlternativesResponse(BaseModel):
    source_product_id: int
    preference: str
    methodology_version: str
    eligible_count: int
    alternatives: list[Alternative]
    picks: dict[str, Optional[Pick]]
    message: Optional[str]
    site: Optional[str] = Field(None, description="Shop the product was analysed from, if known")
    scope: Literal["same_site", "all"] = Field("all", description="Where the alternatives were drawn from")


class CategoryInfo(BaseModel):
    id: str
    label: str
    product_count: int


class Health(BaseModel):
    status: str
    database: Literal["ok", "unavailable"]
    methodology_version: str
    product_count: Optional[int]


# ------------------------------------------------------------------ endpoints

@app.get("/api/health", response_model=Health, tags=["reference"])
def health() -> dict:
    try:
        s = session_factory()()
        try:
            count = repo.count_products(s)
        finally:
            s.close()
        return {"status": "ok", "database": "ok", "methodology_version": VERSION, "product_count": count}
    except (DatabaseNotConfigured, OperationalError):
        return {"status": "degraded", "database": "unavailable", "methodology_version": VERSION,
                "product_count": None}


@app.post("/api/analyze-url", response_model=ProductAnalysis, tags=["analysis"],
          dependencies=[Depends(rate_limited)])
def analyze_url(req: AnalyzeUrlRequest, s=Depends(db)) -> dict:
    """Fetch a product page, extract, normalise, store and score it."""
    return services.analyze_url(s, req.url.strip(), req.category, req.refresh)


@app.post("/api/analyze-upload", response_model=ProductAnalysis, tags=["analysis"],
          dependencies=[Depends(rate_limited)])
async def analyze_upload(file: UploadFile = File(..., description="Pack photo, app screenshot, or saved product page (.html)"),
                         page_url: Optional[str] = Form(None, max_length=2048,
                                                        description="Where the product was listed, if known"),
                         site: Optional[str] = Form(None, max_length=100,
                                                    description="Shop it is from, e.g. blinkit.com or zeptonow.com"),
                         category: Optional[Category] = Form(None),
                         name: Optional[str] = Form(None, max_length=200,
                                                    description="Product name, if the image does not show it"),
                         s=Depends(db)) -> dict:
    """Read a photo or a saved page (nothing is fetched), then normalise, store and score it like a URL."""
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise error(413, "too_large", f"File over {MAX_UPLOAD_BYTES} bytes.")
    try:
        return services.analyze_upload(s, data, file.filename or "", file.content_type, page_url or None,
                                       site or None, category, name=name or None)
    except services.UploadError as e:
        raise error(e.status, e.code, e.message)


@app.get("/api/products", response_model=ProductList, tags=["products"])
def list_products(category: Optional[Category] = None, q: Optional[str] = Query(None, max_length=100),
                  limit: int = Query(50, ge=1, le=500), s=Depends(db)) -> dict:
    return services.list_products(s, category, q, limit)


@app.get("/api/products/{product_id}", response_model=ProductAnalysis, tags=["products"])
def get_product(product_id: int, s=Depends(db)) -> dict:
    out = services.get_analysis(s, product_id)
    if out is None:
        raise error(404, "not_found", f"No stored product with id {product_id}.")
    return out


@app.post("/api/products/compare", response_model=CompareResponse, tags=["products"])
def compare(req: CompareRequest, s=Depends(db)) -> dict:
    try:
        return compare_stored(s, req.product_ids, req.priorities)
    except LookupError as e:
        raise error(404, "not_found", str(e).strip("'\""))
    except ValueError as e:
        raise error(422, "validation_error", str(e))


@app.get("/api/products/{product_id}/alternatives", response_model=AlternativesResponse, tags=["products"])
def get_alternatives(product_id: int, preference: Literal["balanced", "nutrition", "price", "transparency"] = "balanced",
                     limit: int = Query(5, ge=1, le=20),
                     scope: Literal["same_site", "all"] = Query("same_site", description="same_site falls back to "
                                                                "all stored products when nothing qualifies"),
                     s=Depends(db)) -> dict:
    out = alternatives(s, product_id, preference, limit, scope=scope)
    if out is None:
        raise error(404, "not_found", f"No stored product with id {product_id}.")
    return out


@app.get("/api/reference/categories", tags=["reference"])
def categories(s=Depends(db)) -> dict:
    counts: dict[str, int] = {}
    for row, _ in repo.latest_analyses(s):
        if row.category:
            counts[row.category] = counts.get(row.category, 0) + 1
    labels = {"biscuits_cookies": "Biscuits and cookies", "breakfast_cereals": "Breakfast cereals",
              "instant_noodles": "Instant noodles", "beverages": "Beverages", "namkeen_chips": "Namkeen and chips"}
    return {"categories": [CategoryInfo(id=c, label=labels[c], product_count=counts.get(c, 0)).model_dump()
                           for c in CATEGORIES]}


EVIDENCE_LABELS = {
    "declared": "Stated on the product listing or package.",
    "derived": "Calculated from declared data (for example sodium from salt, or per 100 g from per serving).",
    "interpreted": "Judged against a defined benchmark or keyword rule (for example the category).",
    "verified": "Checked against an authoritative source (the verified evaluation set).",
    "unknown": "Cannot be established from available evidence. Shown as unknown, never as zero.",
}
CLAIM_STATUSES = {
    "consistent with available evidence": "The declared values meet the FSSAI condition for this claim.",
    "requires context": "The claim may be accurate but needs extra context or a qualifying statement.",
    "potential inconsistency for review": "The declared values do not meet the recorded condition. This is a "
                                          "prompt for review, not an accusation.",
    "cannot be verified from available information": "A value or condition needed for the check is missing.",
}
LIMITATIONS = [
    "Methodology v0.1.0 is a prototype: weights and curves are design choices to be calibrated, not validated science.",
    "Red (high) nutrient bounds use the UK FSA 2016 scheme as a labelled placeholder; FSSAI has no final 'high' cut-offs.",
    "FSSAI front-of-pack warning thresholds are not published, so the warning simulation is not run.",
    "Extraction accuracy has not been measured on a verified set yet; see notebooks/evaluation.ipynb for what is measured.",
    "Label photos are read offline with Tesseract OCR, or by a vision model when an Anthropic API key is set. "
    "Either can misread a label, so check the text in the extraction log against the pack. Accuracy on photos "
    "has not been measured.",
    "Same-site alternatives come only from products already analysed from that site; the shop's catalogue is "
    "not crawled.",
    "Barcode scanning, cross-source validation, personalisation and lab evidence are future work.",
    "The score is consumer decision support, not a medical or clinical assessment.",
]
DATA_SOURCES = [
    {"name": "Open Food Facts", "licence": "Open Database License (ODbL) 1.0; images CC BY-SA",
     "use": "Baseline product records (scripts/ingest_off.py), reference only; never overwrites a listing."},
    {"name": "FSSAI (Advertising and Claims) Regulations 2018, compendium 14-12-2022", "licence": "Government text",
     "use": "Claim conditions in data/reference/fssai_claims.csv."},
    {"name": "ICMR-NIN Nutrient Requirements 2020", "licence": "Government text",
     "use": "Protein RDA (54 g/day) for converting % RDA claim conditions."},
    {"name": "UK DH/FSA front-of-pack guidance 2016", "licence": "Open Government Licence",
     "use": "Placeholder red bounds for traffic lights."},
    {"name": "Synthetic demo records (data/sample/)", "licence": "Project-generated",
     "use": "Illustrative records so the app runs offline; labelled synthetic everywhere."},
]


@app.get("/api/reference/methodology", tags=["reference"])
def methodology() -> dict:
    cfg = scoring_config()
    return {"version": cfg["methodology_version"], "dimension_weights": cfg["dimension_weights"],
            "grade_bands": cfg["grade_bands"], "scoring": cfg, "thresholds": thresholds(),
            "claim_rules": claim_rules(), "category_weights": read_csv("category_weights.csv"),
            "evidence_labels": EVIDENCE_LABELS, "claim_statuses": CLAIM_STATUSES,
            "missing_data": ["Missing values stay unknown and are never treated as zero.",
                             f"Nutrition needs at least {cfg['min_nutrition_coverage']:.0%} of its weighted nutrients; "
                             "otherwise no overall score is given.",
                             "Dimensions that cannot be scored are left out and the remaining weights renormalised; "
                             "the report says which."],
            "freshness": "Each product shows when it was collected; prices are stored as dated observations.",
            "data_sources": DATA_SOURCES, "limitations": LIMITATIONS}
