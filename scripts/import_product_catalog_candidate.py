#!/usr/bin/env python3
"""Import a supplied catalog XLSX into an isolated, unverified candidate release."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from acquisition.catalog_workbook import import_catalog_workbook  # noqa: E402
from acquisition.models import AcquisitionContext  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Source XLSX; read-only")
    parser.add_argument("--out-dir", required=True, type=Path,
                        help="New/empty isolated candidate output directory; never overwritten")
    args = parser.parse_args(argv)
    context = AcquisitionContext(started_at=datetime.now(timezone.utc), dry_run=True)
    try:
        report = import_catalog_workbook(args.input, args.out_dir, context=context)
    except Exception as exc:
        print(f"candidate import failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "candidate_imported", "candidate_annotation_count": report["candidate_annotation_count"],
                      "product_listing_record_count": report["product_listing_record_count"],
                      "price_observation_record_count": report["price_observation_record_count"],
                      "acquisition_record_count": report["acquisition_record_count"],
                      "image_reference_count": report["image_references"]["count"],
                      "price_candidate_record_count": report["retailer_price_candidates"]["candidate_record_count"],
                      "populated_unverified_price_observation_count": report["retailer_price_candidates"]["populated_unverified_count"],
                      "missing_price_placeholder_count": report["retailer_price_candidates"]["missing_placeholder_count"],
                      "invalid_price_placeholder_count": report["retailer_price_candidates"]["invalid_placeholder_count"],
                      "output_directory": str(args.out_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
