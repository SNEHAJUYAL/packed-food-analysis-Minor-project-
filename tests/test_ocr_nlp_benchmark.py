from evaluation.ocr_nlp import evaluate_ingredient_sample, evaluate_ocr


def test_ocr_benchmark_reports_reproducible_metrics():
    result = evaluate_ocr()
    assert result["status"] == "complete"
    assert result["cer"] <= 0.02
    assert result["wer"] == 0
    assert "Ingredients: Okra" in result["predicted_text"]


def test_ingredient_sample_keeps_six_records_and_uncertain_match():
    result = evaluate_ingredient_sample()
    assert result["n_records"] == 6
    assert result["record_precision"] == 1
    assert result["record_recall"] == 1
    assert result["record_f1"] == 1
    assert result["uncertain"] == 1
    assert result["unmatched"] == ["Soy Lecithin"]
    assert "soy" in result["allergens"]
