# Evaluation labels (small, team-labelled)

These files are the labelled sets the evaluation notebook (`notebooks/evaluation.ipynb`) can use today.
They are **small and not independent**: they were written by the development team from the test pages
and from the regulation text, not by external annotators, and the test pages are synthetic. Results on
them show that the metric code works and give a first signal; they are not accuracy claims.

| File | What | Size | How labelled |
| --- | --- | --- | --- |
| `extraction_gold.json` | Expected normalised fields for the 4 synthetic test pages in `tests/fixtures/` | 4 pages, 15 fields each | Read off each page by hand; per-serving values scaled to per 100 g by hand |
| `ingredient_gold.csv` | Expected class for single ingredient phrases (or `uncertain`) | 57 phrases | Team judgement using `ingredient_classes.csv` definitions. Updated 12 Oct 2026 when the dictionary gained the `common_ingredient` and related classes: 7 phrases moved from `uncertain` to those classes and 7 phrases were added |
| `claim_gold.csv` | Product values and the expected claim status | see file | Expected status worked out by hand from FSSAI Schedule I / reg. 6 / Schedule V |
| `src/evaluation/ocr_nlp.py` | Reproducible OCR and required ingredient-sample benchmarks | 1 rendered label and 1 six-item sample | The OCR fixture is synthetic; it validates the harness, not real-photo accuracy |

The proposed target from the build spec is a verified set of 100–200 real products (`data/verified/`,
template `verified_products_template.csv`). It has not been built yet.

Run the benchmark and write the consolidated report with:

```bash
PYTHONPATH=src python -m evaluation.run
```

The OCR benchmark reports CER, WER and latency. It intentionally does not claim
performance on camera photographs until manually verified label images are added.

Run the separate live retailer audit with:

```bash
PYTHONPATH=src python -m evaluation.retailer_audit
```

It uses only the existing robots-aware, SSRF-safe fetcher and generic
JSON-LD/HTML extractors. Results are dynamic and must not be interpreted as
accuracy claims.
