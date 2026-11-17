"""Find any product, bring it in from Open Food Facts, and track its prices.

* ``search``: stored products plus live Open Food Facts results (India first, then worldwide), so a
  product that has not been analysed yet can still be found by name, brand or barcode.
* ``import_off``: fetch one product from the Open Food Facts API by barcode, store it with its
  minerals and vitamins, and score it. Open Food Facts is the registered, permitted product source
  (acquisition/registry.py); its API is used with an identifying User-Agent and within its published
  rate limits (search 10/min, product 100/min). Data is ODbL: credit it.
* ``price_summary`` / ``add_price``: every price is a dated observation with its shop and source.
  Prices are typed in by a person who saw them (no shop is scraped), or come from the labelled
  synthetic demo records. Nothing here is a live retailer price.
"""
from __future__ import annotations

import re
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.schema import Evidence, EvidenceLabel
from database import repository as repo
from database.ingest import OFF_PRODUCT_URL, category_for, to_extraction
from database.models import PriceObservation, ProductRow
from normalise.build import build_product, categorise
from normalise.units import parse_pack_size, price_per_100

OFF_BASE = "https://world.openfoodfacts.org"
OFF_SEARCH = "https://search.openfoodfacts.org/search"  # Open Food Facts' own search service
USER_AGENT = "FoodDecisionIntelligence/0.1 (academic project, MSIT GGSIPU)"
OFF_FIELDS = ("code,product_name,brands,quantity,categories_tags,countries_tags,ingredients_text,labels,"
              "nutriments,nutriscore_grade,last_modified_t,image_front_url,image_url")
SEARCH_LIMIT_PER_MIN = 10
PRODUCT_LIMIT_PER_MIN = 100

# Minerals, vitamins and other nutrients Open Food Facts may hold (per 100 g/ml), shown but not scored.
MICRONUTRIENTS = {
    "calcium": ("Calcium", "mg", "mineral"), "iron": ("Iron", "mg", "mineral"),
    "magnesium": ("Magnesium", "mg", "mineral"), "phosphorus": ("Phosphorus", "mg", "mineral"),
    "potassium": ("Potassium", "mg", "mineral"), "zinc": ("Zinc", "mg", "mineral"),
    "copper": ("Copper", "mg", "mineral"), "manganese": ("Manganese", "mg", "mineral"),
    "selenium": ("Selenium", "µg", "mineral"), "iodine": ("Iodine", "µg", "mineral"),
    "vitamin-a": ("Vitamin A", "µg", "vitamin"), "vitamin-c": ("Vitamin C", "mg", "vitamin"),
    "vitamin-d": ("Vitamin D", "µg", "vitamin"), "vitamin-e": ("Vitamin E", "mg", "vitamin"),
    "vitamin-b1": ("Vitamin B1 (thiamin)", "mg", "vitamin"), "vitamin-b2": ("Vitamin B2 (riboflavin)", "mg", "vitamin"),
    "vitamin-pp": ("Niacin (B3)", "mg", "vitamin"), "vitamin-b6": ("Vitamin B6", "mg", "vitamin"),
    "vitamin-b9": ("Folate (B9)", "µg", "vitamin"), "vitamin-b12": ("Vitamin B12", "µg", "vitamin"),
    "cholesterol": ("Cholesterol", "mg", "other"), "caffeine": ("Caffeine", "mg", "other"),
    "polyunsaturated-fat": ("Polyunsaturated fat", "g", "other"),
    "monounsaturated-fat": ("Monounsaturated fat", "g", "other"),
}
_UNIT_FACTOR = {"g": {"g": 1.0, "mg": 1000.0, "µg": 1e6}, "mg": {"g": 0.001, "mg": 1.0, "µg": 1000.0},
                "µg": {"g": 1e-6, "mg": 0.001, "µg": 1.0}}

RETAILERS = {"blinkit": "Blinkit", "zepto": "Zepto", "instamart": "Swiggy Instamart", "bigbasket": "BigBasket",
             "amazon": "Amazon", "jiomart": "JioMart", "flipkart": "Flipkart Minutes", "dmart": "DMart",
             "shop": "Local shop", "pack mrp": "MRP printed on pack", "brand website": "Brand website",
             "other": "Other", "synthetic": "Synthetic demo price"}
# How each kind of price came in, strongest evidence first. The kind is the text after the last comma of
# price_observation.source, so it is stored with every observation.
EVIDENCE_KINDS = {
    "invoice-backed purchase": ("invoice", "Paid price on a purchase invoice"),
    "mrp on invoice": ("invoice", "MRP printed on a purchase invoice"),
    "entered in app by hand": ("hand", "Typed in by a user who saw the price"),
    "recorded by hand": ("hand", "Recorded by hand from the shop or pack"),
    "workbook observation, unverified": ("unverified", "From a research workbook; not checked against the shop"),
}


class CatalogError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class _Limiter:
    """Sliding one-minute window shared by all requests of this API process."""

    def __init__(self, per_minute: int):
        self.per_minute, self.hits, self.lock = per_minute, deque(), threading.Lock()

    def take(self) -> bool:
        with self.lock:
            now = time.monotonic()
            while self.hits and now - self.hits[0] > 60:
                self.hits.popleft()
            if len(self.hits) >= self.per_minute:
                return False
            self.hits.append(now)
            return True


_search_limit = _Limiter(SEARCH_LIMIT_PER_MIN)
_product_limit = _Limiter(PRODUCT_LIMIT_PER_MIN)
_search_cache: dict[str, tuple[float, list[dict]]] = {}


def _client(client: Optional[httpx.Client]) -> httpx.Client:
    return client or httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20, follow_redirects=False)


# ------------------------------------------------------------------ micronutrients

def micronutrients_from(nutriments: dict) -> dict:
    """{key: {label, value, unit, group}} per 100 g/ml for the nutrients OFF holds. Missing stays missing."""
    out = {}
    for key, (label, unit, group) in MICRONUTRIENTS.items():
        v = nutriments.get(f"{key}_100g")
        if v in (None, ""):
            continue
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        if v < 0:
            continue
        # OFF stores *_100g in grams whatever the display unit; convert to the unit people read.
        value = v * _UNIT_FACTOR["g"][unit]
        out[key] = {"label": label, "value": round(value, 4), "unit": unit, "group": group,
                    "source": "Open Food Facts nutriments (declared by contributors)"}
    return out


# ------------------------------------------------------------------ search

def _stored_matches(s: Session, q: str, limit: int) -> list[dict]:
    ql = q.lower().strip()
    out = []
    for row, res in repo.latest_analyses(s):
        hay = f"{row.brand or ''} {row.name or ''}".lower()
        if all(tok in hay for tok in ql.split()):
            out.append({"product_id": row.id, "name": row.name, "brand": row.brand, "barcode": row.barcode,
                        "category": row.category, "overall": res.overall_score, "grade": res.grade,
                        "status": res.status, "price_per_100": res.price_per_100,
                        "pack_size": row.pack_size, "pack_unit": row.pack_unit,
                        "price_inr": row.prices[-1].price_inr if row.prices else None,
                        "price_retailer": row.prices[-1].source if row.prices else None,
                        "price_evidence": row.prices[-1].evidence_status if row.prices else None,
                        "source_url": row.sources[-1].source_url if row.sources else None,
                        "collected_at": row.sources[-1].collected_at.isoformat() if row.sources else None,
                        "is_synthetic": repo.is_synthetic(row), "stored": True,
                        "image_url": ((row.field_evidence or {}).get("image_local") or {}).get("value")
                        or ((row.field_evidence or {}).get("image_url") or {}).get("value")})
            if len(out) >= limit:
                break
    return out


def _off_search(q: str, client: Optional[httpx.Client], page_size: int, india_only: bool) -> list[dict]:
    """Open Food Facts search service (search.openfoodfacts.org), falling back to the classic search.pl."""
    key = f"{q.lower().strip()}|{india_only}|{page_size}"
    hit = _search_cache.get(key)
    if hit and time.monotonic() - hit[0] < 600:
        return hit[1]
    if not _search_limit.take():
        raise CatalogError(429, "rate_limited", "Open Food Facts allows 10 searches a minute. Wait a moment and try again.")
    fields = "code,product_name,brands,quantity,nutriscore_grade,image_front_small_url,categories_tags"
    c = _client(client)
    products: list[dict] = []
    try:
        query = q.replace('"', " ") + (' countries_tags:"en:india"' if india_only else "")
        r = c.get(OFF_SEARCH, params={"q": query, "page_size": page_size, "fields": fields})
        r.raise_for_status()
        for h in r.json().get("hits", []):
            brands = h.get("brands")
            h["brands"] = ", ".join(brands) if isinstance(brands, list) else brands
            products.append(h)
    except (httpx.HTTPError, ValueError):
        try:
            params = {"search_terms": q, "search_simple": 1, "json": 1, "page_size": page_size, "fields": fields}
            if india_only:
                params["countries_tags_en"] = "india"
            r = c.get(f"{OFF_BASE}/cgi/search.pl", params=params)
            r.raise_for_status()
            products = r.json().get("products", [])
        except (httpx.HTTPError, ValueError) as exc:
            raise CatalogError(502, "source_fetch_failed",
                               f"Open Food Facts search could not be reached ({type(exc).__name__}). "
                               "Stored products are still shown.") from exc
    _search_cache[key] = (time.monotonic(), products)
    return products


def search(s: Session, q: str, *, include_online: bool = True, limit: int = 20,
           client: Optional[httpx.Client] = None) -> dict:
    q = (q or "").strip()
    if len(q) < 2:
        raise CatalogError(422, "validation_error", "Type at least two characters of a product name, brand or barcode.")
    stored = _stored_matches(s, q, limit)
    online, notes = [], []
    if include_online:
        try:
            raw = _off_search(q, client, limit, india_only=True)
            if len(raw) < 3:
                raw += _off_search(q, client, limit, india_only=False)
            stored_codes = {r["barcode"] for r in stored if r.get("barcode")}
            seen = set()
            for p in raw:
                code = str(p.get("code") or "")
                if not code or code in seen or not p.get("product_name"):
                    continue
                seen.add(code)
                existing = s.scalar(select(ProductRow.id).where(ProductRow.external_product_id == f"off:{code}"))
                if code in stored_codes:
                    continue
                online.append({"barcode": code, "name": p.get("product_name"),
                               "brand": (p.get("brands") or "").split(",")[0].strip() or None,
                               "quantity": p.get("quantity") or None,
                               "nutriscore_grade": p.get("nutriscore_grade") or None,
                               "image_url": p.get("image_front_small_url") or p.get("image_front_url") or None,
                               "product_id": existing, "stored": existing is not None,
                               "source_url": OFF_PRODUCT_URL.format(code=code)})
                if len(online) >= limit:
                    break
        except CatalogError as e:
            notes.append(e.message)
    return {"query": q, "stored": stored, "online": online, "notes": notes,
            "attribution": "Online results: Open Food Facts (ODbL), crowdsourced; values are not checked against the pack."}


# ------------------------------------------------------------------ import from Open Food Facts

def fetch_off_product(code: str, client: Optional[httpx.Client] = None) -> Optional[dict]:
    if not re.fullmatch(r"\d{4,14}", code or ""):
        raise CatalogError(422, "validation_error", "A barcode is 4 to 14 digits.")
    if not _product_limit.take():
        raise CatalogError(429, "rate_limited", "Too many product lookups this minute. Wait a moment and try again.")
    try:
        r = _client(client).get(f"{OFF_BASE}/api/v2/product/{code}.json", params={"fields": OFF_FIELDS})
    except httpx.HTTPError as exc:
        raise CatalogError(502, "source_fetch_failed",
                           f"Open Food Facts could not be reached ({type(exc).__name__}).") from exc
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        raise CatalogError(502, "source_fetch_failed", f"Open Food Facts answered HTTP {r.status_code}.")
    data = r.json()
    return data.get("product") if data.get("status") == 1 else None


def store_off_record(s: Session, p: dict) -> ProductRow:
    """Store one Open Food Facts product JSON (any category) with its micronutrients."""
    code = str(p.get("code"))
    tags = p.get("categories_tags") or []
    cat = category_for(tags) or categorise(p.get("product_name"), " ".join(tags).replace("en:", " ").replace("-", " "))
    product = build_product([to_extraction(p)], url=OFF_PRODUCT_URL.format(code=code), category_override=None)
    product.category = (Evidence(value=cat, label=EvidenceLabel.INTERPRETED, source="off_category_map.csv / keywords",
                                 note="mapped from Open Food Facts categories and the product name")
                        if cat else Evidence(note="category outside the five scored categories"))
    image = p.get("image_front_url") or p.get("image_url")
    if image and str(image).startswith("https://"):
        product.image_url = Evidence(value=image, label=EvidenceLabel.DECLARED, source="open-food-facts",
                                     note="image reference only; not downloaded or checked")
    if p.get("last_modified_t"):
        product.collected_at = datetime.fromtimestamp(int(p["last_modified_t"]), timezone.utc).isoformat()
    row = repo.save_product(
        s, product, source_type="open_food_facts", external_id=f"off:{code}", barcode=code,
        extraction_method="off-api",
        extraction_log=[{"step": "open-food-facts-api", "outcome": "ok",
                         "detail": f"product {code} fetched from the Open Food Facts API (ODbL), crowdsourced "
                                   "reference data; values are not checked against the pack"}])
    ev = dict(row.field_evidence or {})
    ev["micronutrients"] = micronutrients_from(p.get("nutriments") or {})
    if p.get("nutriscore_grade"):
        ev["off_nutriscore_grade"] = {"value": p["nutriscore_grade"], "label": "declared",
                                      "source": "open-food-facts", "note": "computed by Open Food Facts"}
    row.field_evidence = ev
    s.flush()
    return row


def import_off(s: Session, code: str, client: Optional[httpx.Client] = None) -> dict:
    from services import analyse_row, payload
    p = fetch_off_product(code.strip(), client)
    if p is None:
        raise CatalogError(404, "not_found", f"Open Food Facts has no product with barcode {code}. "
                                             "Try a product URL, a photo of the pack, or manual entry.")
    if not p.get("product_name"):
        raise CatalogError(422, "product_extraction_failed",
                           "Open Food Facts has this barcode but no product name. Try a photo of the pack or manual entry.")
    row = store_off_record(s, p)
    report = analyse_row(s, row)
    return payload(row, report)


# ------------------------------------------------------------------ prices

def _retailer_of(source: Optional[str]) -> tuple[str, str]:
    """(key, label) of the shop named at the start of a price source."""
    text = (source or "").strip()
    low = text.lower()
    if "synthetic" in low:
        return "synthetic", RETAILERS["synthetic"]
    for key, label in RETAILERS.items():
        if low.startswith(key) or low.startswith(label.lower()):
            return key, label
    name = re.split(r"\s*\(|,", text, maxsplit=1)[0].strip() or "Other"
    return name.lower(), name


def _evidence_of(source: Optional[str], synthetic: bool) -> tuple[str, str]:
    if synthetic:
        return "synthetic", "Made-up demo price"
    kind = (source or "").rsplit(",", 1)[-1].strip().lower()
    return EVIDENCE_KINDS.get(kind, ("unverified", "Source not stated"))


def _iso(d: Optional[datetime]) -> Optional[str]:
    if d is None:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.isoformat()


def price_summary(s: Session, product_id: int) -> Optional[dict]:
    row = repo.get_row(s, product_id)
    if row is None:
        return None
    synthetic = repo.is_synthetic(row)
    per = "100 ml" if row.pack_unit == "ml" or row.nutrition_basis == "per_100ml" else "100 g"
    observations = []
    def when(o):
        d = o.observed_at or datetime.min
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

    labels: dict[str, str] = {}
    for o in sorted(row.prices, key=when):
        key, label = ("synthetic", RETAILERS["synthetic"]) if synthetic else _retailer_of(o.source)
        labels[key] = label
        ev, ev_text = _evidence_of(o.source, synthetic)
        observations.append({
            "id": o.id, "retailer": key, "retailer_label": label,
            "price_inr": o.price_inr, "pack_size": o.pack_size, "pack_unit": o.pack_unit,
            "price_per_100": o.price_per_100g_or_ml, "observed_at": _iso(o.observed_at),
            "source": o.source, "source_url": o.source_url, "evidence": ev, "evidence_text": ev_text,
            "is_mrp": key == "pack mrp" or "mrp on invoice" in (o.source or "").lower(), "outlier": False,
        })
    selling = [o for o in observations if not o["is_mrp"]]
    units = sorted(o["price_per_100"] for o in selling if o["price_per_100"] is not None)
    if len(units) >= 3:
        mid = units[len(units) // 2]
        for o in selling:
            u = o["price_per_100"]
            if u is not None and mid and (u < 0.5 * mid or u > 1.8 * mid):
                o["outlier"] = True
    by_retailer: dict[str, list[dict]] = {}
    for ob in selling:
        by_retailer.setdefault(ob["retailer"], []).append(ob)
    retailers = []
    for key, obs in by_retailer.items():
        units = [o["price_per_100"] for o in obs if o["price_per_100"] is not None]
        first, last = obs[0], obs[-1]
        change = (last["price_inr"] - first["price_inr"]) if len(obs) > 1 else None
        retailers.append({
            "retailer": key, "retailer_label": labels.get(key, key.title()), "observations": len(obs),
            "evidence": obs[-1]["evidence"], "outlier": obs[-1]["outlier"],
            "latest_price_inr": last["price_inr"], "latest_price_per_100": last["price_per_100"],
            "latest_observed_at": last["observed_at"], "pack_size": last["pack_size"], "pack_unit": last["pack_unit"],
            "lowest_price_per_100": min(units) if units else None, "highest_price_per_100": max(units) if units else None,
            "change_inr": round(change, 2) if change is not None else None,
            "change_percent": round(100 * change / first["price_inr"], 1) if change is not None and first["price_inr"] else None,
            "trend": (None if change is None else "up" if change > 0 else "down" if change < 0 else "flat"),
            "source_url": last["source_url"],
        })
    current = [r for r in retailers if r["latest_price_per_100"] is not None and not r["outlier"]]
    cheapest = min(current, key=lambda r: r["latest_price_per_100"]) if current else None
    dearest = max(current, key=lambda r: r["latest_price_per_100"]) if current else None
    spread = None
    if cheapest and dearest and len(current) > 1:
        diff = dearest["latest_price_per_100"] - cheapest["latest_price_per_100"]
        spread = {"cheapest": cheapest["retailer_label"], "dearest": dearest["retailer_label"],
                  "difference_per_100": round(diff, 2),
                  "difference_percent": round(100 * diff / cheapest["latest_price_per_100"], 1)
                  if cheapest["latest_price_per_100"] else None}
    peers = repo.peer_unit_prices(s, row.category, row.nutrition_basis, exclude_id=row.id)
    from statistics import median
    med = round(median(peers), 2) if peers else None
    latest_unit = selling[-1]["price_per_100"] if selling else None
    mrp = next((o for o in reversed(observations) if o["is_mrp"]), None)
    vs_category = None
    if med and latest_unit is not None:
        vs_category = {"category_median_per_100": med, "peer_count": len(peers),
                       "difference_percent": round(100 * (latest_unit - med) / med, 1)}
    notes = ["Every price is a dated observation with its source: a purchase invoice, a person who typed it in, "
             "a research workbook (unverified) or labelled demo data. No shop is scraped, so none of these is a live price."]
    if any(o["outlier"] for o in selling):
        notes.append("Prices marked 'check' are far from this product's other prices (under half or nearly double "
                     "the middle price) and are left out of the cheapest-shop comparison.")
    if any(o["evidence"] == "unverified" for o in selling):
        notes.append("Workbook prices are unverified: they were not checked against the shop.")
    if synthetic:
        notes.append("This is a synthetic demo product: its prices are made up to show how the comparison works.")
    if not observations:
        notes.append("No price recorded yet. Add one from Blinkit, Zepto, Instamart, a shop or the pack MRP.")
    return {"product_id": row.id, "basis": per, "is_synthetic": synthetic, "observations": observations,
            "retailers": sorted(retailers, key=lambda r: (r["latest_price_per_100"] is None, r["latest_price_per_100"] or 0)),
            "cheapest": cheapest["retailer_label"] if cheapest else None, "spread": spread,
            "vs_category": vs_category, "notes": notes,
            "mrp": ({"price_inr": mrp["price_inr"], "observed_at": mrp["observed_at"], "evidence_text": mrp["evidence_text"]}
                    if mrp else None),
            "retailer_options": {k: v for k, v in RETAILERS.items() if k != "synthetic"}}


def add_price(s: Session, product_id: int, values: dict) -> dict:
    from services import analyse_row
    row = repo.get_row(s, product_id)
    if row is None:
        raise CatalogError(404, "not_found", f"No stored product with id {product_id}.")
    if repo.is_synthetic(row):
        raise CatalogError(422, "validation_error", "Synthetic demo products cannot take real prices.")
    retailer = (values.get("retailer") or "").strip().lower()
    if retailer not in RETAILERS or retailer == "synthetic":
        raise CatalogError(422, "validation_error", "Choose the shop the price was seen at.")
    price = values.get("price_inr")
    if price is None or price <= 0:
        raise CatalogError(422, "validation_error", "Enter the selling price in rupees.")
    size_text = (values.get("pack_size_text") or "").strip()
    if size_text:
        size = parse_pack_size(size_text)
        if not size:
            raise CatalogError(422, "validation_error", "Pack size not understood; write it like 200 g or 1 l.")
    elif row.pack_size and row.pack_unit:
        size = (row.pack_size, row.pack_unit)
    else:
        raise CatalogError(422, "validation_error", "Enter the pack size the price is for (for example 200 g).")
    when = values.get("observed_at") or datetime.now(timezone.utc)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    if when > datetime.now(timezone.utc):
        raise CatalogError(422, "validation_error", "The date the price was seen cannot be in the future.")
    place = (values.get("place") or "").strip()[:60]
    url = (values.get("listing_url") or "").strip()
    url = url if url.startswith(("https://", "http://")) else None
    source = f"{RETAILERS[retailer]}{f' ({place})' if place else ''}, entered in app by hand"
    s.add(PriceObservation(product_id=row.id, price_inr=float(price), pack_size=size[0], pack_unit=size[1],
                           price_per_100g_or_ml=round(price_per_100(float(price), size[0]), 2),
                           source=source, source_url=url, evidence_status="declared", observed_at=when))
    s.flush()
    s.refresh(row)
    analyse_row(s, row)
    return price_summary(s, product_id)
