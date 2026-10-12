# Methodology v0.1.0 (prototype)

Dated 12 October 2026. All weights and curve parameters are prototype choices to be calibrated
(master doc section 8.6), not validated science. The score is a consumer decision-support
assessment, not a medical or clinical score.

## Where every number lives

| What | File | State |
| --- | --- | --- |
| Dimension weights (0.40 / 0.25 / 0.15 / 0.10 / 0.10), grade bands, curves | `config/scoring.json` | From doc section 8.3; curve parameters are prototype |
| Nutrient benchmarks (traffic lights, sub-scores) | `data/reference/thresholds.csv` | Green bounds: FSSAI Advertising and Claims Regs 2018, Schedule I "low" / "source of" conditions. Red bounds: UK DH/FSA 2016 as a **labelled placeholder** (no final Indian "high" cut-off). Protein: 10% of the ICMR-NIN RDA (54 g). Energy: **TODO** |
| Category nutrient weights | `data/reference/category_weights.csv` | Cereals: doc worked example. Others: equal weights over the nutrients the doc lists |
| Claim conditions | `data/reference/fssai_claims.csv` | 18 claims with values and clause numbers from the FSSAI compendium (14-12-2022): Schedule I (nutrient content), reg. 6(1) (no added sugar), reg. 9(2) + Schedule V ("natural"). Checked 12 Oct 2026 |
| FSSAI front-of-pack warning (draft) | `data/reference/fop_warning.csv` | **TODO** until the rule is final |
| INS codes | `data/reference/ins_codes.csv` | 66 common codes, seed list to verify against Codex CXG 36-1989 and FSSAI additive regulations |
| Ingredient dictionary | `data/reference/ingredient_terms.csv` | Seed list; align with the Open Food Facts taxonomy |
| Allergens | `data/reference/allergens.csv` | FSSAI Labelling and Display Regulations 2020 groups; verify wording |

Protein claims convert "% RDA" to grams with the ICMR-NIN 2020 RDA of 54 g/day (sedentary adult man,
reg. 2(1)(n) points to current ICMR values); the per-serving route is not checked, so a fail is
"potential inconsistency for review". A TODO cell loads as "unknown". The system then says "cannot be verified" or leaves the
nutrient out of N (and reports the coverage), rather than guessing.

## Pipeline

1. **Extraction.** JSON-LD / microdata first (`extract/jsonld.py`), then HTML (`extract/html_parser.py`),
   then a Claude fallback (`extract/llm_fallback.py`) whose values must appear verbatim in the page. `extract/fetch.py` checks
   robots.txt and caches pages for the demo.
2. **Normalisation** (`normalise/build.py`). Per 100 g/ml; per-serving panels with a stated serving size
   are scaled and labelled *derived*; a panel without a stated basis is not used. Sodium from salt
   is *derived* (salt ÷ 2.5). Sources that differ by more than 2 % set `conflict_flag` and are listed.
3. **Ingredients** (`normalise/ingredients.py`). Bracket-aware splitting, recursive compound
   ingredients, INS codes (INS 322, E322, 500(ii), bare codes in brackets), dictionary then
   RapidFuzz matching, allergen detection with "may contain" advisories kept separate.
4. **Analysis** (`analyse/`). Nutrition (lights, sub-scores, N), ingredient profile (I),
   transparency (T), claims (C), value (V), FSSAI warning simulation.
5. **Scoring** (`score/`). Sub-scores → N (renormalised over known nutrients, minimum 50 % coverage);
   dimensions rounded half-up, then S = 0.40N + 0.25I + 0.15T + 0.10C + 0.10V; A–E grade.
   No overall score without N.
6. **Comparison** (`recommend/`). Same-category ranking, three separate picks (best for priorities,
   lowest price per 100 g/ml, best nutrition) with reasons; TF-IDF + kNN for similar products.

## Sub-score curve (prototype)

* Lower-better nutrients: value ≤ green bound → 100; falls linearly to 40 at the red bound;
  then to 0 at twice the red bound.
* Higher-better nutrients: 0 → 0, rising linearly to 100 at the green bound.

## Dimension rules (prototype)

* **Ingredients (I):** start at 100; deductions from `ingredient_deductions` for added sugar in the
  top three (or anywhere), palm oil, hydrogenated fat, artificial sweeteners, synthetic colours,
  flavour enhancers, synthetic antioxidants, preservatives, artificial flavouring, refined flour
  first; bonus for whole grain first. These are disclosure and processing signals, not safety findings.
* **Transparency (T):** share of 10 core fields disclosed, bonus for added sugars / trans fat / fibre,
  deductions for additive classes without INS codes and undisclosed oil sources.
* **Claims (C):** mean of status scores (consistent 100, requires context 60, cannot be verified 50,
  potential inconsistency 0). No claims → not scored.
* **Value (V):** 50 at the category median price per 100 g/ml, 100 at half, 0 at double
  (linear in log2). Needs a comparison set.

## Worked example (doc section 8.4)

`tests/test_scoring.py` reproduces it exactly from the doc's illustrative sub-scores:
N = 52.5 → 53, S = 57.75 → 58, grade C (and the uncorrected draft's 63 with claim = 80).

Running the full pipeline on a synthetic page with the same nutrition values gives overall 69 (C),
nutrition 61, with value unscored (no comparison set) and energy unscored (no benchmark). The
"High Protein" claim is flagged exactly as the doc's correction says: 7 g per 100 g and 1.71 g per
100 kcal are below FSSAI's 10.8 g / 5.4 g conditions.
