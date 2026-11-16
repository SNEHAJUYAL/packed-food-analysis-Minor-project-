"""Load real price observations: Zepto purchase invoices and the team's multi-retailer workbook.

    ./run.sh market-prices            # or: PYTHONPATH=src python scripts/load_market_prices.py

Inputs (all in data/prices/):
  zepto_invoice_items.csv        item lines copied from the team's Zepto tax invoices (no names or addresses):
                                 paid price and MRP per item, invoice date. Stored as "invoice-backed purchase".
  workbook_retailer_prices.csv   shop prices from authentic_multi_retailer_dataset.xlsx. Not checked against
                                 the shops, so stored as "workbook observation, unverified".
  product_links.csv              which Open Food Facts product each name is (checked by hand), or blank.
  web_sourced_labels.csv         ingredients and nutrition found by web search for products Open Food Facts does not
                                 have, with the page each came from. Stored as web-sourced and unverified.

A linked product is fetched from Open Food Facts (nutrition, ingredients, minerals) and scored. An unlinked
product is stored with only its name, brand and pack size, so its prices still show; it has no nutrition.
Re-running does not duplicate prices. Scores are recomputed at the end so value for money uses the prices.
"""
from __future__ import annotations

import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sqlalchemy import select  # noqa: E402

import catalog  # noqa: E402
from core.schema import Evidence, EvidenceLabel  # noqa: E402
from database import repository as repo  # noqa: E402
from database.models import PriceObservation, ProductRow  # noqa: E402
from database.session import session_scope  # noqa: E402
from normalise.build import build_product, categorise  # noqa: E402
from normalise.units import parse_pack_size, price_per_100  # noqa: E402

DATA = ROOT / "data" / "prices"
RETAILER_NAMES = {"zepto": "Zepto", "instamart": "Swiggy Instamart", "bigbasket.com": "BigBasket",
                  "jiomart grocery": "JioMart", "amazon.in": "Amazon", "dmart ready": "DMart"}


def key(name: str, brand: str) -> str:
    return f"{name.strip().lower()}|{brand.strip().lower()}"


def read(name: str) -> list[dict]:
    with open(DATA / name, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def invoice_only_product(s, name: str, brand: str, size_text: str) -> ProductRow:
    ext = f"invoice:{key(name, brand)}"
    row = s.scalar(select(ProductRow).where(ProductRow.external_product_id == ext))
    if row is not None:
        return row
    product = build_product([{"source": "purchase-invoice", "name": name, "brand": brand,
                              "pack_size_text": size_text or None}])
    cat = categorise(name)
    product.category = (Evidence(value=cat, label=EvidenceLabel.INTERPRETED, source="category_keywords.csv")
                        if cat else Evidence(note="category outside the five scored categories"))
    product.warnings.append("Only the name, brand and pack size are known (from a purchase invoice); "
                            "no nutrition or ingredient data is available for this product yet.")
    return repo.save_product(s, product, source_type="manual", external_id=ext, extraction_method="purchase-invoice",
                             extraction_log=[{"step": "purchase-invoice", "outcome": "ok",
                                              "detail": "name, brand and pack size from a Zepto tax invoice line; "
                                                        "no Open Food Facts record linked"}])


def add_obs(s, row: ProductRow, price: float, size_text: str, when: datetime, source: str, url: str | None) -> bool:
    size = parse_pack_size(size_text) if size_text else None
    if not size and row.pack_size and row.pack_unit:
        size = (row.pack_size, row.pack_unit)
    if not size:
        return False
    exists = s.scalar(select(PriceObservation).where(
        PriceObservation.product_id == row.id, PriceObservation.source == source,
        PriceObservation.observed_at == when, PriceObservation.price_inr == price))
    if exists:
        return False
    s.add(PriceObservation(product_id=row.id, price_inr=price, pack_size=size[0], pack_unit=size[1],
                           price_per_100g_or_ml=round(price_per_100(price, size[0]), 2), source=source,
                           source_url=url if url and url.startswith("https://") else None,
                           evidence_status="declared", observed_at=when))
    return True


def apply_web_labels(s) -> int:
    """Fill invoice-only products with label data found on the web (source page kept, marked unverified)."""
    import json
    from urllib.parse import urlsplit
    n = 0
    for r in read("web_sourced_labels.csv"):
        ext = f"invoice:{key(r['product_name'], r['brand'])}"
        row = s.scalar(select(ProductRow).where(ProductRow.external_product_id == ext))
        if row is None:
            continue
        host = (urlsplit(r["source_url"]).hostname or "web").removeprefix("www.")
        nutrition = json.loads(r["nutrition_json"] or "{}")
        extraction = {"source": f"web:{host}", "name": row.name, "brand": row.brand,
                      "pack_size_text": f"{row.pack_size:g} {row.pack_unit}" if row.pack_size else None,
                      "ingredients_text": r["ingredients"] or None, "nutrition": nutrition,
                      "nutrition_basis_text": r["basis"] or None}
        product = build_product([extraction], url=r["source_url"])
        if row.category:
            product.category = Evidence(value=row.category, label=EvidenceLabel.INTERPRETED,
                                        source="category_keywords.csv")
        product.warnings.append(f"Ingredients and nutrition were found by web search ({r['source_name']}, looked up "
                                f"{r['looked_up_on']}). They are web-sourced and unverified: check them against the pack.")
        prices = list(row.prices)
        new = repo.save_product(s, product, source_type="manual", external_id=ext, extraction_method="web-search",
                                extraction_log=[{"step": "purchase-invoice", "outcome": "ok",
                                                 "detail": "name, brand and pack size from a Zepto tax invoice line"},
                                                {"step": "web-search", "outcome": "ok",
                                                 "detail": f"ingredients/nutrition from {r['source_name']}: {r['source_url']} "
                                                           "(web-sourced, unverified)"}])
        assert new.id == row.id and len(new.prices) == len(prices)
        micro = {}
        for k, (value, unit) in json.loads(r["micronutrients_json"] or "{}").items():
            label, _, group = catalog.MICRONUTRIENTS.get(k, (k.title(), unit, "other"))
            micro[k] = {"label": label, "value": value, "unit": unit, "group": group,
                        "source": f"{r['source_name']} (web-sourced, unverified)"}
        ev = dict(new.field_evidence or {})
        ev["micronutrients"] = micro
        ev["web_source"] = {"value": r["source_url"], "label": "declared", "source": r["source_name"],
                            "note": "web-sourced, unverified"}
        new.field_evidence = ev
        n += 1
    s.flush()
    return n


def main() -> int:
    from services import rescore_all
    links = {key(r["product_name"], r["brand"]): r for r in read("product_links.csv")}
    invoices, workbook = read("zepto_invoice_items.csv"), read("workbook_retailer_prices.csv")
    stats = {"products_from_off": 0, "products_invoice_only": 0, "invoice_prices": 0, "workbook_prices": 0,
             "skipped_no_pack_size": 0}
    rows: dict[str, ProductRow] = {}
    with session_scope() as s:
        def product_for(name: str, brand: str, size_text: str) -> ProductRow:
            k = key(name, brand)
            if k in rows:
                return rows[k]
            code = (links.get(k) or {}).get("off_code", "").strip()
            row = None
            if code:
                existing = s.scalar(select(ProductRow).where(ProductRow.external_product_id == f"off:{code}"))
                if existing is not None:
                    row = existing
                else:
                    p = None
                    for attempt in range(4):  # Open Food Facts answers 429 when busy: wait and retry
                        try:
                            p = catalog.fetch_off_product(code)
                            break
                        except catalog.CatalogError as exc:
                            print(f"  {name}: {exc.message} (attempt {attempt + 1})", flush=True)
                            time.sleep(20 * (attempt + 1))
                    time.sleep(2)
                    if p and p.get("product_name"):
                        row = catalog.store_off_record(s, p)
                        stats["products_from_off"] += 1
            if row is None:
                row = invoice_only_product(s, name, brand, size_text)
                stats["products_invoice_only"] += 1
            rows[k] = row
            return row

        for r in invoices:
            row = product_for(r["product_name"], r["brand"], r["pack_size"])
            when = datetime.strptime(r["invoice_date"], "%Y-%m-%d").replace(hour=12, tzinfo=timezone.utc)
            place = r.get("place") or ""
            src = f"Zepto ({place}), invoice-backed purchase" if place else "Zepto, invoice-backed purchase"
            if add_obs(s, row, float(r["paid_inr"]), r["pack_size"], when, src, None):
                stats["invoice_prices"] += 1
            if r.get("mrp_inr"):
                add_obs(s, row, float(r["mrp_inr"]), r["pack_size"], when, f"Pack MRP ({place}), mrp on invoice", None)
        for r in workbook:
            row = product_for(r["product_name"], r["brand"], r["pack_size"])
            shop = RETAILER_NAMES.get(r["retailer"].strip().lower(), r["retailer"].strip())
            when = datetime.strptime(r["observed_date"], "%Y-%m-%d").replace(hour=12, tzinfo=timezone.utc)
            place = r.get("place") or ""
            src = f"{shop} ({place}), workbook observation, unverified" if place else f"{shop}, workbook observation, unverified"
            if add_obs(s, row, float(r["price_inr"]), r["pack_size"], when, src, r.get("listing_url")):
                stats["workbook_prices"] += 1
            elif not (r["pack_size"] or row.pack_size):
                stats["skipped_no_pack_size"] += 1
        s.flush()
        stats["web_sourced_labels"] = apply_web_labels(s)
        stats["rescored"] = rescore_all(s)
    print(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
