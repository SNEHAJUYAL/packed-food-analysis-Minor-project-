# Test Execution Report

**Date:** 16 November 2026

## Commands executed

| Command | Result |
|---|---|
| `PYTHONPATH=src .venv/bin/python -m pytest -q` | 164 passed |
| `cd web && npm test -- --run` | 40 passed, 7 files |
| `PYTHONPATH=src .venv/bin/python -m evaluation.run` | Completed; report written |
| `PYTHONPATH=src .venv/bin/python -m evaluation.retailer_audit` | Completed for 4 permitted URLs |
| `git diff --check` | Passed |

## Evaluation results

### Synthetic extraction fixtures

- 4 pages, 60 fields.
- Precision: 1.0.
- Recall: 0.8125 overall.
- Exact-match accuracy: 0.85.
- The beverage unstructured fixture accounts for the missing-field recall.

### OCR

- Fixture type: synthetic rendered label, not a camera photograph.
- CER: 0.0081.
- WER: 0.0.
- Latency varies by run; latest evaluation was approximately 3.6 seconds.
- No real-photo accuracy claim is justified.

### Ingredient audit sample

- Six records extracted.
- Record precision/recall/F1: 1.0/1.0/1.0.
- Five dictionary matches.
- One uncertain unmatched term: `Soy Lecithin`.
- Allergens: `gluten_cereals`, `soy`.

### Ingredient gold set

- 57 team-labelled phrases.
- Classification precision/recall/F1: 1.0/1.0/1.0.
- 53 classified items and 4 uncertain cases were handled as expected.
- This is a team-labelled set, not an independent benchmark.

### Product matching

- 90 synthetic queries.
- Correct-match rate: 0.9889.
- Case/order: 1.0.
- Typo: 0.975.
- Absent products: 1.0.
- This does not validate cross-retailer variant identity.

### Open Food Facts sample coverage

- 466 records.
- 405 partial and 61 insufficient.
- Price missing in 100% because the OFF sample has no prices.
- 349 records have ingredient lists.
- 17.6% of ingredient items are uncertain.

## Skips and limitations

- No real camera-photo OCR benchmark exists.
- No PaddleOCR comparison was run.
- No OpenCV benchmark was run.
- No live retailer extraction test is an accuracy test; pages are dynamic and location-dependent.
- No BigBasket, JioMart, or other additional retailer live evidence was collected.
- No browser E2E suite was run.
- No production deployment was verified.
- No unit-test coverage percentage was collected; the repository does not currently provide a coverage report.

## Interpretation

The passing suite demonstrates local deterministic behavior and API/data-flow regression protection.
It does not establish accuracy or availability for external retailer pages, real photographs, or authorised
third-party provider integrations.

