# First authorized source implementation plan

## Recommended first source: Open Food Facts (existing integration)

The repository already has the best-supported permitted network source: Open Food Facts (OFF). `scripts/fetch_off_india.py` calls the documented OFF API, requests a constrained field set, identifies the project user agent, and spaces requests. `src/database/ingest.py` converts OFF records through the existing normalizer and repository, labels the source, and records the OFF product URL. Its module documentation states that OFF data is ODbL and must be credited. Existing documentation also warns that OFF is crowdsourced reference data, not ground truth.

The first adapter implementation should formalize this existing path, not fetch a second copy or alter its data semantics. It should retain current API parameters and output behavior while adding the common adapter metadata/envelope, run manifest, validation report and dry-run mode. During rollout, compare the canonical output with the current `to_extraction()` and `build_product()` behavior using synthetic fixtures, then use an offline sample for end-to-end tests. A real network run or database import should require separate operator authorization and explicit output paths.

## Staged implementation

### 1. Contract and source registry

- Define `AcquisitionContext`, `RawSourceRecord`, `AcquisitionRecord`, `FieldProvenance`, `ValidationIssue`, `PolicyDecision`, and `SourceCapabilities`.
- Register OFF metadata: official API endpoint, ODbL-1.0, required attribution, allowed fields, user agent, request pacing, timeout, and source limitations.
- No retailer source is enabled by default. A source policy decision of unknown or denied prevents fetch/persistence.

### 2. Wrap existing OFF acquisition

- Keep `scripts/fetch_off_india.py` as the current CLI until equivalence is demonstrated; make it call the adapter runner later, rather than duplicate its pagination/query logic.
- Preserve source identifiers and `last_modified_t` separately: the latter is OFF's source modification timestamp, not the time this project collected the record.
- Record `collected_at` from the acquisition run in UTC, input/API parameters, adapter version, OFF code, API URL, source license and attribution.
- Preserve missing values. Do not treat OFF package images, nutrient data, ingredient text, GTIN, or categories as independently verified.
- Keep license/attribution obligations visible in every exported data package. Review share-alike implications before combining and redistributing datasets.

### 3. Normalize and validate

- Reuse `database.ingest.to_extraction`, `category_for`, `normalise.build`, and `normalise.units`.
- Validate record shape, barcode format/check digit, pack quantity/unit, known category mapping, and numeric nutrition values. A checksum-valid code remains only a formatting pass.
- Keep country/category/source tags and original OFF fields in the raw record reference. Send unsupported categories and conflicting/ambiguous identity records to quarantine instead of coercing them.
- Distinguish OFF values from package evidence and from any later retailer observation.

### 4. Dry-run and persistence

- Default to `dry_run=True`; report accepted/skipped/quarantined counts and reasons without opening a write transaction.
- On explicit import mode, use existing `ingest_records()`/`repository.save_product()` and idempotent `off:<code>` identity. Avoid saving synthetic records through the real-source registry.
- Before replacing existing data, show a preview of product IDs and changed field values; do not silently replace candidate/manual verification values.
- Write an acquisition manifest with input hash/cursor, API query, run times, package version, license and attribution.

### 5. Retailer price source after OFF adapter parity

There is no repository evidence of an authorized retailer API/feed yet. The first price-observation adapter should therefore initially be an **operator-provided evidence file** with structured retailer, listing URL, exact listed name, selling price, MRP, pack, observed timestamp/timezone, availability, PIN, and evidence reference. It can wrap the existing `database.prices.import_rows()` after improving validation and provenance handling; it must not claim the file is live or verified merely because it is complete. Automated retailer adapters follow only after written authorization or an expressly permitted interface is documented. BigBasket remains blocked from automated collection until that condition is met.

## Acceptance checks before implementation approval

- Offline tests prove repeated OFF codes do not create duplicate products and missing fields remain missing.
- Unit tests cover invalid GTIN check digits, quantity/unit conversion, category quarantine, malformed nutrition values, duplicate raw records, source timestamps, and field provenance.
- Dry-run and write mode are visibly distinct; no production DB is touched by tests.
- OFF attribution/license appears in stored source records and data exports.
- No source adapter can bypass the existing safe-fetch constraints or source policy gate.
- Manual retailer-price file tests verify unit-price arithmetic and exact pack/product compatibility; absent PIN/evidence values remain null.

This document is a plan only. No adapter, importer, schema, data or dependency changes were made.
