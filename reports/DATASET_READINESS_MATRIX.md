# Dataset readiness matrix for task-specific ML

**Assessment date:** 16 November 2026. Counts below are file-level observations or explicitly marked project documentation; no live database was queried. The intended purpose is to decide what can be trained/evaluated, not to claim model capability.

## Repository dataset inventory

| Asset | Rows / record definition | Available fields and types | Category / provenance | Quality and ML suitability |
|---|---|---|---|---|
| `data/sample/off_india_subset.jsonl` | 466 JSON objects; one OFF barcode record per line | Strings: `code`, `product_name`, `brands`, `categories_tags[]`, `countries_tags[]`, `quantity`, `ingredients_text`, `labels[]`, `nutriscore_grade`; integer `last_modified_t`; nested numeric/string `nutriments`; export metadata. | Real OFF India-tagged data from an official bulk export snapshot on 12 Oct 2026, selected in five categories with at least four of six key nutrients. ODbL database / DbCL contents; not ground truth. | 466 unique nonempty barcodes in this subset, 438 unique normalized names, 233 raw brand strings. Ingredients 349/466; quantity 331/466, parseable quantity 288/466; full 10-field mapped nutrient profile 55/466. Good discovery/reference set, weak supervised target set. No image, price or MRP field. |
| `data/sample/synthetic_products.jsonl` | 40 JSON objects; 8 each in five generated categories | Similar OFF-shaped fields; `_synthetic`, `_note`, `_price_inr` distinguish generated demo values. | Generated via `scripts/make_synthetic_sample.py`; deterministic fixed-seed ranges; not external products. | Names/codes unique by construction; 4 recurring generated brands; ingredients 35/40. Exclude from all real-world training, validation, test, calibration and recommendation judgments. Use only for UI/demo and software behavior. |
| `data/verified/eval/extraction_gold.json` + `tests/fixtures/*.html` | 4 pages × 15 expected fields = 60 field slots | Expected name/brand/pack/price/nutrition values and absent values, JSON; HTML fixtures contain schema, table and prose examples. | Test pages are project-generated; labels were read manually from the same fixtures. | Tiny, synthetic and likely templatically matched to extraction rules. Suitable for regression tests only. |
| `data/verified/eval/ingredient_gold.csv` | 57 phrase→class rows | `text` string, `expected_class` categorical label. | Team judgement using `ingredient_classes.csv`, updated with dictionary edits. | Useful smoke test; same definitions inform rules and annotations, so not independent. No product context, spans, token boundaries or real OCR variation. |
| `data/verified/eval/claim_gold.csv` | 22 hand-worked cases | `case`, `claim_text`, boolean-like `liquid`, numeric nutrients, `ingredients`, `expected_status`, `why`. | Hand-derived from the referenced FSSAI rules; not external expert review. | Deterministic rule test, not an ML corpus. Several fields are deliberately missing. |
| `data/verified/verified_products_template.csv` | 0 data rows | Header template only. | Intended real pack verification. | No labeled product ground truth yet. |
| `data/verified/pack_check/pack_check_sheet.csv` | 200 prepared candidate rows | Candidate OFF identity and system output plus label verification fields. | 0 reviewer/date/pack or label-result cells populated. | Queue, not labeled set; no measured correctness for products/categories/nutrition/ingredients/recommendations. |
| `data/verified/prices/price_entry_sheet.csv` | 300 prepared candidate rows | Candidate product/platform plus observation date, locality, listing, sale/MRP, stock, URL fields. | 0 actual observation fields populated. | No price training data, current prices, availability outcomes or relevance judgments. |
| `data/reference/*.csv` | 10 rule/dictionary files; entries: 9 allergens, 5 category keyword groups, 20 category-weight rows, 6 FOP rows, 18 claim rows, 36 ingredient classes, 219 ingredient terms, 64 INS codes, 10 OFF category map rows, 13 nutrient thresholds. | String IDs/terms and rule values/weights/thresholds; see headers in each file. | Project seed dictionaries, public regulatory references and selected external taxonomies. | Useful weak supervision/normalization references. They are not a balanced labeled product corpus; terms may overlap or lack review status. Methodology marks several thresholds provisional. |
| `data/raw/`, `data/cache/` | No committed payloads (only `.gitkeep` in raw/cache listing) | Runtime/ignored data locations. | Exports/cached web pages are git-ignored according to `docs/data_sources.md`. | No additional local corpus could be profiled from tracked files. |

### OFF subset completeness detail

| Field | Present rows | Missing rows | Completeness |
|---|---:|---:|---:|
| Barcode | 466 | 0 | 100% |
| Product name | 466 | 0 | 100% |
| Brand | 438 | 28 | 94.0% |
| Ingredient text | 349 | 117 | 74.9% |
| Raw quantity | 331 | 135 | 71.0% |
| Quantity parseable by existing parser | 288 | 178 | 61.8% |
| Energy | 465 | 1 | 99.8% |
| Total fat | 465 | 1 | 99.8% |
| Saturated fat | 414 | 52 | 88.8% |
| Trans fat | 130 | 336 | 27.9% |
| Carbohydrate | 462 | 4 | 99.1% |
| Total sugars | 460 | 6 | 98.7% |
| Added sugars | 387 | 79 | 83.0% |
| Protein | 461 | 5 | 98.9% |
| Fibre | 234 | 232 | 50.2% |
| Sodium | 446 | 20 | 95.7% |
| All ten mapped nutrition values together | 55 | 411 | 11.8% |

Nutrition records are crowdsourced declaration data. “Present” does not ensure transcription accuracy, consistent basis, current formulation, or label verification. There are 28 repeated normalized product-name values (438 unique names); zero duplicate barcodes and zero duplicate simple `(raw brand, name, quantity)` triples were observed. Exact triple uniqueness is not proof of unique physical variants.

## Category coverage and imbalance

Project mapped categories among the 466 real OFF rows: **beverages 197 (42.3%)**, **biscuits/cookies 99 (21.2%)**, **namkeen/chips 80 (17.2%)**, **breakfast cereals 55 (11.8%)**, **instant noodles 35 (7.5%)**. There is no manually verified category ground truth, and the underlying OFF taxonomy includes typos, cross-category tags and non-target products. The five-category `CATEGORIES` list in `src/core/schema.py` and database check constraint are a deployment restriction, not a validated market taxonomy.

The synthetic set has exactly eight records in each of the same five categories. This balance is artificial and has no evidential value for the real category distribution.

## Task-level readiness

| ML task | Available input | Required ground truth not present | Readiness / first defensible baseline |
|---|---|---|---|
| Packaged-food category classification | OFF categories/tags, product names, brands, ingredient snippets; 466 real rows in five broad groups | Human-verified single primary category, multi-label policy, hierarchy, taxonomy version and adequate examples per class including out-of-scope examples | **Low.** Annotate categories and disagreements. Compare majority/keyword rules with TF-IDF word+character n-grams + linear SVM/logistic regression. Evaluate macro-F1, per-class recall and unknown-class rejection. |
| Ingredient recognition / normalization | 349 real ingredient lists; 2,544 parsed items in the current 466-row analysis report; 219-term dictionary; 57 phrase labels | Product/source-linked list spans, canonical identity, hierarchy for subingredients, additive/INS labels, aliases/transliteration, OCR provenance and adjudication | **Low for ML, moderate for rule baseline.** Expand lexicon and annotation; compare parser/dictionary against span/entity labels and normalization accuracy. Traditional CRF or fine-tuned multilingual token classifier only after sufficient diverse annotations. |
| Nutritional profile classification | Up to 466 OFF label-declared profiles, with field missingness above | A defined target (e.g. regulatory thresholds per basis, independent expert rating or consumer preference), exact pack label/verified numeric values, versioned rules and a missing-data policy | **Low.** First establish deterministic regulatory/threshold baseline with verified label data. A classifier over nutrient values risks learning current prototype scores; use supervised ML only for a distinct, defensible target. |
| Exact product identity matching | OFF barcode/name/brand/quantity; fuzzy matcher; synthetic 40-product perturbation test | Cross-source positive links, hard negative pairs (same family/flavour/size), barcode validity and mismatch adjudication, family/variant/pack levels, retailer SKU crosswalk | **Very low.** Implement exact identifier and attribute rules as candidate baseline; collect pair labels and report pairwise precision/recall, false merge rate, and review load before ML. |
| Alternative recommendations | Stored product category/nutrition/scores, synthetic prices; TF-IDF similarity | Human relevance/preference judgments or consented interaction events, constraints/needs, comparable candidate sets, outcomes and exposure data | **Very low for learned ranking.** Keep eligibility deterministic; collect expert pairwise rankings or user preference judgments, then compare rule ranking with learning-to-rank offline. Do not use synthetic prices/preferences as labels. |

## Evaluation and leakage controls

No dataset currently records product-family or brand split keys. Before any model comparison, annotate a stable `brand_id`, `family_id`, `variant_id`, source snapshot and product revision. Make train/validation/test partitions by product family; use a stricter brand-held-out stress test for category/ingredient generalization. Keep all records and images of a family, package revision, close duplicate, and derived dataset row in one partition. OFF, PackSense and Shelfpedia must not appear as “independent” copies across splits. For temporal freshness, reserve later snapshots as an additional test. Tune thresholds/hyperparameters on validation only; freeze test once, report support and confidence intervals, and slice by category, region/language, source and OCR quality.

For matching, construct pair/query splits by product family so near-duplicate pairs cannot straddle train/test. For recommendations, split users and candidate families as appropriate and prevent future observations from leaking into training. A random row split is unsafe for every task in this product domain.
