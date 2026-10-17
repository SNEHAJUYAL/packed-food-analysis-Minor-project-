"""Import prices recorded by hand (data/verified/prices/price_entry_sheet.csv) into price_observation.

    PYTHONPATH=src python -m database.prices data/verified/prices/price_entry_sheet.csv

Every stored price keeps its platform, place, observation time and pack size, and gets a price per 100 g
or 100 ml. Rows without a price, a time, a usable pack size or a product match are skipped and counted,
never filled in. Re-running the import does not duplicate rows. Scores are recomputed afterwards so value
for money uses the new prices.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import PriceObservation, ProductRow
from normalise.units import parse_pack_size, price_per_100

PLATFORMS = {"zepto", "blinkit", "instamart", "bigbasket", "shop", "pack mrp", "brand website", "other"}
MATCHES = {"exact", "different size"}


def _price(v: str) -> Optional[float]:
    try:
        x = float((v or "").replace("₹", "").replace("Rs", "").replace(",", "").strip())
    except ValueError:
        return None
    return x if x > 0 else None


def _when(v: str) -> Optional[datetime]:
    v = (v or "").strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d", "%d-%m-%Y %H:%M", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(v, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def import_rows(s: Session, rows: Iterable[dict]) -> dict:
    stats = {"rows": 0, "imported": 0, "already_stored": 0, "skipped": {}}

    def skip(reason: str) -> None:
        stats["skipped"][reason] = stats["skipped"].get(reason, 0) + 1

    for r in rows:
        stats["rows"] += 1
        price = _price(r.get("selling_price_inr", ""))
        if price is None:
            skip("no price recorded")
            continue
        platform = (r.get("platform") or "").strip().lower()
        if platform not in PLATFORMS:
            skip("platform missing or unknown")
            continue
        if (r.get("matches_product") or "").strip().lower() not in MATCHES:
            skip("listing not confirmed as the same product")
            continue
        when = _when(r.get("observed_at", ""))
        if when is None:
            skip("no observation date")
            continue
        size = parse_pack_size(r.get("listing_pack_size", ""))
        if not size:
            skip("pack size missing or unreadable")
            continue
        row = s.scalar(select(ProductRow).where(ProductRow.external_product_id == f"off:{(r.get('off_code') or '').strip()}"))
        if row is None:
            skip("product not in the database")
            continue
        place = (r.get("city_pincode") or "").strip()
        source = f"{platform}{f' ({place})' if place else ''}, recorded by hand"
        url = (r.get("listing_url") or "").strip()
        url = url if url.startswith(("https://", "http://")) else None
        exists = s.scalar(select(PriceObservation).where(
            PriceObservation.product_id == row.id, PriceObservation.source == source,
            PriceObservation.observed_at == when, PriceObservation.price_inr == price))
        if exists:
            stats["already_stored"] += 1
            continue
        s.add(PriceObservation(product_id=row.id, price_inr=price, pack_size=size[0], pack_unit=size[1],
                               price_per_100g_or_ml=round(price_per_100(price, size[0]), 2),
                               source=source, source_url=url, evidence_status="declared", observed_at=when))
        stats["imported"] += 1
    s.flush()
    return stats


def main() -> None:
    ap = argparse.ArgumentParser(description="Import hand-recorded prices")
    ap.add_argument("csv_path")
    ap.add_argument("--no-rescore", action="store_true")
    args = ap.parse_args()
    from database.session import session_scope
    from services import rescore_all
    with Path(args.csv_path).open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    with session_scope() as s:
        stats = import_rows(s, rows)
        if stats["imported"] and not args.no_rescore:
            stats["rescored"] = rescore_all(s)
    print(json.dumps(stats, indent=2, default=str))


if __name__ == "__main__":
    main()
