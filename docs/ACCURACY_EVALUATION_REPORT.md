# Accuracy, Recall, Precision and F1 Evaluation

**Project:** Food Decision Intelligence  
**Methodology version:** 0.1.0  
**Evaluation date:** 16 November 2026

## Executive interpretation

The current system is a deterministic decision-support prototype. Its measured results are valid only for
the labelled fixtures and samples described below. They must not be presented as production accuracy for
all packaged foods, retailer pages, camera photographs, or medical decisions.

## Metric definitions

For a field or classification task:

- **Precision** = `TP / (TP + FP)`: how many returned results were correct.
- **Recall** = `TP / (TP + FN)`: how many expected results were found.
- **F1** = `2 × precision × recall / (precision + recall)`: harmonic mean of precision and recall.
- **Exact-match accuracy** = exact correct predictions divided by all labelled cases.
- **CER** = character edit distance divided by the number of expected characters.
- **WER** = word edit distance divided by the number of expected words.

## Measured results

| Component | Dataset | Precision | Recall | F1 | Accuracy / other | Interpretation |
|---|---|---:|---:|---:|---:|---|
| Product field extraction | 4 synthetic pages, 60 labelled fields | 1.000 | 0.8125 | 0.8966 | Exact match 0.8500 | No false positives in this small fixture set; one unstructured page produced many missing fields |
| OCR | 1 rendered label fixture | Not applicable | Not applicable | Not applicable | CER 0.0081, WER 0.0000 | Harness validation only; not a camera-photo benchmark |
| Six-item ingredient sample | 6 expected ingredient records | 1.000 | 1.000 | 1.000 | 6/6 records | One term, Soy Lecithin, was preserved as uncertain |
| Ingredient classification gold set | 57 team-labelled phrases | 1.000 | 1.000 | 1.000 | 53 classified + 4 expected uncertain | Team-labelled, not an independent benchmark |
| Claim status rules | 22 hand-worked cases | Not separately reported | Not separately reported | Not separately reported | Status accuracy 1.000 | Tests expected rule outcomes, not external legal certification |
| Product name matching | 90 synthetic perturbed queries | Not separately reported | Not separately reported | Not separately reported | Correct-match rate 0.9889 | Does not prove exact retailer variant identity |
| Alternative recommendations | No relevance labels | Not measured | Not measured | Not measured | Not measured | Requires human relevance judgements and Precision@3/NDCG@5 |

## Extraction detail

| Fixture | Precision | Recall | Exact match |
|---|---:|---:|---:|
| Cereal JSON-LD | 1.000 | 1.000 | 1.000 |
| Biscuit HTML-only | 1.000 | 1.000 | 1.000 |
| Noodles per serving | 1.000 | 1.000 | 1.000 |
| Beverage unstructured | Not defined | 0.000 | 0.400 |

The overall extraction result is weighted across all 60 fields, not averaged equally across pages.

## Dataset and coverage facts

- Open Food Facts reference subset: **466 records**.
- Partial records: **405**.
- Insufficient records: **61**.
- Price missing in the reference subset: **100%**.
- Ingredient list present: **349 records**.
- Ingredient items marked uncertain: **17.6%**.
- Synthetic demonstration products: **40**; their prices are not real retailer prices.

## What is not measured

- Accuracy on real food-label photographs.
- OCR performance under blur, rotation, glare, shadows, or low light.
- Live Zepto, Blinkit, Amazon, or Instamart extraction accuracy.
- Exact cross-retailer product identity accuracy.
- Live price accuracy or availability accuracy.
- Clinical or medical safety accuracy.
- Recommendation relevance from independent human reviewers.

## Correct presentation wording

Use:

> “The prototype achieved 100% precision and 81.25% recall on four controlled synthetic product pages.
> OCR achieved 0.81% CER on one rendered label fixture. These results validate deterministic pipeline
> behavior, not general production accuracy.”

Do not use:

> “The application is 100% accurate.”

## Source of truth

The machine-readable measurements are in [evaluation_results.json](../reports/evaluation_results.json).
The implementation and model-status explanation is in [AI_ML_METHODOLOGY.md](AI_ML_METHODOLOGY.md).
