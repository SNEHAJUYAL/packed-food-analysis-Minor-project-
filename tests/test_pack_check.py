"""Scoring a filled pack-checking sheet. The rows here are made up for the test, not checked packs."""
from evaluation.pack_check import score


def _row(**kw):
    base = {"sample": "main", "pack_found": "yes", "category_correct": "yes", "label_basis": "per_100g",
            "sys_alt_1": "Alt A", "sys_alt_2": "Alt B", "sys_alt_3": ""}
    return base | kw


def test_pack_check_scoring():
    rows = [
        _row(label_protein_g="10", sys_protein_g="10.1", label_sodium_mg="400", sys_sodium_mg="430",
             ingredients_match="same", rec_alt_1_quality="5", rec_alt_2_quality="2"),
        _row(label_protein_g="8", sys_protein_g="", label_sodium_mg="", sys_sodium_mg="250",
             category_correct="no", ingredients_match="major differences", rec_alt_1_quality="4"),
        _row(pack_found="not found"),
        {"sample": "reserve", "pack_found": ""},
    ]
    out = score(rows)
    assert out["attempted"] == 3 and out["compared"] == 2
    assert out["pack_found"] == {"yes": 2, "not found": 1}
    assert out["category_correct"] == {"n": 2, "rate": 0.5}
    p = out["nutrition"]["protein_g"]
    assert p["printed_on_pack"] == 2 and p["system_missing"] == 1 and p["within_2pct"] == 1.0
    s = out["nutrition"]["sodium_mg"]
    assert s["compared"] == 1 and s["within_2pct"] == 0.0 and s["within_label_rounding"] == 0.0
    assert s["system_value_not_on_pack"] == 1
    assert out["ingredients_match"]["counts"] == {"same": 1, "major differences": 1}
    assert out["recommendations"]["alt_1"] == {"n": 2, "mean": 4.5, "share_4_or_5": 1.0}
    # product 1: one of two rated alternatives is 4+; product 2: one of one
    assert out["recommendations"]["precision_at_3_rating_4plus"] == {"n_products": 2, "value": 0.75}


def test_per_serving_rows_are_not_compared():
    out = score([_row(label_basis="per serving only", label_protein_g="3", sys_protein_g="10")])
    assert out["nutrition"]["protein_g"]["compared"] == 0
