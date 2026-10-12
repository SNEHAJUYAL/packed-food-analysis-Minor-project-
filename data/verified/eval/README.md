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

The proposed target from the build spec is a verified set of 100–200 real products (`data/verified/`,
template `verified_products_template.csv`). It has not been built yet.
