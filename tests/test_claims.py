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


def test_high_protein_flagged_as_in_corrected_worked_example():
    # Doc 8.4 correction: 7 g protein / 410 kcal is unlikely to meet "high protein".
    # FSSAI Schedule I Sl. 11: 20% RDA per 100 g (10.8 g) or 10% RDA per 100 kcal (5.4 g), RDA 54 g.
    r = check_claim("high_protein", cereal(), {})
    assert r["status"] == INCONSISTENT
    assert any("6.8% of energy" in f for f in r["facts"])
    assert any("1.71 g per 100 kcal" in f for f in r["facts"])
    assert "Schedule I" in r["rule"]


def test_source_of_protein_met_by_same_cereal():
    assert check_claim("source_of_protein", cereal(), {})["status"] == CONSISTENT


def test_per_100kcal_route_can_satisfy_protein_claim():
    p = cereal()
    p.nutrition["energy"] = Evidence.declared(150, "test")
    p.nutrition["protein"] = Evidence.declared(9, "test")   # 9 g / 150 kcal = 6 g per 100 kcal >= 5.4
    assert check_claim("high_protein", p, {})["status"] == CONSISTENT


def test_low_saturated_fat_also_checks_energy_share():
    p = cereal()
    p.nutrition["saturated_fat"] = Evidence.declared(1.4, "test")
    p.nutrition["energy"] = Evidence.declared(100, "test")  # 1.4 x 9 / 100 = 12.6% > 10%
    assert check_claim("low_saturated_fat", p, {})["status"] == INCONSISTENT
    p.nutrition["energy"] = Evidence.declared(400, "test")
    assert check_claim("low_saturated_fat", p, {})["status"] == CONSISTENT


def test_nested_claims_not_double_counted():
    ids = {c["claim_id"] for c in extract_claims(["Very Low Sodium", "Saturated fat free", "no sugar added"])}
    assert ids == {"very_low_sodium", "saturated_fat_free", "no_added_sugar"}


def test_missing_condition_is_unverifiable():
    r = check_claim("low_fat", cereal(), {}, overrides={"low_fat": {"threshold_solid": None}})
    assert r["status"] == UNVERIFIABLE


def test_no_added_sugar_contradicted_by_ingredients():
    r = check_claim("no_added_sugar", cereal(), {"added_sugar": ["Sugar"]})
    assert r["status"] == INCONSISTENT and "Sugar" in r["facts"][0]


def test_no_added_sugar_true_but_high_total_sugar_needs_context():
    r = check_claim("no_added_sugar", cereal(), {"whole_grain": ["Oats"]})
    assert r["status"] == CONTEXT


def test_no_added_sugar_without_ingredients_is_unverifiable():
    assert check_claim("no_added_sugar", cereal(), None)["status"] == UNVERIFIABLE


def test_natural_rules_schedule_v():
    assert check_claim("natural", cereal(), {"synthetic_colour": ["INS 102"]})["status"] == INCONSISTENT
    # Composite food called "natural": Schedule V allows only "made from natural ingredients".
    assert check_claim("natural", cereal(), {}, ingredient_count=4)["status"] == INCONSISTENT
    assert check_claim("natural", cereal(), {}, ingredient_count=1)["status"] == CONTEXT
    assert check_claim("natural_ingredients", cereal(), {}, ingredient_count=4)["status"] == CONTEXT


def test_max_condition_with_override():
    p = cereal()
    o = {"low_fat": {"threshold_solid": 3.0}}
    assert check_claim("low_fat", p, {}, overrides=o)["status"] == INCONSISTENT
    p.nutrition["total_fat"] = Evidence.declared(2.0, "test")
    assert check_claim("low_fat", p, {}, overrides=o)["status"] == CONSISTENT


def test_claim_score_averages_statuses():
    r = analyse_claims(cereal(), {})
    assert r["score"] == 0  # one claim, potential inconsistency
    assert analyse_claims(Product(), {})["score"] is None
