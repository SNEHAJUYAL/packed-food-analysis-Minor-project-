# Product data acquisition

Covers Tasks 2A-5 to 2A-6.3 as implemented in `src/acquisition/`, `src/extract/` and `src/services.py`,
checked on 16 November 2026. Route details are in [api.md](api.md).

## 1. Acquisition foundation (`src/acquisition/`)

| Module | Contents |
| --- | --- |
| `models.py` | Versioned envelope `AcquisitionRecord` with `ProductIdentity`, `RetailerListing`, `PriceObservation`, `ImageReference`; `FieldValue` (value + state) and `FieldProvenance`; `RawSourceRecord` with SHA-256 payload hash; `AcquisitionContext` (run id, time, PIN code); `PolicyDecision`; `ValidationIssue` |
| `adapter.py` | `ProductSourceAdapter` protocol: `check_policy`, `fetch`, `normalize`. Adapters must not write to the database |
| `registry.py` | `SourceRegistration` and `SourceRegistry`; `DEFAULT_SOURCE_REGISTRY` |
| `validation.py` | Record and batch validation (see [DATASET_AND_DATA_ENGINEERING.md](DATASET_AND_DATA_ENGINEERING.md#6-provenance-and-quality-validation)) |
| `orchestration.py` | `run_dry_run`: policy gate → fetch → normalise → validate, with no database writer by design |
| `product_url.py` | Product URL candidate service (Task 2A-6.1/6.2/6.3) |
| `catalog_workbook.py` | Read-only importer for the Complete Product Catalog workbook |

## 2. Central source authorization

The registry **fails closed**: a source is allowed only if it is registered, `enabled`,
`authorization_status == "permitted"`, has written `authorization_evidence`, and (for network access)
`network_acquisition` is true. The decision is made from URL syntax only, before any DNS lookup or HTTP
request.

| source_id | Type | Enabled | Authorization | Network | Domains |
| --- | --- | --- | --- | --- | --- |
| `open_food_facts` | official API | yes | permitted (ODbL-1.0, robots.txt respected) | yes, 60/min, ≥ 1 s apart | `world.openfoodfacts.org` |
| `complete_product_catalog` | operator file | yes | permitted (user-supplied workbook) | **no** | — |
| `operator_price_file` | operator file | no | unknown | no | — |
| `bigbasket` | authorized feed (placeholder) | no | unknown, no evidence | flag set, but blocked while disabled | none |

**Open Food Facts is the only enabled external product source.** Blinkit, Zepto, Swiggy Instamart,
Amazon, JioMart and BigBasket are not authorized; listing a website in the research register does not
authorize automated access.

How each path uses the registry (code as of 16 Nov 2026, 21:45 IST):

| Host | `POST /api/product-candidates/from-url` | `POST /api/analyze-url` |
| --- | --- | --- |
| Registered and permitted (OFF) | fetched, redirects confined to its domains | fetched, redirects confined to its domains |
| Registered but disabled / not permitted | 403 `unsupported_source`, no DNS/HTTP | 403 `unsupported_source`, no DNS/HTTP |
| Not registered | 403 `unsupported_source`, no DNS/HTTP | fetched once as a user-submitted page (SSRF, robots.txt, limits apply) |

This is the intended behaviour, confirmed by the team on 16 Nov 2026. It replaces the stricter rule in
the Task 2A-6.2 report (which blocked unregistered hosts on both paths). Fetching one page that a user
submits is not authorization to collect from that site in bulk, and robots.txt is always honoured.

## 3. Product URL candidate (Task 2A-6.1)

`ProductURLExtractionService.acquire(url)` reuses the existing safe fetcher, JSON-LD and HTML extractors,
normaliser, acquisition models, registry and validation. It returns `ProductURLResult`:

| status | HTTP | When |
| --- | --- | --- |
| `candidate` | 200 | Product fields extracted |
| `invalid` | 422 | Malformed URL, wrong scheme, credentials or non-standard port |
| `blocked` | 403 | Source not authorized, destination blocked, redirect leaves registered hosts, robots.txt disallows |
| `failed` | 502 | Source could not be retrieved |
| `failed` + `product_extraction_failed` | 422 | Page retrieved, no product fields |

A candidate (`product-url-candidate/1`) carries:

* **Identity and content**: name, brand, description, category hint, variant, pack size, multipack count,
  GTIN, ingredients, nutrition with basis and serving size, allergens, claims, price, MRP, currency,
  availability.
* **Original and normalised values separately** in `field_evidence[]` (`original_value`,
  `normalized_value`), each with `provenance` and `validation_status` (`candidate`, `requires_review`,
  `conflict`, `invalid`). A price without a stated currency is not normalised as INR; an ambiguous
  nutrient unit is preserved but not normalised.
* **Missing-field warnings and conflicts** in `issues[]` (identity conflicts between JSON-LD and HTML,
  nutrition issues).
* **Image references**: `validation_status: url_syntax_valid_not_fetched`, association `product_entity`
  or `page_level_unverified`. Image URLs are not requested.
* **Source attribution and licence** from the registration, and `additional_product_candidates` when a
  page has several product entities (never silently picked as an exact match).

Nothing is saved, scored, compared or recommended.

## 4. Error handling (Task 2A-6.3)

`extract.fetch.public_source_fetch_error` maps internal fetch errors to stable public codes:

| Code | HTTP | Meaning | User guidance shown |
| --- | --- | --- | --- |
| `unsupported_source` | 403 | Source not authorized, or redirect leaves its hosts | Upload a saved page or screenshots |
| `robots_disallowed` | 403 | robots.txt disallows the page | "We respect its access restrictions"; upload instead |
| `source_fetch_failed` | 502 | Network failure, timeout or non-HTML content | Upload instead |
| `product_extraction_failed` | 422 | Retrieved but no product fields | Upload label images or enter details manually |
| `blocked_destination` | 400 | Private/loopback/link-local address, bad scheme, port or credentials | — |
| `invalid_url` | 422 | Not a full http(s) URL | — |

The application never bypasses robots.txt, logins, location gates or anti-bot controls.

## 5. Offline alternatives

| Path | Endpoint | What happens | Saved? |
| --- | --- | --- | --- |
| Saved HTML page (⌘S / Ctrl+S) | `POST /api/analyze-upload` (`.html`, ≤ 5 MB) | Parsed locally with the JSON-LD and HTML extractors. **No scripts executed, no external resources or remote images fetched, LLM fallback disabled.** Canonical link or `og:url` recorded if no `page_url` given. `source_type: saved_page`; report labels evidence user-supplied and unverified | Yes, scored |
| Packaging photo / ingredient label / nutrition table / app screenshot | `POST /api/analyze-upload` (JPEG/PNG/WebP/GIF ≤ 8 MB) | Tesseract OCR (default) or Claude vision (if key set). Transcript kept in the extraction log. `source_type: photo`; record id is the image hash, so re-uploading the same photo replaces its record | Yes, scored |
| User corrections on upload | form fields `brand`, `variant`, `pack_size_text`, `ingredients_text`, `nutrition_basis`, `nutrition_text`, `name` | Corrections take precedence over OCR values; the original OCR transcript is retained | Yes |
| Manual entry | `POST /api/analyze-manual` (JSON) | Name required; brand, category, variant, pack size/unit, ingredients, nutrition basis + values, price optional. `source_type: manual`, reliability `manual_entry`, unverified banner | Yes, scored |

All user-supplied evidence (photos, saved pages, manual entries) stays **unverified**. The candidate
preview is a separate action from these saved analyses.

## 6. Workbook candidate import

`CompleteCatalogWorkbookAdapter` implements the adapter protocol for the user-supplied catalogue workbook
(network off). It writes only to `data/annotation/candidate_sources/complete_product_catalog/`, never
fetches image URLs and never writes to the database. See
[DATASET_AND_DATA_ENGINEERING.md](DATASET_AND_DATA_ENGINEERING.md#32-complete-product-catalog-import).

## 7. Retailer prices

Retailer price collection is manual: `data/verified/prices/price_entry_sheet.csv` →
`./run.sh prices <csv>` (`database/prices.py`). Zepto and Blinkit offer no public price API and automated
collection is treated as not permitted. See
[PRODUCT_COMPARISON_AND_RECOMMENDATIONS.md](PRODUCT_COMPARISON_AND_RECOMMENDATIONS.md#5-price-intelligence).

## 8. Supporting reports

`reports/DATA_ACQUISITION_ARCHITECTURE_PROPOSAL.md`, `reports/FIRST_AUTHORIZED_SOURCE_IMPLEMENTATION_PLAN.md`,
`reports/PRODUCT_URL_EXTRACTION_ARCHITECTURE.md`, `reports/PRODUCT_URL_SOURCE_AUTHORIZATION_LIMITATIONS.md`,
`reports/PRODUCT_URL_TEST_RESULTS.md`, `reports/TASK_2A_6_2_IMPLEMENTATION_REPORT.md`,
`reports/TASK_2A_6_3_IMPLEMENTATION_REPORT.md`, `docs/SOURCE_ADAPTER_INTERFACE_SPEC.md`,
`docs/retailer_extraction_assessment.md`.
