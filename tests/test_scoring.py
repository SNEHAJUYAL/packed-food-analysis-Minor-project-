"""Scoring engine, including the worked example in master doc section 8.4."""
import pytest

from score.category_rules import subscore, traffic_light
from score.grade import grade, round_half_up
from score.scorer import nutrition_score, overall_score, weighted

# Section 8.4: illustrative sub-scores and weights for the cereal example.
WORKED_SUBSCORES = {"total_sugars": 35, "saturated_fat": 45, "sodium": 65,
                    "energy": 55, "fibre": 70, "protein": 60}
WORKED_WEIGHTS = {"total_sugars": 0.25, "saturated_fat": 0.20, "sodium": 0.15,
                  "energy": 0.10, "fibre": 0.15, "protein": 0.15}
WORKED_DIMENSIONS = {"nutrition": 53, "ingredients": 61, "transparency": 72, "claims": 30, "value": 75}


def test_worked_example_nutrition_is_52_5_rounded_to_53():
    n = nutrition_score(WORKED_SUBSCORES, WORKED_WEIGHTS)
    assert n["raw"] == pytest.approx(52.5)
    assert n["score"] == 53
    contributions = {r["name"]: r["contribution"] for r in n["rows"]}
    assert contributions == pytest.approx({"total_sugars": 8.75, "saturated_fat": 9.0, "sodium": 9.75,
                                           "energy": 5.5, "fibre": 10.5, "protein": 9.0})


def test_worked_example_overall_is_57_75_rounded_to_58_grade_c():
    s = overall_score(WORKED_DIMENSIONS)
    assert s["raw"] == pytest.approx(57.75)
    assert s["score"] == 58
    assert s["grade"] == "C"
    contributions = {r["name"]: r["contribution"] for r in s["rows"]}
    assert contributions == pytest.approx({"nutrition": 21.2, "ingredients": 15.25, "transparency": 10.8,
                                           "claims": 3.0, "value": 7.5})


def test_worked_example_category_weights_file_matches_doc():
    from core.config import category_weights
    assert category_weights()["breakfast_cereals"] == pytest.approx(WORKED_WEIGHTS)


def test_earlier_draft_claim_score_80_gave_63():
    # Doc section 18: the uncorrected draft scored the claim 80 and got 63.
    s = overall_score({**WORKED_DIMENSIONS, "claims": 80})
    assert s["score"] == 63 and s["grade"] == "C"


def test_round_half_up_differs_from_python_round():
    assert round(52.5) == 52
    assert round_half_up(52.5) == 53
    assert round_half_up(57.75) == 58
    assert round_half_up(57.49) == 57


@pytest.mark.parametrize("score,expected", [(100, "A"), (85, "A"), (84.99, "B"), (70, "B"), (69, "C"),
                                            (55, "C"), (54, "D"), (40, "D"), (39, "E"), (0, "E")])
def test_grade_bands(score, expected):
    assert grade(score) == expected


def test_missing_parts_are_renormalised_and_reported():
    parts = dict(WORKED_SUBSCORES, energy=None, protein=None)
    n = nutrition_score(parts, WORKED_WEIGHTS)
    assert n["missing"] == ["energy", "protein"]
    assert n["coverage"] == pytest.approx(0.75)
    assert n["raw"] == pytest.approx((8.75 + 9.0 + 9.75 + 10.5) / 0.75)


def test_low_coverage_gives_unknown_not_a_number():
    parts = {k: None for k in WORKED_SUBSCORES} | {"total_sugars": 35}
    assert nutrition_score(parts, WORKED_WEIGHTS)["score"] is None


def test_overall_unknown_without_nutrition():
    s = overall_score({**WORKED_DIMENSIONS, "nutrition": None})
    assert s["score"] is None and s["grade"] is None


def test_weights_must_sum_to_one():
    with pytest.raises(ValueError):
        weighted({"a": 50}, {"a": 0.5})


def test_traffic_lights_for_worked_example():
    # Doc 8.4 lights: sugar red, sat fat yellow, sodium yellow, fibre green, protein green.
    assert traffic_light("total_sugars", 28, "breakfast_cereals", "per_100g") == "red"
    assert traffic_light("saturated_fat", 5, "breakfast_cereals", "per_100g") == "yellow"
    assert traffic_light("sodium", 400, "breakfast_cereals", "per_100g") == "yellow"
    assert traffic_light("fibre", 4, "breakfast_cereals", "per_100g") == "green"
    # Protein: FSSAI "source of protein" (10% of the ICMR-NIN RDA, 5.4 g per 100 g).
    assert traffic_light("protein", 7, "breakfast_cereals", "per_100g") == "green"
    # Energy has no sourced benchmark, so no light rather than a guess.
    assert traffic_light("energy", 410, "breakfast_cereals", "per_100g") is None


def test_subscore_curve():
    assert subscore("total_sugars", 5, None, "per_100g")["subscore"] == 100
    assert subscore("total_sugars", 22.5, None, "per_100g")["subscore"] == 40
    assert subscore("total_sugars", 45, None, "per_100g")["subscore"] == 0
    assert subscore("fibre", 1.5, None, "per_100g")["subscore"] == 50
    assert subscore("fibre", 9, None, "per_100g")["subscore"] == 100
    s = subscore("energy", 410, None, "per_100g")
    assert s["subscore"] is None and "TODO" in s["reason"]
    assert subscore("total_sugars", None, None, "per_100g")["reason"] == "value not declared"


def test_drinks_use_per_100ml_thresholds():
    assert traffic_light("total_sugars", 10, "beverages", "per_100ml") == "yellow"
    assert traffic_light("total_sugars", 12, "beverages", "per_100ml") == "red"
