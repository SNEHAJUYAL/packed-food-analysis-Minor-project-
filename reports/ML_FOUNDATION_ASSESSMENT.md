# AI/ML foundation and dataset readiness assessment

**Repository reviewed:** local checkout at `/Users/snehajuyal/Downloads/minor project`  
**Assessment date:** 16 November 2026  
**Scope:** read-only audit. No model training, imports, application edits, schema changes, or dependency installs were performed.

## Executive assessment

The project has a usable deterministic product-analysis pipeline and a small amount of classical text similarity. It does **not** currently contain a trained packaged-food ML classifier, entity-resolution model, ingredient sequence tagger, recommendation learner, or trained OCR model. The repository’s most useful starting assets are 466 real OFF product records, 40 explicitly synthetic demo records, curated reference dictionaries, and small developer-authored evaluation fixtures. These are enough to exercise the current pipeline and define a data-collection plan; they are not enough to validate production ML across Indian brands, languages, packaging revisions, or retailer catalogs.

Near-term priority should be creating a versioned, manually verified real-product ground-truth set with family/brand identity and label provenance, then establishing group-separated baselines. Do not train on the synthetic rows or use the existing tiny fixture metrics as expected real-world performance.

## Repository evidence and implemented capabilities

| Area | Evidence in repository | Current capability / limit |
|---|---|---|
| Backend flow | `src/pipeline.py`, `src/services.py`, `docs/architecture.md` | JSON-LD and HTML extraction, optional schema-constrained LLM fallback, normalization, deterministic analysis/scoring, persistence. |
| Extraction | `src/extract/jsonld.py`, `html_parser.py`, `label_ocr.py`, `llm_fallback.py` | Rule/DOM extraction and Tesseract OCR with fixed text parsers. The optional LLM locates text grounded on the page; it is not a fitted task model. |
| Normalization | `src/normalise/ingredients.py`, `units.py`, `build.py` | Bracket-aware ingredient parsing, rule/dictionary/INS matching, fuzzy term matching, unit conversion, per-serving scaling and conflict flags. |
| Category | `src/normalise/build.py`, `data/reference/category_keywords.csv`, `src/core/schema.py` | Keyword-based interpreted category over five allowed categories. No learned category classifier. |
| Scoring | `src/analyse/*`, `src/score/*`, `config/scoring.json`, `data/reference/*.csv` | Deterministic prototype rules and weights. `docs/methodology.md` labels the thresholds/weights as prototype choices, including placeholder bounds. Not a learned nutrition classifier or clinically validated score. |
| Matching | `src/normalise/matcher.py` | OFF barcode lookup and token-set fuzzy candidate rank with cutoff 85. Name/brand similarity does not establish exact variant identity. |
| Recommendation | `src/recommend/alternatives.py`, `ranker.py`, `similarity.py` | Rule-based eligibility using stored category/basis/scores and TF-IDF word n-gram cosine similarity for ranking/tie-break. `TfidfVectorizer` is fitted at request time to the candidate pool; no trained/relevance-calibrated recommendation model. |
| Persistence | `src/database/models.py`, `migrations/versions/0001*`, `0002*` | Product, source, nutrient, ordered ingredient, price-observation, analysis and recommendation tables. No verified family/variant crosswalk or annotation/label table. Barcode nullable/non-unique; product category is restricted to five values. |
| Evaluation | `src/evaluation/run.py`, `metrics.py`, `reports/evaluation_results.json`, `notebooks/evaluation.ipynb` | Metrics and benchmark harness exist. Most gold data is hand-authored from synthetic fixtures or rules, not an independent Indian product test set. Recommendations/expert ranking are explicitly not run. |
| Frontend | `web/src/components/*`, `web/src/lib/types.ts` | Displays deterministic report, ingredients, nutrition, product records and alternative picks. No client-side trained inference. |

## Current data inventory and profile

The local files were read directly. Figures below refer to repository files, not live PostgreSQL. No `DATABASE_URL` was configured in the prior data audit, so deployed/production table totals remain unknown. `data/sample/README.md` documents the committed OFF subset as filtered from a 2,692-record India export on 12 October 2026.

| Dataset / asset | Size and nature | Identity / category / quality observations |
|---|---|---|
| `data/sample/off_india_subset.jsonl` | 466 real, OFF-derived rows; source fields include code, product_name, brands, categories_tags, countries_tags, quantity, ingredients_text, nutriments, labels, nutriscore_grade, last_modified_t, `_export`. | 466 non-empty and distinct barcodes within this file; 466 names present / 438 unique trimmed case-folded names; 438 rows with brands / 233 unique raw brand strings; no duplicate barcode. Current mapped category counts in `reports/DATA_QUALITY_ASSESSMENT.md`: beverages 197, biscuits/cookies 99, namkeen/chips 80, breakfast cereals 55, instant noodles 35. Product names/categories are crowdsourced and include taxonomy noise. |
| OFF subset completeness | Fields are untyped JSON values from JSONL; `nutriments` is an object. | Ingredient text 349/466 (74.9%); quantity text 331/466 (71.0%), current quantity parser succeeds for 288/466 (61.8%); all ten mapped nutrient fields present in 55/466 (11.8%). Present: energy 465, fat 465, saturated fat 414, trans fat 130, carbohydrate 462, total sugars 460, added sugars 387, protein 461, fibre 234, sodium 446. No image, sale-price or MRP fields in this committed subset. |
| `data/sample/synthetic_products.jsonl` | 40 generated records, 8 each in five project categories. Fields include OFF-like identity/category/nutrition/ingredient structures plus `_synthetic`, `_note`, `_price_inr`. | 40 unique generated names/codes, but only 4 recurring demo brands; 35 have generated ingredient text. Nutrients were generated from fixed-seed ranges, not label data; 40 prices are made up. Never use as real-world training/test examples or price relevance labels. |
| Reference dictionaries | CSV rules: allergens (9 rows), category keywords (5), category weights (20), FOP warnings (6), FSSAI claims (18), ingredient classes (36), ingredient terms (219), INS codes (64), OFF category map (10), thresholds (13). | Curated project references/rules, not product annotations. “Rows” are dictionary entries and may not equal unique semantic classes. See `reports/DATASET_SCHEMA_COMPARISON.md` for schema context. |
| Evaluation labels | `extraction_gold.json`: 4 synthetic fixture pages × 15 expected fields; `ingredient_gold.csv`: 57 phrases; `claim_gold.csv`: 22 cases. `verified_products_template.csv` is empty. | Labels are developer/team-authored from synthetic pages, dictionary/rule definitions, and regulations. They are useful for regression/harness checks, not independent labels or representative test data. |
| Verification and price templates | `pack_check_sheet.csv`: 200 prepared rows; `price_entry_sheet.csv`: 300 prepared rows. | 0 pack-check rows have reviewer/date/pack-found or label results. 0 price rows have observation time, location, listing, selling price, MRP, stock or URL. These are queues/templates, not verified examples. |

Dataset quality detail is in [DATASET_READINESS_MATRIX.md](DATASET_READINESS_MATRIX.md); provenance and exact local profile are also recorded in the existing [data quality report](DATA_QUALITY_ASSESSMENT.md) and [project data-source docs](../docs/data_sources.md).

## Existing evaluation results: what they mean

`reports/evaluation_results.json` records harness results, but the sample sizes and sources constrain interpretation:

- Extraction: 4 synthetic HTML fixtures, 60 fields, precision 1.00, recall 0.8125, exact-match accuracy 0.85. Three structured fixtures were extracted perfectly; the unstructured page had zero true positives among its expected fields. This is not retailer or real-label performance.
- Ingredient phrase classification: 57 team-labelled phrases, reported micro precision/recall/F1 of 1.00; same dictionary definitions informed the code and labels, so this is circular and small. The separate six-item sample is also a developer-supplied sample.
- Claim status: 22 hand-worked regulatory cases, accuracy 1.00; tests rule implementation, not independent regulatory adjudication.
- Product matching: 90 queries generated from 40 synthetic product records and name perturbations, correct-match rate 0.9889. It does not measure matching among real variants, similar brand families, recycled barcodes, or retailer listings.
- Nutrition score correlation: 339 OFF rows with Nutri-Score, Spearman 0.7631; comparison to a crowdsourced proxy label is not clinical validity or independent nutritional ground truth.
- OCR: one clean, digitally rendered synthetic image, CER 0.0081 / WER 0.0, about 3.6 seconds in recorded run. It does not establish camera-photo or multilingual pack accuracy.
- Alternative recommendations and expert ranking: not run because no human relevance judgments/rankings were collected.

Treat metrics as a baseline harness check only. Accuracy claims for production require frozen real-product evaluation data, external review, and error analysis by class/category/language/source.

## Readiness by task

| Task | Current readiness | Main blocker |
|---|---|---|
| Category classification | Low-to-moderate baseline readiness | Only five categories and noisy OFF tags; no independently verified category labels or broader coverage. A transparent TF-IDF + linear classifier would be a reasonable first learned baseline after label review. |
| Ingredient recognition and normalization | Moderate rule baseline; low supervised-ML readiness | 219-term seed dictionary and parser are reusable, but 57 phrase labels are tiny/circular; no token/span annotations for real package text, multilingual spellings, compound lists or OCR noise. |
| Nutritional profile classification | Low | Numeric values exist for many OFF records but substantial missingness; no agreed ground-truth class target (e.g., regulatory class, user preference or a defined nutrient profile). Existing deterministic score is a prototype rule output, not independent target label. |
| Exact product identity matching | Low | Within-file barcodes are unique, but no cross-source identity links, families, variant-level gold pairs/hard negatives, retailer SKU crosswalk or verified product-family labels. Name perturbation tests are synthetic. |
| Alternative recommendation | Very low for learning-to-rank; rules can run | No human preference/relevance judgments, no stable user context/feedback data, sparse real assortment across only five categories; candidate pool includes synthetic data unless filtered. |

## Recommended immediate work

The next implementation task should be **a read-only annotation/labeling pipeline and versioned ground-truth dataset for 200–300 real packaged variants**, beginning with identity, brand/family/variant, category, pack and label-grounded ingredient/nutrition fields. It should produce source-linked records and group identifiers without importing into production. This creates the minimum trustworthy substrate for group-split baselines across extraction/classification/matching and exposes taxonomy/schema decisions before training.

Do not start with a pretrained transformer or OCR model fine-tuning: available labeled data is too small and evaluation leakage is high. Start with deterministic baselines and interpretable scikit-learn models after the annotation gates in the architecture proposal.
