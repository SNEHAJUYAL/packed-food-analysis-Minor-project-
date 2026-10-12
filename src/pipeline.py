"""URL -> extraction -> normalisation -> analysis -> scoring -> report (doc section 6)."""
from __future__ import annotations

from typing import Optional

from analyse.claims import analyse_claims
from analyse.fop_warning import simulate_fop_warning
from analyse.ingredients import analyse_ingredients
from analyse.nutrition import analyse_nutrition
from analyse.transparency import analyse_transparency
from analyse.value import analyse_value
from core.config import scoring_config
from core.schema import Product
from extract.fetch import fetch
from extract.html_parser import extract_html
from extract.jsonld import extract_jsonld
from extract.llm_fallback import extract_llm
from normalise.build import build_product
from normalise.ingredients import normalise_ingredients
from score.scorer import overall_score

DISCLAIMER = ("Consumer decision-support assessment, not a medical or clinical score. "
              "Methodology v{v} is a prototype; weights and thresholds are listed with their sources.")


def extract_all(html: str, url: str) -> list[dict]:
    """Structured metadata first, then HTML, then the LLM fallback (doc section 6)."""
    found = [extract_jsonld(html, url), extract_html(html, url)]
    if not any(f and (f.get("nutrition") or f.get("ingredients_text")) for f in found):
        found.append(extract_llm(html, url))
    return [f for f in found if f]


def analyse_product(product: Product, peer_unit_prices: Optional[list[float]] = None,
                    claim_overrides: Optional[dict] = None) -> dict:
    normalised = normalise_ingredients(product.ingredients_raw.value) if product.ingredients_raw.known else None
    nutrition = analyse_nutrition(product)
    ingredients = analyse_ingredients(normalised)
    transparency = analyse_transparency(product, normalised)
    claims = analyse_claims(product, ingredients["groups"] if normalised else None, claim_overrides)
    value = analyse_value(product, peer_unit_prices)
    dims = {"nutrition": nutrition["score"], "ingredients": ingredients["score"],
            "transparency": transparency["score"], "claims": claims["score"], "value": value["score"]}
    overall = overall_score(dims)
    notes = []
    if overall["score"] is None:
        notes.append("Overall score not computed: nutrition could not be scored.")
    elif overall["missing"]:
        notes.append("Not scored: " + ", ".join(overall["missing"])
                     + ". The other dimension weights were renormalised.")
    return {
        "product": product.model_dump(mode="json"),
        "dimensions": {
            "nutrition": nutrition, "ingredients": ingredients, "transparency": transparency,
            "claims": claims, "value": value,
        },
        "overall": {**overall, "notes": notes},
        "fop_warning_simulation": simulate_fop_warning(product),
        "ingredients_normalised": normalised,
        "disclaimer": DISCLAIMER.format(v=scoring_config()["methodology_version"]),
    }


def analyse_html(html: str, url: str, category: Optional[str] = None,
                 peer_unit_prices: Optional[list[float]] = None) -> dict:
    product = build_product(extract_all(html, url), url=url, category_override=category)
    return analyse_product(product, peer_unit_prices)


def analyse_url(url: str, category: Optional[str] = None, use_cache: bool = True,
                peer_unit_prices: Optional[list[float]] = None) -> dict:
    return analyse_html(fetch(url, use_cache=use_cache), url, category, peer_unit_prices)
