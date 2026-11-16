# Task 2 implementation report: native acquisition foundation

## Implemented

- Added Pydantic v2 models for `AcquisitionContext`, `RawSourceRecord`, `AcquisitionRecord`, `FieldProvenance`, `ValidationIssue`, `PolicyDecision`, `SourceCapabilities`, and nested product identity, retailer listing, and price-observation records. Schemas are versioned as `raw-source-record/1` and `acquisition-record/1`.
- Raw payloads receive a deterministic SHA-256 digest; supplied digests are checked against the canonical payload. Missing string values normalize to `null`; no value is synthesized.
- Added the `ProductSourceAdapter` protocol with policy check, fetch, and normalization operations. Adapters return typed records and have no database dependency.
- Added a source registry with license, attribution, permitted fields, authorization evidence/status, enabled state, domains, and request pacing metadata. The central policy check fails closed for unknown, disabled, denied, or undocumented sources. Open Food Facts is registered from the repository's existing source/license documentation; operator price-file ingestion remains disabled until a policy/provenance registration is supplied. BigBasket is explicitly disabled with unknown authorization and has no collector.
- Added validation for GTIN-8/12/13/14 check digits, positive pack quantities, `g`/`ml` units, positive INR prices/MRP, discounts, timezone-aware timestamps, safe HTTP(S) URL shape, missing field provenance, missing values, and duplicate observation candidates. A valid GTIN checksum is not treated as product identity evidence.
- Added `run_dry_run()`. It evaluates central policy before adapter checks or `fetch()`, bounds record iteration, normalizes and validates records, and returns issues/results without importing database modules or writing to a database. `dry_run=False` is rejected because persistence is outside this foundation.
- Updated the adapter interface specification to describe the implemented contract and default registry.

## Files created

- `src/acquisition/__init__.py`
- `src/acquisition/adapter.py`
- `src/acquisition/models.py`
- `src/acquisition/orchestration.py`
- `src/acquisition/registry.py`
- `src/acquisition/validation.py`
- `tests/test_acquisition_foundation.py`
- `reports/TASK_2_IMPLEMENTATION_REPORT.md`

## Files modified

- `docs/SOURCE_ADAPTER_INTERFACE_SPEC.md`

No existing extraction, normalization, OFF ingestion, manual price importer, PostgreSQL model/migration, or production record was modified. No source adapter for any retailer was implemented. No network request, database import, dependency installation, commit, push, or deployment was performed.

## Test results

Passed:

```text
python -m pytest tests/test_acquisition_foundation.py tests/test_fetch.py -q
40 passed
```

The acquisition tests use synthetic fixture strings only. Safe-fetch tests use mocked HTTP transports and test URL-policy behavior without live requests.

Compatibility tests for the existing OFF and manual price import modules could not be collected in this environment: `rapidfuzz` is required by `src/normalise/ingredients.py` but is not installed. No dependency was installed. The attempted command was `python -m pytest tests/test_acquisition_foundation.py tests/test_ingest.py tests/test_prices.py tests/test_fetch.py -q`; it stopped during collection with `ModuleNotFoundError: No module named 'rapidfuzz'` for `test_ingest.py` and `test_prices.py`. The new package does not import or modify those paths.

## Backward compatibility

The new package is additive and independent of `src/core/schema.py`, `src/database/*`, `src/extract/*`, and `src/normalise/*`. Existing safe-fetch tests pass, and no existing call signatures or storage behavior were changed. OFF/manual importer regression tests remain unverified in this environment due to the missing already-declared dependency. This foundation does not yet adapt existing OFF ingestion or manual price CSV into the canonical acquisition models.

## Remaining limitations

- There is no concrete OFF adapter, retailer adapter, file adapter, database writer, identity resolver, acquisition-run persistence, or migration. This task implements the reusable contract and dry-run boundary only.
- The default Open Food Facts authorization evidence references the repository's existing API and ODbL documentation; operators must recheck source terms and permitted fields before any future network run.
- URL validation checks URL syntax, scheme, credentials, and port. Network adapters must still use the existing safe fetch controls for DNS/IP, robots, redirect, timeout, and response-size enforcement.
- GTIN validation verifies formatting/checksum only. Product ownership requires independent evidence.
- Existing database schema cannot retain all observation-level retailer listing, MRP, availability, and location history without a separately approved schema change.
- `SourceRegistry` is in-memory configuration; it is not an authorization evidence management UI or immutable policy store.
