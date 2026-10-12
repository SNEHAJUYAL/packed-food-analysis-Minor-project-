import pytest

from normalise.units import (kj_to_kcal, nutrient_to_unit, parse_pack_size, parse_quantity, price_per_100,
                             salt_g_to_sodium_mg, scale_to_100, sodium_mg_to_salt_g)


@pytest.mark.parametrize("text,expected", [
    ("200 g", (200.0, "g")), ("1.2kg", (1.2, "kg")), ("Energy 1720 kJ", (1720.0, "kj")),
    ("400mg", (400.0, "mg")), ("1 litre", (1.0, "litre")), ("12,5 g", (12.5, "g")),
])
def test_parse_quantity(text, expected):
    assert parse_quantity(text) == expected


@pytest.mark.parametrize("text,expected", [
    ("200 g", (200.0, "g")), ("1 kg", (1000.0, "g")), ("750 ml", (750.0, "ml")),
    ("1.5 L", (1500.0, "ml")), ("4 x 70 g", (280.0, "g")), ("Net Wt. 75gm", (75.0, "g")),
    ("410 kcal", None), ("family pack", None),
])
def test_parse_pack_size(text, expected):
    assert parse_pack_size(text) == expected


def test_doc_price_example():
    # Section 2: ₹120 for 200 g vs ₹110 for 300 g.
    assert price_per_100(120, 200) == pytest.approx(60.0)
    assert price_per_100(110, 300) == pytest.approx(36.67, abs=0.005)


def test_salt_sodium_conversion():
    assert salt_g_to_sodium_mg(1.0) == pytest.approx(400.0)
    assert sodium_mg_to_salt_g(400) == pytest.approx(1.0)


def test_energy_and_mass_conversion():
    assert kj_to_kcal(1715.44) == pytest.approx(410.0)
    assert nutrient_to_unit(1720, "kj", "kcal") == pytest.approx(411.09, abs=0.01)
    assert nutrient_to_unit(0.4, "g", "mg") == pytest.approx(400)
    assert nutrient_to_unit(400, "mg", "g") == pytest.approx(0.4)
    assert nutrient_to_unit(5, "g", "kcal") is None


def test_scale_to_100():
    assert scale_to_100(1.4, 70) == pytest.approx(2.0)
    with pytest.raises(ValueError):
        scale_to_100(1, 0)
