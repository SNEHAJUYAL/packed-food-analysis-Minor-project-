# OCR, NLP and Retailer Extraction Audit

**Project:** AI-Based Multimodal Packaged Food Analysis and Consumer Decision Support System  
**Audit date:** 16 November 2026  
**Scope:** Read-only audit, benchmark implementation, and permitted live retailer checks

## Executive summary

The existing OCR and ingredient pipeline is functional and covered by tests. Tesseract is correctly
installed and integrated, and the upload workflow reaches FastAPI, OCR, normalisation, storage, scoring,
and the frontend report. Ingredient parsing preserves unknown values and does not automatically classify
them as harmful.

The largest reliability risk is URL extraction from dynamic retailer pages. Blinkit returned partial
structured metadata, while Zepto and Swiggy Instamart returned empty bodies in this environment. Amazon
returned dynamic UI text that could be mistaken for a product name. Generic extraction is therefore not
reliable enough to establish product identity, price, variant, or nutrition automatically across retailers.

No scoring methodology, database schema, recommendation logic, or existing production extractor was
rewritten.

## Existing implementation

| Area | Finding |
|---|---|
| OCR engine | Tesseract through `pytesseract` and Pillow |
| Tesseract languages | `eng`, `osd`, `snum` |
| Image handling | EXIF transpose, grayscale, enlargement, autocontrast |
| OCR confidence | Not currently captured; `image_to_string` is used |
| OpenCV | Not installed or integrated |
| Claude Vision | Optional fallback when `ANTHROPIC_API_KEY` is configured |
| Ingredient NLP | Deterministic splitting, dictionary lookup, INS parsing, RapidFuzz |
| Allergen detection | Reference dictionary matching |
| URL extraction | JSON-LD/microdata, HTML heuristics, optional grounded LLM fallback |
| Upload API | `POST /api/analyze-upload` |
| Frontend | `UploadForm` validates type/size, shows loading/error state, submits FormData |

## OCR audit

### Verified behavior

The current OCR implementation:

- Corrects EXIF orientation.
- Converts images to grayscale.
- Enlarges small images.
- Applies autocontrast.
- Extracts text using Tesseract.
- Parses ingredients, price, pack size, nutrition, and claims.
- Stores the OCR transcript in the extraction log.
- Returns explicit errors for missing readers, unreadable images, invalid types, and oversized files.

### Smoke benchmark

The benchmark uses a reproducibly rendered label fixture, not a camera photograph:

| Metric | Result |
|---|---:|
| Character error rate | 0.0081 |
| Word error rate | 0.0000 |
| Latency | approximately 747 ms |
| Expected words | 22 |
| Extracted words | 22 |

These are harness-validation results, not real-food-label accuracy claims.

### OCR limitations

- No deskewing, rotation search, thresholding, denoising, cropping, or blur detection.
- No word-level confidence scores.
- No manually verified food-label photo dataset is currently committed.
- Camera-photo CER/WER and failure rate are therefore not measurable yet.

## NLP audit

Input:

```text
Whole Wheat Flour, Sugar, Maltodextrin, Soy Lecithin, Salt, Permitted Flavouring.
```

Result:

| Metric | Result |
|---|---:|
| Ingredient records | 6 |
| Record precision | 1.0 |
| Record recall | 1.0 |
| Record F1 | 1.0 |
| Dictionary matches | 5 |
| Uncertain matches | 1 |

`Soy Lecithin` is preserved as an ingredient but remains uncertain because it is not an exact term in
the current ingredient dictionary. The allergen detector still identifies `soy`. This is the correct
evidence-preserving behavior, but the dictionary could be improved with compound-ingredient aliases.

The parser:

- Splits commas and semicolons while respecting brackets.
- Removes declared percentages from names.
- Handles nested ingredients.
- Extracts INS/E codes.
- Performs exact, contains, and RapidFuzz matching.
- Labels unmatched ingredients as uncertain.
- Separates ingredient allergens from advisory allergens.
- Does not infer that an ingredient is harmful.

## Retailer compatibility audit

The live audit used the existing robots-aware, SSRF-safe fetcher and generic JSON-LD/HTML extractors.
No internal APIs were accessed and no access restrictions were bypassed.

| Retailer | Fetch | Identity | Quantity | Price | Ingredients/nutrition | Main limitation |
|---|---|---|---|---|---|---|
| Blinkit | Worked | Name and brand from JSON-LD | `75 g` from HTML | Missing | Missing | Partial metadata only |
| Zepto | HTTP succeeded, empty body | Missing | Missing | Missing | Missing | Dynamic/location/bot response |
| Swiggy Instamart | HTTP succeeded, empty body | Missing | Missing | Missing | Missing | Dynamic/location/bot response |
| Amazon India | Worked | Incorrect dynamic title: “Adding to Cart...” | Missing | Missing | Weak ingredient heuristic | Dynamic/anti-bot page |

The detailed machine-readable output is in [`retailer_audit.json`](./retailer_audit.json).

### Product identity risk

Open Food Facts matching currently uses token-set similarity with an 85 cutoff. It does not require
barcode, retailer SKU, pack size, or variant agreement. It is suitable as a reference cross-check, but
not as proof that two retailer listings are identical.

## Dependency evaluation

| Technology | Status/recommendation |
|---|---|
| Tesseract | Keep as default; lightweight and CPU-compatible |
| OpenCV | Consider after real-photo benchmark; useful for preprocessing |
| PaddleOCR | Benchmark only if Tesseract fails on verified photos; adds model/runtime dependencies |
| RapidFuzz | Keep; already integrated and lightweight |
| spaCy | Not required yet; a PhraseMatcher/EntityRuler alias layer may be useful later |
| Transformers | Do not add now; generic NER is not food-specific and adds substantial model/runtime cost |
| Claude Vision | Keep optional; transcript grounding is already implemented |

Currently absent: `cv2`, `paddleocr`, `spacy`, and `transformers`.

## BuyHatke and Flash

### BuyHatke

BuyHatke publicly provides consumer price comparison and tracking products. No public self-service
developer API, API documentation, or published commercial API pricing was found. Treat access as
partnership-only until written authorisation is obtained.

### Flash

The publicly discoverable Flash API documentation describes a South African prepaid/payments platform,
not an India-focused packaged-food price intelligence API. No authorised India-relevant integration was
verified.

No adapter was added, and no internal endpoint or application behavior was reverse-engineered.

## Tests and artifacts

Relevant validation completed:

- OCR/NLP/upload focused tests: 27 passed.
- Evaluation tests: 8 passed.
- Extraction regression tests: 55 passed.
- Existing full backend suite previously passed: 162 tests.
- Existing frontend suite previously passed: 40 tests.
- TypeScript and ESLint previously passed.
- `git diff --check` passed.

Artifacts:

- [`ocr_nlp.py`](../src/evaluation/ocr_nlp.py)
- [`retailer_audit.py`](../src/evaluation/retailer_audit.py)
- [`test_ocr_nlp_benchmark.py`](../tests/test_ocr_nlp_benchmark.py)
- [`evaluation_results.json`](./evaluation_results.json)
- [`retailer_audit.json`](./retailer_audit.json)

## Recommended next steps

1. Collect and manually label real food-label photographs.
2. Measure real-photo CER, WER, latency, and failure rate.
3. Add confidence-aware OCR using `image_to_data`.
4. Evaluate OpenCV preprocessing against the real-photo baseline.
5. Add compound aliases such as `soy lecithin` to the ingredient reference data.
6. Design retailer-specific adapters with strict identity evidence requirements.
7. Require barcode/SKU/variant/quantity agreement before declaring products identical.
8. Contact BuyHatke and Flash for written API or partnership terms before any integration.

## Remaining limitations

- No real-photo accuracy claim can be made yet.
- Retailer pages are dynamic, location-dependent, and unstable across requests.
- Prices and availability can change by location and time.
- Generic extraction does not reliably obtain product images.
- Authorised BuyHatke/Flash access is unresolved.
- No production fixes were applied during this audit phase.
