# Nutrition score vs Nutri-Score

16 October 2026 · methodology v0.1.0 · numbers from `reports/nutriscore_comparison.json`
(`PYTHONPATH=src python -m evaluation.nutriscore`).

**In one line.** On 339 real Open Food Facts India products, our nutrition score N and the Nutri-Score grade
order products in broadly the same way: Spearman ρ = 0.76 (95 % bootstrap interval 0.71 to 0.81), Kendall
τ-b = 0.63 (0.58 to 0.67). That is agreement with one established reference scheme on this sample. It is not
evidence that either score predicts health outcomes.

> **Correction to the 12 October figure (ρ = 0.73, n = 379).** Writing this up exposed a bug: Open Food
> Facts stores drinks' values under the same `_100g` keys, and the ingestion only recognised a drink when the
> quantity field ended in "ml" or "l". Drinks with "1 ltr" or no quantity were scored against per-100 g food
> thresholds, which are about twice as lenient for sugar. The basis now comes from the pack unit (quantity,
> then product name), and stays unknown for a drink with no unit anywhere, so those drinks get no N rather
> than a wrong one. That removed 40 drinks from the comparison and raised ρ from 0.73 to 0.76. Use the
> new figure.

## 1. What is compared

| | Our nutrition score N | Nutri-Score |
| --- | --- | --- |
| What | The nutrition dimension only (0 to 100), before ingredients, transparency, claims and value are added | Grade A to E computed by Open Food Facts |
| How | Per-nutrient sub-scores against FSSAI / UK FSA thresholds, weighted per category (`data/reference/category_weights.csv`) | Points for energy, sugars, saturated fat, salt, minus points for fibre, protein, fruit/vegetables/legumes |
| Coded as | 0 to 100 | A = 5, B = 4, C = 3, D = 2, E = 1 |

N was not fitted to Nutri-Score: its weights come from the master doc and its thresholds from the reference
CSVs, all set before this comparison.

## 2. Sample selection

| Step | Records |
| --- | --- |
| Open Food Facts India records in the five categories (full CSV export, 12 Oct 2026) | 2,692 |
| No Nutri-Score grade in OFF | −1,381 |
| N unknown: under half the category's nutrient weight available, or a drink with unknown basis | −972 |
| **Compared** | **339** |

| Category | n | Nutri-Score grades (A/B/C/D/E) |
| --- | --- | --- |
| Beverages | 126 | 1 / 23 / 16 / 5 / 81 |
| Biscuits and cookies | 85 | 0 / 0 / 2 / 12 / 71 |
| Namkeen and chips | 75 | 1 / 3 / 1 / 12 / 58 |
| Breakfast cereals | 51 | 14 / 7 / 14 / 10 / 6 |
| Instant noodles | 2 | 0 / 0 / 0 / 0 / 2 |

What this selection means:

* **It is not a random sample of Indian packaged food.** It is the products someone entered into Open Food
  Facts with a fairly complete nutrition panel. Popular national brands are over-represented.
* **It is dominated by grade E** (218 of 339, 64 %). Most of the ranking signal comes from separating E from
  the rest.
* **Instant noodles are effectively absent** (2 products), so nothing is claimed for that category.
* Records are crowdsourced and unverified. The sample contains at least one junk record ("dsdsds" by
  "bfgfg", code 12345678), which was kept so the numbers match the data as loaded.

## 3. Missing data

* Nothing is imputed. A missing nutrient is left out and the remaining weights are renormalised; if less than
  50 % of the category weight remains, N is unknown and the product drops out (above).
* **Energy is never scored**: there is no sourced energy benchmark yet (`thresholds.csv`), so every product's N
  is renormalised without it. For drinks this leaves sugar as the only scored nutrient.
* 281 of the 339 products have every other weighted nutrient. On those alone ρ = 0.78, close to the full
  sample, so the renormalisation is not driving the result.

## 4. Why rank correlation

* Nutri-Score is **ordinal with five levels**; N is on a 0 to 100 scale. The two are not on the same scale and
  the relation need not be linear, so Pearson correlation would be the wrong tool.
* The decision-support question is **whether products are put in the same order**, which is what a rank
  correlation measures. Spearman's ρ is unchanged by any monotone rescaling of N.
* **Kendall's τ-b** is reported as well because Nutri-Score has heavy ties (five grades for 339 products) and
  τ-b corrects for them. It also reads directly: over pairs of products ordered differently by both scores,
  τ-b = 0.63 means concordant pairs outnumber discordant ones by about four to one.
* Intervals are percentile bootstraps (2,000 resamples for ρ, 500 for τ-b, fixed seed).

## 5. Results

**Overall:** ρ = 0.763 [0.707, 0.808]; τ-b = 0.630 [0.582, 0.673]; n = 339.

| Category | n | Spearman ρ | 95 % interval |
| --- | --- | --- | --- |
| Beverages | 126 | 0.79 | 0.72 to 0.85 |
| Breakfast cereals | 51 | 0.77 | 0.59 to 0.89 |
| Namkeen and chips | 75 | 0.64 | 0.48 to 0.75 |
| Biscuits and cookies | 85 | 0.46 | 0.25 to 0.63 |

**N by Nutri-Score grade** (median and interquartile range):

| Nutri-Score | n | N median | N IQR |
| --- | --- | --- | --- |
| A | 16 | 98 | 94 to 100 |
| B | 33 | 100 | 95 to 100 |
| C | 33 | 87 | 81 to 96 |
| D | 39 | 62 | 40 to 74 |
| E | 218 | 24 | 14 to 39 |

**Grade agreement.** Putting N into the A to E bands used for the overall grade (85/70/55/40) gives the same
grade as Nutri-Score for 57 % of products and within one grade for 85 %. The bands were designed for the
overall score, so this is only a rough check, but the cross-tabulation shows a clear pattern:

| Nutri-Score ↓ / N band → | A | B | C | D | E |
| --- | --- | --- | --- | --- | --- |
| A | 14 | 2 | 0 | 0 | 0 |
| B | 30 | 2 | 1 | 0 | 0 |
| C | 19 | 10 | 2 | 2 | 0 |
| D | 4 | 8 | 14 | 4 | 9 |
| E | 3 | 7 | 10 | 28 | 170 |

## 6. Where and why they disagree

1. **N is more lenient at the top.** 30 of 33 Nutri-Score B products get an A band, and 33 products sit at the
   ceiling of N = 100. N does not separate A from B. Because the energy term is missing, products low in
   sugar, saturated fat and sodium score 100 even if they are energy-dense.
2. **Biscuits agree least (ρ = 0.46)** largely because the range is narrow: 71 of 85 are grade E, and a rank
   correlation falls when one variable barely varies. N also does not score energy, which Nutri-Score weighs
   heavily for biscuits.
3. **Drinks are scored on sugar alone.** Unsweetened coconut milk (KLF) gets N = 100 but Nutri-Score E, which
   reflects its saturated fat. Nutri-Score's current drinks algorithm also penalises non-nutritive
   sweeteners; in our method sweeteners count against the ingredient score, not N.
4. **Things Nutri-Score counts that N does not**: fruit, vegetable and legume content, and energy. **Things N
   counts that Nutri-Score treats differently**: Indian FSSAI thresholds for "low" claims, category-specific
   weights.
5. Individual cases worth reading: Saffola Masala Oats (N = 81, Nutri-Score E; its sodium sub-score is 0 but
   sodium is only 15 % of the cereal weight), Britannia Jim Jam (N = 9, Nutri-Score D; sugar and saturated
   fat sub-scores are very low). The full list is in `largest_disagreements` in the JSON.

## 7. What this does and does not show

* **Shows:** on this sample, N ranks products in an order consistent with a widely used, independently designed
  front-of-pack scheme, with the agreement strongest for drinks and cereals and weakest for biscuits.
* **Does not show:** that N is medically valid or predicts health outcomes. Nutri-Score is a reference point,
  not ground truth, and it was designed for European diets.
* **Shared inputs:** OFF computes Nutri-Score from the same crowdsourced nutrient values N uses. An error in a
  value moves both scores, which inflates agreement. The pack-checking sheet (`data/verified/pack_check/`)
  is how the values themselves get checked.
* **Nutri-Score version:** OFF computes grades with its current algorithm (the 2023/2024 update); the export
  field recording the version was not kept, so this is inferred.

## 8. How to say it in an interview

"On 339 real Indian products from Open Food Facts, our nutrition score ranked products in broadly the same
order as Nutri-Score, with a Spearman correlation of 0.76 (bootstrap interval 0.71 to 0.81). I used rank
correlation because Nutri-Score is a five-level ordinal grade. The sample is skewed to grade E and to products
with full nutrition panels, both scores share the same crowdsourced inputs, and agreement is weakest for
biscuits, so I treat it as a consistency check against an established scheme, not a validation. The
comparison also caught a bug in how drinks' nutrition basis was read, which I fixed."

## Reproduce

```bash
./run.sh off-export                                   # data/raw/off_india.jsonl (2,692 records)
PYTHONPATH=src .venv/bin/python -m evaluation.nutriscore   # -> reports/nutriscore_comparison.json
```

Without the full export it runs on the committed 466-record subset and gives different numbers.
