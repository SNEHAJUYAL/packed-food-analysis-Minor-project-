# AI/ML methodology and honest model status

Checked against the code on 16 November 2026.

## 1. Summary

**No machine-learning model has been independently trained in this project.** There are no model weight
files in the repository, no training script, and no training dataset that has passed verification. The
system's intelligence comes from:

* deterministic extraction (JSON-LD, HTML table parsing, regular expressions);
* OCR with the pretrained open-source Tesseract engine;
* optional pretrained large language and vision models (Anthropic Claude and Google Gemini) used only to *locate* text that
  already exists on a page or photo;
* dictionary- and rule-based ingredient classification with fuzzy string matching;
* rule-based, sourced nutrition benchmarks and a weighted scoring formula;
* a classic information-retrieval similarity method (TF-IDF vectors + k-nearest neighbours by cosine);
* rule-based eligibility and ranking for alternatives.

The scores are deterministic: the same input gives the same score. They are prototype decision support,
not a validated or medical model.

## 2. Component classification

| Component | File | Type | Trained here? |
| --- | --- | --- | --- |
| JSON-LD / microdata extraction | `extract/jsonld.py` (uses `extruct`) | Deterministic parser | No training |
| HTML nutrition table and label extraction | `extract/html_parser.py` | Deterministic parser + rules | No training |
| Unit normalisation | `normalise/units.py`, `normalise/build.py` | Deterministic rules (kJ ÷ 4.184, sodium = salt ÷ 2.5, per-serving scaling) | No training |
| Pack-photo OCR | `extract/label_ocr.py` | Pretrained OCR (Tesseract via `pytesseract`) + regex rules for ingredients, nutrient rows, net quantity, price | Not trained here |
| Vision label reading (optional) | `extract/label_image.py` | Pretrained multimodal LLM (Anthropic Claude); transcript first, then schema; value kept only if in transcript | Not trained here; off unless `ANTHROPIC_API_KEY` is set |
| Search-grounded AI answer (optional) | `answer.py` | Google Gemini with Google Search grounding; source links are returned separately from stored evidence | Not trained here; off unless `GEMINI_API_KEY` is set |
| Text fallback for unstructured pages (optional) | `extract/llm_fallback.py` | Pretrained LLM with schema-constrained output; values must appear verbatim in page text | Not trained here; off unless key set; disabled for uploaded HTML |
| Ingredient splitting and classification | `normalise/ingredients.py` + `data/reference/ingredient_terms.csv` (219 terms), `ingredient_classes.csv` (36 classes), `ins_codes.csv` (64 codes), `allergens.csv` (9 groups) | Dictionary lookup, then RapidFuzz `ratio` with cutoff 90; otherwise *uncertain* | No training |
| Category assignment | `normalise/build.py: categorise` + `category_keywords.csv`; OFF tags via `off_category_map.csv` | Keyword rules | No training (the CSV notes a TF-IDF classifier as a future replacement) |
| Nutrition, ingredient, transparency, claim, value scores | `analyse/`, `score/`, `config/scoring.json` | Rule-based formulas with sourced thresholds | No training |
| Claim checks | `analyse/claims.py` + `fssai_claims.csv` (18 rules) | Regex claim detection + regulatory rules | No training |
| Product similarity | `recommend/similarity.py` | TF-IDF (unigrams + bigrams) + `NearestNeighbors(metric="cosine")` from scikit-learn, fitted at request time on stored products; a pure-Python identical fallback when scikit-learn is absent (Vercel bundle) | Unsupervised, fitted per request; no stored model |
| Alternatives ranking | `recommend/alternatives.py` | Rule-based eligibility, sort by preference score, similarity as tie-break | No training |
| OFF record matching | `services.match_open_food_facts`, `normalise/matcher.py` | RapidFuzz token-set ratio, cutoff 85 | No training |

## 3. Model cards for the models actually used

### 3.1 Tesseract OCR

| Field | Value |
| --- | --- |
| Model | Tesseract OCR engine (system install, `brew install tesseract`), called through `pytesseract` |
| Architecture | Pretrained LSTM-based OCR engine distributed by the Tesseract project |
| Purpose | Read text from pack photos and app screenshots offline |
| Input | JPEG, PNG, WebP or GIF up to 8 MB |
| Output | Plain text; then regex rules extract ingredients, nutrient rows (per-100 column), net quantity, price |
| Dataset | Not trained by the project |
| Evaluation | One reproducible *rendered* label image (`src/evaluation/ocr_nlp.py`): CER 0.0081, WER 0.0, 3.6 s (`reports/evaluation_results.json`). This validates the harness, **not** accuracy on camera photos, which has not been measured |
| Inference | Upload a photo on the landing page, or `POST /api/analyze-upload` |
| Model file | System binary (`/opt/homebrew/bin/tesseract` on the team Mac); no model file in the repository |

### 3.2 Anthropic Claude (optional)

| Field | Value |
| --- | --- |
| Model | Anthropic Claude through the `anthropic` SDK; model id from `FDI_LLM_MODEL` (default in `src/extract/llm_fallback.py`) |
| Architecture | Hosted pretrained large language / vision model |
| Purpose | (a) locate product fields on pages with no structured data; (b) transcribe and read label photos |
| Input | Visible page text, or an image |
| Output | Strict Pydantic schema (`LlmProduct`, `LabelReading`) |
| Safeguard | A value is kept only if it appears verbatim in the page text or in the model's own transcript; dropped otherwise |
| Dataset / training | None by the project |
| Evaluation | Not measured; disabled in all recorded test runs (no key) |
| Inference | Set `ANTHROPIC_API_KEY` in `.env`; the code chooses it automatically |

### 3.3 Google Gemini with Google Search grounding (optional)

| Purpose | Answer an unknown product query with current web discovery while keeping the result clearly labelled as an
unverified AI estimate |
|---|---|
| SDK | `google-genai` |
| Default model | `gemini-3.8-flash`, configurable with `GEMINI_MODEL` |
| Grounding | `GoogleSearch` tool; returned web source links are shown in the answer card |
| Inference | Set `GEMINI_API_KEY` in `.env`; the key remains server-side |
| Data boundary | Gemini output is never persisted as product nutrition, price, grade, or verified identity |
| Model file | Hosted; nothing stored |

### 3.3 TF-IDF + kNN similarity

| Field | Value |
| --- | --- |
| Method | `TfidfVectorizer(ngram_range=(1, 2))` over name, brand, category and ingredients; `NearestNeighbors(metric="cosine")` |
| Purpose | Tie-break among eligible alternatives; similarity value shown with each alternative |
| Training | Fitted on the stored candidate pool for each request; nothing persisted |
| Evaluation | Recommendation relevance (Precision@3, NDCG@5) **not run**: no relevance judgements collected (metric code exists in `evaluation/metrics.py`) |

## 4. Evaluation evidence that exists

All from `PYTHONPATH=src python -m evaluation.run` → `reports/evaluation_results.json`. Sample sizes are
small and team-labelled, so these are checks that the code behaves as designed, not accuracy claims.

| Check | Data | Result |
| --- | --- | --- |
| Field extraction | 4 synthetic test pages, 60 fields | precision 1.0, recall 0.81, exact match 0.85 (the unstructured page yields nothing without the LLM) |
| Ingredient classification | 57 team-labelled phrases | 53/53 classes correct, 4/4 uncertain flagged |
| Claim status | 22 hand-worked FSSAI cases | status accuracy 1.0 |
| Product matching | 90 perturbed queries on 40 synthetic names | 0.989 correct |
| Agreement with Nutri-Score | 339 OFF India products with an OFF Nutri-Score grade and a computable nutrition score | Spearman ρ = 0.763 (95 % CI 0.707–0.808), Kendall τb = 0.63. Nutri-Score is computed from the same nutrients, so this is agreement with a reference scheme, not accuracy ([nutriscore_comparison.md](nutriscore_comparison.md)) |
| Weight robustness | 40 synthetic records, ±20 % on each weight | mean absolute score change 0.6–1.3 points |
| OCR harness | 1 rendered label | CER 0.0081 |
| Expert ranking, recommendation relevance | — | not run |

## 5. ML readiness (not yet implemented)

The repository prepares for future supervised work without claiming it:

* annotation schema v1 (`data/annotation/schema_v1.json`) and guidelines;
* 85 consolidated **candidate** records awaiting human review, plus 25 catalogue candidates;
* grouped split tooling (`scripts/create_grouped_splits.py`) so that product families or brands never
  leak across train and test;
* proposals in `reports/ML_ARCHITECTURE_PROPOSAL.md` and `reports/ML_FOUNDATION_ASSESSMENT.md`.

`data/annotation/splits/` contains only `.gitkeep`: no split has been produced, because no record has been
verified. Training should not start until a verified set exists (the build spec targets 100–200 real
products checked against packs; the pack-check sheet for 150 + 50 reserve products is unfilled).

## 6. Wording to use in the report and viva

* Say "rule-based, explainable scoring" and "TF-IDF similarity", not "trained ML model".
* Say "OCR with Tesseract" and "optional LLM-assisted extraction with verbatim grounding".
* Say "agreement with Nutri-Score ρ = 0.76 on 339 OFF products", not "76 % accuracy".
* Say "photo-reading accuracy has not been measured".
