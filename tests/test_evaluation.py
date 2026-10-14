import pytest

from evaluation.metrics import (binary_rates, field_scores, label_prf, ndcg_at_k, precision_at_k, spearman,
                                values_match)


def test_values_match_tolerance_and_missing():
    assert values_match(100, 101.5) and not values_match(100, 103)
    assert values_match(None, None) and not values_match(None, 0)  # missing is not zero
    assert values_match("Example  Foods", "example foods")


def test_field_scores():
    s = field_scores([(1, 1), (2, None), (None, 3), (4, 9), (None, None)])
    assert (s["tp"], s["fp"], s["fn"]) == (1, 2, 2)
    assert s["exact_match_accuracy"] == pytest.approx(2 / 5)


def test_label_prf_treats_uncertain_as_no_label():
    s = label_prf(["a", "b", "uncertain", "c"], ["a", "uncertain", "uncertain", "x"], "uncertain")
    assert (s["tp"], s["fp"], s["fn"]) == (1, 1, 2)


def test_binary_rates():
    s = binary_rates([True, False, False, True], [True, True, False, False])
    assert s["false_positive_rate"] == 0.5 and s["precision"] == 0.5 and s["recall"] == 0.5


def test_spearman_and_ranking_metrics():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert spearman([1, 2], [1, 2]) is None
    assert precision_at_k(["a", "b", "c", "d"], {"a", "c"}, 3) == pytest.approx(2 / 3)
    assert ndcg_at_k(["a", "b"], {"a": 3, "b": 1}) == pytest.approx(1.0)
    assert ndcg_at_k(["b", "a"], {"a": 3, "b": 1}) < 1.0
