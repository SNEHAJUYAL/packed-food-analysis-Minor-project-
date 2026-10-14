"""Command line: analyse a product URL or saved page, or compare several.

    python src/cli.py analyse https://brand.example/product
    python src/cli.py analyse tests/fixtures/cereal_jsonld.html --category breakfast_cereals
    python src/cli.py compare page1.html page2.html --category biscuits_cookies
    python src/cli.py analyse <url> --json          # full report as JSON
    python src/cli.py analyse <url> --save          # also store in PostgreSQL (DATABASE_URL)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.schema import CATEGORIES, NUTRIENTS  # noqa: E402
from extract.fetch import fetch  # noqa: E402
from normalise.build import build_product  # noqa: E402
from pipeline import analyse_html, extract_all  # noqa: E402
from recommend.ranker import compare  # noqa: E402

LIGHT = {"green": "GREEN", "yellow": "YELLOW", "red": "RED"}


def load(source: str) -> tuple[str, str]:
    """Return (html, url) for a URL or a local file."""
    path = Path(source)
    if path.exists():
        return path.read_text(encoding="utf-8"), f"file://{path.resolve()}"
    return fetch(source), source


def print_report(r: dict) -> None:
    p, o, d = r["product"], r["overall"], r["dimensions"]
    print(f"\n{p['name']['value'] or 'Unnamed product'}  [{p['brand']['value'] or '-'}]")
    print(f"Category: {p['category']['value']} ({p['category']['label']})")
    score = f"{o['score']}/100  grade {o['grade']}" if o["score"] is not None else "not computed"
    print(f"Overall: {score}")
    for n in o["notes"]:
        print(f"  note: {n}")
    if p["conflict_flag"]:
        print("  sources disagree: " + "; ".join(p["conflicts"]))
    print("\nDimensions")
    for name, dim in d.items():
        s = dim["score"]
        print(f"  {name:<13} {('%.0f' % s) if s is not None else 'not scored'}")
        for line in dim["explanation"]:
            print(f"      - {line}")
    n = d["nutrition"]
    if n["basis"]:
        per = "100 ml" if n["basis"] == "per_100ml" else "100 g"
        print(f"\nNutrition per {per}")
        for k, unit in NUTRIENTS.items():
            f = n["facts"][k]
            val = "-" if f["value"] is None else f"{f['value']:g} {unit}"
            print(f"  {k:<14} {val:<12} {LIGHT.get(n['traffic_lights'].get(k), ''):<7} {f['evidence']}")
    if p["allergens"]:
        print("\nAllergens: " + ", ".join(p["allergens"]))
    fop = r["fop_warning_simulation"]
    print(f"\nFSSAI front-of-pack warning (draft): {fop['status']}. {fop['reason']}")
    print(f"\n{r['disclaimer']}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Food Decision Intelligence")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyse", help="analyse one product URL or saved HTML page")
    a.add_argument("source")
    a.add_argument("--category", choices=CATEGORIES)
    a.add_argument("--json", action="store_true")
    a.add_argument("--save", action="store_true", help="store in PostgreSQL (needs DATABASE_URL)")
    c = sub.add_parser("compare", help="compare products in one category")
    c.add_argument("sources", nargs="+")
    c.add_argument("--category", choices=CATEGORIES, required=True)
    c.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "analyse":
        if args.save:  # store in the database and score against stored products of the category
            import services
            from database.session import session_scope
            if Path(args.source).exists():
                print("--save needs a URL (stored products keep their source URL)", file=sys.stderr)
                return 2
            with session_scope() as s:
                out = services.analyze_url(s, args.source, args.category)
            r = out["report"]
            print(f"saved as product_id {out['product_id']}", file=sys.stderr)
        else:
            html, url = load(args.source)
            r = analyse_html(html, url, args.category)
        if args.json:
            print(json.dumps(r, indent=2, default=str))
        else:
            print_report(r)
        return 0

    products = []
    for s in args.sources:
        html, url = load(s)
        products.append(build_product(extract_all(html, url), url, args.category))
    out = compare(products)
    if args.json:
        print(json.dumps({k: v for k, v in out.items() if k != "reports"}, indent=2, default=str))
        return 0
    print(f"\nCategory: {out['category']}")
    for i, row in enumerate(out["ranking"], 1):
        pr = f"₹{row['price_per_100']:.2f}/100" if row["price_per_100"] is not None else "price unknown"
        print(f"  {i}. {row['name']}  overall {row['overall']} ({row['grade']})  nutrition {row['nutrition']}  {pr}")
    print()
    for k, v in out["picks"].items():
        if v:
            print(f"{k.replace('_', ' ')}: {v['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
