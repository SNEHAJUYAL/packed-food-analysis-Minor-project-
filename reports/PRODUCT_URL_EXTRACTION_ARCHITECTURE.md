# Native Product URL Extraction Architecture

## Repository inspection and reuse

| Existing module | Reused behavior |
|---|---|
| `src/extract/fetch.py` | HTTP(S) syntax/destination checks, public-IP validation, robots policy, timeout/size limits, per-host pacing, redirect validation. Extended with a final-URL fetch helper and registered-host redirect confinement. |
| `src/extract/jsonld.py` | Existing JSON-LD/microdata `Product` extraction and source-specific raw values. |
| `src/extract/html_parser.py` | Existing HTML metadata, pack, ingredient, nutrition, image, allergen and serving-size fallback extraction. |
| `src/extract/image_validation.py` | HTTPS image URL syntax validation without probing/downloading the image. |
| `src/normalise/build.py` and `src/normalise/units.py` | Existing product normalization, unit parsing, conflict detection and per-serving nutrient scaling. Ambiguous-unit nutrients are kept in source evidence but excluded from normalization. |
| `src/acquisition/models.py`, `registry.py`, `validation.py` | Existing candidate, provenance, source policy and validation types. The service emits an `AcquisitionRecord`; it does not write to a database. |

The service entry point is `ProductURLExtractionService.acquire(url, context)`. It accepts an injectable fetch function for deterministic tests. It returns a `ProductURLResult` with a policy/fetch outcome and, when extraction succeeds, a `ProductURLCandidate` containing the shared acquisition envelope, normalized `Product`, source field evidence, image references and quality issues. The DB-free application endpoint is `POST /api/product-candidates/from-url`; it returns candidate data without invoking scoring or persistence.

## Request flow

1. Parse HTTP(S) URL syntax without DNS access.
2. Match the submitted hostname to an enabled, documented network source registration. Unsupported and denied hosts return a blocked result before DNS or HTTP access.
3. Delegate destination safety, robots.txt handling, pacing, response limits, timeout and redirect checks to `extract.fetch`. Redirects remain inside the source registration's host allowlist. This extraction entry point does not use the shared HTML cache so it can retain the final URL.
4. Run the existing JSON-LD extractor first and HTML fallback second. No LLM fallback is used.
5. Pass extracted data through the existing normalizer. Keep all source values and per-source provenance in `field_evidence`; keep normalized values separate. Conflicts are surfaced and no exact product match is made.
6. Emit an unverified candidate with a deterministic URL/name/brand/barcode identity hash, field-level provenance, and validation results. No database writer or annotation promotion is called.

## Output and quality controls

- `AcquisitionRecord.product_identity` holds name, brand, interpreted category, variant, quantity/unit, multipack and optional barcode.
- `listing` holds the submitted URL, title and image references. The Open Food Facts domain is a product reference source, not a retailer, so retailer name remains unknown.
- `observation` is present only where offer data is explicitly extracted. Currency is never inferred; a price without an unambiguous explicit currency is retained as source evidence and not normalized as INR. MRP, availability, selling price and currency remain separate.
- `field_evidence` retains each source's original value, normalized value where available, source/final URL, extraction method/time, evidence state and validation status.
- Images are represented as URL references only. JSON-LD images are associated with a product entity as candidates; page-level HTML images require review. URL syntax is checked, image bytes/MIME/reachability are not requested.
- Missing names, brands and ingredients, identity conflicts, ambiguous pack sizes/variants, invalid nutrition units/barcodes, duplicate page Product entities, and uncertain image associations are reported.

See [source authorization and limitations](PRODUCT_URL_SOURCE_AUTHORIZATION_LIMITATIONS.md), [synthetic candidate example](PRODUCT_URL_SYNTHETIC_CANDIDATE.json), and [test results](PRODUCT_URL_TEST_RESULTS.md).

## Boundaries

Only the currently registered Open Food Facts product-page domain is eligible. No retailer adapters, exact identity matcher, scoring, recommendation, database persistence, image download, or verified-label promotion is included.
