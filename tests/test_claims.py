from analyse.claims import CONSISTENT, CONTEXT, INCONSISTENT, UNVERIFIABLE, analyse_claims, check_claim, extract_claims
from core.schema import Evidence, Product


def cereal() -> Product:
    p = Product(nutrition_basis="per_100g")
    for k, v in {"energy": 410, "total_fat": 10, "saturated_fat": 5, "carbohydrate": 72,
                 "total_sugars": 28, "protein": 7, "fibre": 4, "sodium": 400}.items():
        p.nutrition[k] = Evidence.declared(v, "test")
    p.category = Evidence.declared("breakfast_cereals", "test")
    p.claims_raw = ["High Protein"]
    return p


def test_extract_claims():
    found = {c["claim_id"] for c in extract_claims(["Zero Sugar cola", "NO ADDED SUGAR", "Rich in Protein",
                                                     "contains natural flavouring"])}
    assert found == {"sugar_free", "no_added_sugar", "high_protein"}  # "natural flavouring" is not a claim


def test_high_protein_unverifiable_until_fssai_condition_copied():
    r = check_claim("high_protein", cereal(), {})
    assert r["status"] == UNVERIFIABLE
    assert "6.8% of energy" in r["facts"][0]  # doc 8.4: about 7 %
    assert "TODO" in r["reason"]


def test_high_protein_with_a_supplied_condition():
    # Hypothetical threshold for the test only; the real one must come from the FSSAI gazette.
    r = check_claim("high_protein", cereal(), {}, overrides={"high_protein": {"threshold_solid": 20.0}})
    assert r["status"] == INCONSISTENT


def test_no_added_sugar_contradicted_by_ingredients():
    r = check_claim("no_added_sugar", cereal(), {"added_sugar": ["Sugar"]})
    assert r["status"] == INCONSISTENT and "Sugar" in r["facts"][0]


def test_no_added_sugar_true_but_high_total_sugar_needs_context():
    r = check_claim("no_added_sugar", cereal(), {"whole_grain": ["Oats"]})
    assert r["status"] == CONTEXT


def test_no_added_sugar_without_ingredients_is_unverifiable():
    assert check_claim("no_added_sugar", cereal(), None)["status"] == UNVERIFIABLE


def test_natural_with_synthetic_colour_flagged():
    assert check_claim("natural", cereal(), {"synthetic_colour": ["INS 102"]})["status"] == INCONSISTENT
    assert check_claim("natural", cereal(), {})["status"] == CONTEXT


def test_max_condition_with_override():
    p = cereal()
    o = {"low_fat": {"threshold_solid": 3.0}}
    assert check_claim("low_fat", p, {}, overrides=o)["status"] == INCONSISTENT
    p.nutrition["total_fat"] = Evidence.declared(2.0, "test")
    assert check_claim("low_fat", p, {}, overrides=o)["status"] == CONSISTENT


def test_claim_score_averages_statuses():
    r = analyse_claims(cereal(), {})
    assert r["score"] == 50  # one unverifiable claim
    assert analyse_claims(Product(), {})["score"] is None
