# Food Decision Intelligence — Pitch Documentation

## One-line pitch

**Food Decision Intelligence turns a packaged-food URL, label photo, or product search into an
evidence-labelled report that helps consumers understand nutrition, ingredients, price, and alternatives.**

## The problem

Packaged-food listings mix serving sizes, missing nutrition fields, marketing claims, ingredient names,
pack sizes, and changing prices. Consumers cannot easily compare products fairly or distinguish declared
facts from calculated values.

## The solution

The platform creates one explainable product record:

`URL / photo / search -> extraction -> normalization -> ingredient analysis -> scoring -> comparison -> alternatives`

Every field is labelled as declared, derived, interpreted, verified, or unknown. Missing data remains
missing instead of being silently converted to zero.

## User demonstration flow

1. Search for **Maggi**.
2. View all stored Maggi varieties and Open Food Facts matches.
3. Review pack size, score, grade, image, price status, and source.
4. Open a product report.
5. Compare two or more instant noodle products.
6. Open explainable alternatives such as higher-scoring or lower-sodium stored products.
7. Upload a package photo when a retailer page is blocked.

## What the current prototype demonstrates

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

## Accuracy slide

Use this exact, conservative summary:

| Measure | Result | Dataset |
|---|---:|---|
| Extraction precision | 100% | 60 fields across 4 controlled synthetic pages |
| Extraction recall | 81.25% | Same dataset |
| Extraction exact-match accuracy | 85% | Same dataset |
| Ingredient precision / recall / F1 | 1.00 / 1.00 / 1.00 | Six-item sample |
| Ingredient gold-set precision / recall / F1 | 1.00 / 1.00 / 1.00 | 57 team-labelled phrases |
| OCR CER / WER | 0.81% / 0% | One rendered label fixture |
| Product matching correct-match rate | 98.89% | 90 synthetic perturbed queries |

### Accuracy disclaimer

These are controlled prototype evaluations. They are not claims of accuracy on every retailer,
photograph, food category, location, or product variant. Real-photo OCR, live retailer extraction,
exact cross-retailer identity, and recommendation relevance still require dedicated evaluation datasets.

## AI, ML and analytics explanation for a viva

### AI components

- Tesseract pretrained OCR reads text from labels.
- Optional Claude Vision can transcribe difficult images.
- Optional Claude text fallback can locate fields on unstructured pages.

### ML / information retrieval components

- TF-IDF with cosine similarity finds similar stored products.
- RapidFuzz handles spelling variation and ingredient matching.
- No project-trained classifier or transformer model currently exists.

### Data analytics components

- Nutrition values are standardized to per 100 g/ml.
- Missingness and evidence status are tracked.
- Unit prices enable fair pack-size comparison.
- Score distributions, category distributions, and source composition are visualized.
- Product comparison highlights nutrition, ingredients, transparency, claims, and value.
- Alternatives are ranked using deterministic preferences and explainable rationale.

### Why no large transformer was added

The current deterministic baseline is auditable, lightweight, CPU-compatible, and sufficient for many
structured labels. A generic pretrained NER model is not food-specific. A larger model should be added
only after a verified food-label benchmark shows measurable improvement.

## API-key and integration position

- Open Food Facts: currently usable reference source; no key required.
- Tesseract: local, free OCR; no API key.
- Claude and Gemini: optional keys, server-side only, not enabled in recorded evaluations. Gemini can use
  Google Search grounding for clearly labelled AI estimates when a key is configured.
- BuyHatke and Flash: no authorised India food-price API was verified; no integration is claimed.
- Retailer APIs: future partnership-only integration, subject to written authorization.

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

## Current limitations to state openly

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
