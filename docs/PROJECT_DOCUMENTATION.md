# Food Decision Intelligence — Project Documentation

**Project:** AI-Based Multimodal Packaged Food Analysis and Consumer Decision Support System  
**Methodology version:** 0.1.0  
**Evaluation date:** 16 November 2026

## Contents

1. [Project overview and pitch](#project-overview-and-pitch)
2. [Technology stack](#technology-stack)
3. [Processing pipeline](#processing-pipeline)
4. [Problem and solution](#problem-and-solution)
5. [User demonstration flow](#user-demonstration-flow)
6. [Current prototype capabilities](#current-prototype-capabilities)
7. [Accuracy, recall, precision and F1 evaluation](#accuracy-recall-precision-and-f1-evaluation)
8. [Technical capability matrix](#technical-capability-matrix)
9. [Data and analytics matrix](#data-and-analytics-matrix)
10. [AI/ML status matrix](#aiml-status-matrix)
11. [API and integration study](#api-and-integration-study)
12. [API surface](#api-surface)
13. [Security and governance](#security-and-governance)
14. [Product and business value](#product-and-business-value)
15. [Current limitations](#current-limitations)
16. [Recommended next milestone](#recommended-next-milestone)

## Project overview and pitch

### One-line pitch

**Food Decision Intelligence turns a packaged-food URL, label photo, or product search into an
evidence-labelled report that helps consumers understand nutrition, ingredients, price, and alternatives.**

## Problem and solution

Packaged-food listings mix serving sizes, missing nutrition fields, marketing claims, ingredient names,
pack sizes, and changing prices. Consumers cannot easily compare products fairly or distinguish declared
facts from calculated values.

The platform creates one explainable product record:

`URL / photo / search -> extraction -> normalization -> ingredient analysis -> scoring -> comparison -> alternatives`

Every field is labelled as declared, derived, interpreted, verified, or unknown. Missing data remains
missing instead of being silently converted to zero.

## Technology stack

| Layer | Technologies | Responsibility |
|---|---|---|
| Frontend | Next.js 16, React 19, TypeScript 5.9, Tailwind CSS 4 | Product search, upload, reports, comparisons, alternatives, and responsive UI |
| Backend API | Python, FastAPI, Pydantic | REST endpoints, validation, orchestration, and structured API responses |
| Persistence | PostgreSQL, SQLAlchemy, Alembic | Products, sources, analyses, prices, evidence, and migrations |
| Extraction | JSON-LD, HTML parser, Open Graph, Twitter metadata | Product identity, nutrition, ingredients, price, availability, and image evidence |
| OCR | Tesseract 5.5, pytesseract, Pillow | Offline text extraction from package photographs and screenshots |
| Optional AI | Anthropic Claude Vision/text, Google Gemini | Fallback for difficult content and Google Search-grounded answers when configured |
| NLP | Deterministic parsers, dictionaries, INS codes, RapidFuzz | Ingredient matching, additives, allergens, claims, and uncertainty detection |
| Similarity and ranking | TF-IDF, cosine similarity, rule-based ranking | Product matching, comparisons, and explainable alternatives |
| Configuration | JSON scoring and reference files, environment variables | Score weights, grade bands, dictionaries, and local deployment settings |
| Testing | pytest, Vitest/React Testing Library, TypeScript, ESLint | Backend behavior, frontend behavior, type safety, and code quality |

## Processing pipeline

### End-to-end flow

```text
User URL / product search / package image
              |
              v
Input validation and source-policy checks
              |
              v
Acquisition
  - authorized URL fetch
  - Open Food Facts lookup
  - uploaded image or saved page
              |
              v
Extraction
  - JSON-LD and HTML metadata
  - Open Graph and product image metadata
  - OCR for label images
              |
              v
Normalization
  - product identity and pack-size parsing
  - nutrition units converted to per 100 g/ml
  - ingredient and price normalization
              |
              v
Evidence and validation
  - declared / derived / interpreted / verified / unknown
  - identity and quantity checks
  - missing-data and uncertainty indicators
              |
              v
Intelligence
  - ingredient, additive, allergen, and claim analysis
  - deterministic nutrition scoring
  - product similarity and alternative ranking
              |
              v
Persistence
  - PostgreSQL product, source, price, and analysis records
              |
              v
API response and frontend presentation
  - report, comparison, price, and alternatives views
```

### Pipeline stages

1. **Input:** The user submits a product URL, searches the catalogue, uploads a label image, or uploads a
   saved product page.
2. **Validation:** The backend validates URL format, permitted schemes, source policy, redirects, request
   limits, and upload type.
3. **Acquisition:** Authorized sources are fetched with timeout, size, robots, and SSRF protections.
   Blocked or unsupported retailers return an explicit limitation instead of fabricated data.
4. **Extraction:** Structured JSON-LD is preferred, followed by HTML metadata, Open Graph/Twitter image
   metadata, visible product text, Open Food Facts data, or OCR text from an uploaded image.
5. **Normalization:** Names, brands, categories, variants, pack quantities, nutrition units, ingredients,
   prices, and image evidence are converted into the common product schema.
6. **Evidence tracking:** Each field records its evidence status and source provenance. Missing values stay
   null or unknown; inferred values are not presented as manufacturer declarations.
7. **Analysis:** Ingredients are classified, allergens and additives are identified, claims are checked,
   nutrition values are scored, and compatible alternatives are ranked.
8. **Persistence:** The normalized product and analysis are stored in PostgreSQL with source URL,
   extraction timestamp, prices, and field evidence.
9. **Presentation:** FastAPI returns the structured record. Next.js renders the product report, image,
   nutrition table, ingredients, transparency information, comparison, and alternatives.

## User demonstration flow

1. Search for **Maggi**.
2. View all stored Maggi varieties and Open Food Facts matches.
3. Review pack size, score, grade, image, price status, and source.
4. Open a product report.
5. Compare two or more instant noodle products.
6. Open explainable alternatives such as higher-scoring or lower-sodium stored products.
7. Upload a package photo when a retailer page is blocked.

## Current prototype capabilities

- Searchable packaged-food catalogue.
- Product grades and explainable dimension scores.
- Nutrition normalization per 100 g/ml.
- Ingredient classes, additives, and allergens.
- Claim checks against configured FSSAI-oriented rules.
- Dated price observations and price-per-100 calculations.
- Product comparison and preference-based alternatives.
- OCR upload and saved-page upload.
- PostgreSQL persistence and source provenance.
- Responsive product intelligence UI.

## Accuracy, recall, precision and F1 evaluation

### Executive interpretation

The current system is a deterministic decision-support prototype. Its measured results are valid only for
the labelled fixtures and samples described below. They must not be presented as production accuracy for
all packaged foods, retailer pages, camera photographs, or medical decisions.

### Metric definitions

For a field or classification task:

- **Precision** = `TP / (TP + FP)`: how many returned results were correct.
- **Recall** = `TP / (TP + FN)`: how many expected results were found.
- **F1** = `2 × precision × recall / (precision + recall)`: harmonic mean of precision and recall.
- **Exact-match accuracy** = exact correct predictions divided by all labelled cases.
- **CER** = character edit distance divided by the number of expected characters.
- **WER** = word edit distance divided by the number of expected words.

### Measured results

| Component | Dataset | Precision | Recall | F1 | Accuracy / other | Interpretation |
|---|---|---:|---:|---:|---:|---|
| Product field extraction | 4 synthetic pages, 60 labelled fields | 1.000 | 0.8125 | 0.8966 | Exact match 0.8500 | No false positives in this small fixture set; one unstructured page produced many missing fields |
| OCR | 1 rendered label fixture | Not applicable | Not applicable | Not applicable | CER 0.0081, WER 0.0000 | Harness validation only; not a camera-photo benchmark |
| Six-item ingredient sample | 6 expected ingredient records | 1.000 | 1.000 | 1.000 | 6/6 records | One term, Soy Lecithin, was preserved as uncertain |
| Ingredient classification gold set | 57 team-labelled phrases | 1.000 | 1.000 | 1.000 | 53 classified + 4 expected uncertain | Team-labelled, not an independent benchmark |
| Claim status rules | 22 hand-worked cases | Not separately reported | Not separately reported | Not separately reported | Status accuracy 1.000 | Tests expected rule outcomes, not external legal certification |
| Product name matching | 90 synthetic perturbed queries | Not separately reported | Not separately reported | Not separately reported | Correct-match rate 0.9889 | Does not prove exact retailer variant identity |
| Alternative recommendations | No relevance labels | Not measured | Not measured | Not measured | Not measured | Requires human relevance judgements and Precision@3/NDCG@5 |

### Extraction detail

| Fixture | Precision | Recall | Exact match |
|---|---:|---:|---:|
| Cereal JSON-LD | 1.000 | 1.000 | 1.000 |
| Biscuit HTML-only | 1.000 | 1.000 | 1.000 |
| Noodles per serving | 1.000 | 1.000 | 1.000 |
| Beverage unstructured | Not defined | 0.000 | 0.400 |

The overall extraction result is weighted across all 60 fields, not averaged equally across pages.

### Dataset and coverage facts

- Open Food Facts reference subset: **466 records**.
- Partial records: **405**.
- Insufficient records: **61**.
- Price missing in the reference subset: **100%**.
- Ingredient list present: **349 records**.
- Ingredient items marked uncertain: **17.6%**.
- Synthetic demonstration products: **40**; their prices are not real retailer prices.

### What is not measured

- Accuracy on real food-label photographs.
- OCR performance under blur, rotation, glare, shadows, or low light.
- Live Zepto, Blinkit, Amazon, or Instamart extraction accuracy.
- Exact cross-retailer product identity accuracy.
- Live price accuracy or availability accuracy.
- Clinical or medical safety accuracy.
- Recommendation relevance from independent human reviewers.

### Correct presentation wording

Use:

> “The prototype achieved 100% precision and 81.25% recall on four controlled synthetic product pages.
> OCR achieved 0.81% CER on one rendered label fixture. These results validate deterministic pipeline
> behavior, not general production accuracy.”

Do not use:

> “The application is 100% accurate.”

## Technical capability matrix

| Area | Implemented | Technology / location | Current evidence | Limitation |
|---|---|---|---|---|
| Product URL analysis | Yes | FastAPI, JSON-LD, HTML, safe fetch | API and tests pass | Dynamic retailer pages are unreliable |
| Product search | Yes | PostgreSQL search + Open Food Facts search | Maggi search returns stored and online matches | Online data is crowdsourced |
| OCR | Yes | Tesseract + pytesseract + Pillow | CER 0.0081 on rendered fixture | Real-photo accuracy not measured |
| Vision fallback | Optional | Anthropic Claude | Code path exists | Disabled without key; not evaluated |
| Ingredient parsing | Yes | Deterministic parser, dictionaries, RapidFuzz | Six-item F1 1.0 | Compound aliases remain incomplete |
| Allergen identification | Yes | Allergen reference dictionary | Soy and gluten detected in sample | Not a clinical allergen guarantee |
| Nutrition normalization | Yes | Unit conversion and per-100 g/ml rules | Covered by tests | Source data may be incomplete |
| Nutrition scoring | Yes | Weighted rules in `config/scoring.json` | Deterministic and explainable | Not clinically validated |
| Claim analysis | Yes | Regex + FSSAI rule table | 22 hand-worked cases pass | Not legal certification |
| Product similarity | Yes | TF-IDF + cosine similarity | 90-query matching rate 0.9889 | Similarity is not identity proof |
| Alternatives | Yes | Eligibility and preference ranking | Nutrition/price/transparency views | Recommendation relevance not measured |
| Price observations | Yes | PostgreSQL dated price records | Unit price and history API | No live retailer price adapter |
| Database | Yes | PostgreSQL + SQLAlchemy + Alembic | Runtime database healthy | Production deployment not verified |
| Frontend | Yes | Next.js, React, TypeScript, Tailwind | 50 frontend tests pass | Browser E2E suite not yet added |

## Data and analytics matrix

| Analytics output | Data used | Status | Honest interpretation |
|---|---|---|---|
| Category distribution | Stored product category | Implemented | Describes this installation's catalogue |
| Grade distribution | Deterministic product scores | Implemented | Distribution of prototype scores |
| Missing-data coverage | Product status and missing fields | Implemented | Shows source completeness |
| Price per 100 g/ml | Dated price + pack size | Implemented | Only where both values exist |
| Product comparison | Same category and nutrition basis | Implemented | Compares available stored evidence |
| Alternative ranking | Score, nutrition, similarity, price, transparency | Implemented | Explainable candidate suggestions |
| Sugar/sodium catalogue distribution | Product-level nutrition aggregation | Not available | Requires aggregate endpoint and consistent data |
| Ingredient/additive/allergen frequency | Product-level ingredient analysis | Not available | Requires catalogue aggregation |
| Recommendation Precision@3/NDCG@5 | Human relevance labels | Not measured | Evaluation set must be collected |

## AI/ML status matrix

| Component | AI/ML status | Trained in project? | Purpose |
|---|---|---:|---|
| Tesseract | Pretrained OCR engine | No | Read label text |
| Claude Vision | Optional hosted pretrained model | No | Transcribe difficult label images |
| Claude text fallback | Optional hosted pretrained model | No | Locate fields on unstructured pages |
| Gemini + Google Search | Optional hosted pretrained model with search grounding | No | Answer unknown product queries and return web source links |
| RapidFuzz | Fuzzy string matching | No | Ingredient and reference matching |
| TF-IDF + kNN | Unsupervised information retrieval | No | Product similarity and tie-breaking |
| Ingredient dictionaries | Rule-based NLP | No | Ingredient classes, additives, allergens |
| Nutrition scoring | Rule-based analytics | No | Explainable nutrition indicators |
| Claim verification | Rule-based NLP | No | Compare claims with configured rules |
| Supervised classifier | Not implemented | No | Requires verified labelled dataset |
| Food-specific transformer | Not implemented | No | Not justified until baseline is measured |

## API and integration study

| Service / key | Required? | Used for | Current status | Where configured | Cost / risk |
|---|---:|---|---|---|---|
| `DATABASE_URL` | Yes for persistence | PostgreSQL connection | Configured locally | `.env` only | Must never be committed |
| `ANTHROPIC_API_KEY` | No | Optional Claude page/photo fallback | Empty locally; deterministic path works | `.env` only | Paid hosted inference; do not expose in frontend |
| `GEMINI_API_KEY` | No | Optional Gemini AI responses and Google Search grounding | Empty unless configured | `.env` only | Paid/quota-limited hosted inference; do not expose in frontend |
| `GEMINI_MODEL` | No | Selects the Gemini model | Defaults to `gemini-3.8-flash` | `.env` only | Use a model enabled for the configured API key |
| Tesseract binary | Yes for offline photo OCR | Local OCR | Installed locally | System package | Free/open source; unavailable by default on Vercel |
| Open Food Facts API | No key | Product search/import/reference | Working with source attribution | Backend only | Rate limits and crowdsourced quality |
| BuyHatke API | No | Price intelligence | Not integrated | No key available | Requires authorised commercial agreement |
| Flash API | No | Price intelligence | No India food API verified | No key available | Do not use unrelated or internal APIs |
| Retailer APIs | No | Live prices and availability | Not integrated | No keys | Requires written authorization |
| `NEXT_PUBLIC_API_BASE_URL` | No | Frontend API routing override | Usually empty | `web/.env` | Never put secrets in `NEXT_PUBLIC_*` |

## API surface

| Endpoint | Function |
|---|---|
| `GET /api/health` | Service and database health |
| `POST /api/analyze-url` | Fetch, extract, persist and score a product |
| `POST /api/product-candidates/from-url` | Authorized preview without persistence |
| `POST /api/analyze-upload` | Analyze photo, screenshot, or saved HTML |
| `POST /api/analyze-manual` | Analyze user-entered product data |
| `GET /api/search` | Search stored products and Open Food Facts |
| `POST /api/products/import-off` | Import one Open Food Facts barcode |
| `GET /api/products/{id}` | Product report |
| `POST /api/products/compare` | Compare stored products |
| `GET /api/products/{id}/alternatives` | Explainable alternatives |
| `GET/POST /api/products/{id}/prices` | Read or add dated price observations |
| `GET /api/reference/categories` | Category list |
| `GET /api/reference/methodology` | Scoring and methodology metadata |

## Security and governance

- API keys stay server-side in environment variables.
- The frontend must never receive `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, or database credentials.
- URL fetches apply scheme, SSRF, DNS, redirect, robots, timeout, size, and rate controls.
- Unknown acquisition sources fail closed in the candidate workflow.
- Retailer access restrictions are not bypassed.
- Candidate workbook prices are isolated and labelled unverified.

## Product and business value

### Consumer value

- Understand what is in a packet.
- Compare products on a common basis.
- See missing information honestly.
- Find alternatives with reasons rather than unexplained recommendations.

### Research and engineering value

- Full data lifecycle from acquisition to decision support.
- Evidence and provenance for every important field.
- Modular OCR, NLP, scoring, and recommendation layers.
- Clear path to a verified food-label dataset and future supervised models.

## Current limitations

- Live retailer pages are dynamic, location-dependent, and often inaccessible.
- Open Food Facts has incomplete data and generally no live prices.
- Prices are not live unless recorded with source and date.
- Scores are informational and not medical assessments.
- Alternative recommendations are not clinically validated.
- No real-photo OCR benchmark or production deployment certification exists.

## Recommended next milestone

Build a verified evaluation set of 100–200 real packaged-food products with:

- front/back/ingredient/nutrition photos;
- barcode and exact variant;
- pack size and multipack count;
- manually checked nutrition values;
- dated retailer prices with location;
- human relevance labels for alternatives.

Then measure real-photo OCR CER/WER, field precision/recall/F1, exact identity accuracy, price accuracy,
and recommendation Precision@3/NDCG@5 before adding heavier ML models.

## Source documents

- [Accuracy Evaluation Report](ACCURACY_EVALUATION_REPORT.md)
- [Technical Capability and API Matrix](TECHNICAL_CAPABILITY_AND_API_MATRIX.md)
- [Pitch Documentation](PITCH_DOCUMENTATION.md)
- [AI/ML Methodology](AI_ML_METHODOLOGY.md)
- [Evaluation results](../reports/evaluation_results.json)
