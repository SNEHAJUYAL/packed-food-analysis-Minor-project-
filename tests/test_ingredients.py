from analyse.ingredients import analyse_ingredients
from normalise.ingredients import extract_ins, normalise_ingredients, split_top_level

BISCUIT = ("Ingredients: Refined Wheat Flour (Maida), Sugar, Edible Vegetable Oil (Palmolein), Butter (8%), "
           "Invert Sugar Syrup, Raising Agents [503(ii), 500(ii)], Salt, Emulsifiers (INS 322, 471), "
           "Artificial Flavouring Substances (Vanilla). Contains Wheat, Milk. May contain Nuts.")


def test_split_respects_brackets():
    assert split_top_level("A, B (x, y), C [1, 2]") == ["A", "B (x, y)", "C [1, 2]"]


def test_ins_322_maps_to_lecithins_emulsifier():
    item = normalise_ingredients("Emulsifier (INS 322)")["items"][0]
    assert item["additives"][0]["ins"] == "322"
    assert item["additives"][0]["name"] == "Lecithins"
    assert item["additives"][0]["functional_class"] == "emulsifier"
    assert "generic_additive" not in item["classes"]  # named by code, so not generic


def test_ins_formats():
    assert extract_ins("E322, INS 150d, INS-471, ins 500(ii)") == ["322", "150d", "471", "500"]


def test_biscuit_normalisation():
    n = normalise_ingredients(BISCUIT)
    names = [it["term"] for it in n["items"]]
    assert names[:3] == ["refined wheat flour", "sugar", "edible vegetable oil"]
    oil = n["items"][2]
    assert "oil_palm" in oil["classes"] and "oil_unspecified" not in oil["classes"]
    assert n["additives_ins"] == ["503", "500", "322", "471"]
    assert {"gluten_cereals", "milk"} <= set(n["allergens"])
    assert "tree_nuts" in n["advisory_allergens"]  # "May contain nuts" is advisory, not an ingredient
    assert n["allergen_advisory"].startswith("Contains")


def test_unspecified_oil_and_generic_additives():
    n = normalise_ingredients("Whole Grain Wheat (62%), Sugar, Cocoa Solids (6%), Edible Vegetable Oil, "
                              "Emulsifier, Flavouring")
    classes = {it["term"]: it["classes"] for it in n["items"]}
    assert classes["edible vegetable oil"] == ["oil_unspecified"]
    assert classes["emulsifier"] == ["generic_additive"]
    assert classes["whole grain wheat"] == ["whole_grain"]


def test_fuzzy_match_typo():
    item = normalise_ingredients("Palmolien Oil")["items"][0]
    assert item["term"] == "palmolein oil" and item["match"].startswith("fuzzy")


def test_ingredient_score_explains_deductions():
    r = analyse_ingredients(normalise_ingredients(BISCUIT))
    text = " ".join(r["explanation"])
    assert "Added sugar appears at ingredient #2" in text
    assert "Palm oil" in text and "Refined flour" in text and "Artificial flavouring" in text
    assert r["score"] == 100 - 15 - 10 - 5 - 10


def test_missing_ingredients_is_unknown():
    assert analyse_ingredients(None)["score"] is None


def test_nested_and_bare_ins_codes():
    n = normalise_ingredients("Noodles (Refined Wheat Flour, Thickeners (INS 412, 415)), "
                              "Tastemaker (Sugar, Flavour Enhancer (INS 627, 631))")
    assert n["additives_ins"] == ["412", "415", "627", "631"]
    taste = n["items"][1]
    assert "flavour_enhancer" in taste["classes"] and "generic_additive" not in taste["classes"]
