# Task 2A-6.2 Implementation Report

## Completed

- Unified `/api/analyze-url` and `/api/product-candidates/from-url` around `authorize_product_url()` and the existing central source registry. URL syntax and host registration are checked before DNS validation or HTTP access. Open Food Facts remains the only enabled external product-page source.
- The saved-analysis pathway still uses existing SSRF/destination checks, robots handling, rate limits, timeout/size limits and caching. Fetches are confined to the registered source hosts, including redirects. Policy-scoped cache keys prevent restricted requests from reusing the older unrestricted URL cache entries.
- Unknown, disabled, unauthorized or undocumented sources return `source_policy_blocked` without DNS or page requests. No retailer registration or authorization was added.
- Added **Preview candidate (not saved)** to the landing-page analysis form. It uses the candidate endpoint, presents the result as unverified, displays extracted identity, serving size, ingredients, nutrition, image URL references, missing-field warnings, conflicts and source/field provenance, and does not navigate to a saved report.
- Candidate preview errors explain invalid URLs, source-policy blocks, timeouts, fetch failures and unsupported content. Empty extraction is rendered with explicit missing-field guidance.
- Updated the API documentation to distinguish saving/scoring from candidate-only extraction and document the shared source policy.

## Files changed for this task

- `src/acquisition/product_url.py`
- `src/services.py`
- `src/extract/fetch.py`
- `web/src/components/AnalyzeForm.tsx`
- `web/src/lib/api.ts`
- `web/src/lib/types.ts`
- `tests/test_api_db.py`
- `tests/test_fetch.py`
- `tests/test_product_url_api.py`
- `web/src/__tests__/AnalyzeForm.test.tsx`
- `docs/api.md`
- `reports/TASK_2A_6_2_IMPLEMENTATION_REPORT.md`

No database schema, source workbook, candidate data, or dependencies were changed. No network product-page requests were made by the tests.

## Verification

```text
.venv/bin/python -m pytest tests/test_product_url_acquisition.py tests/test_product_url_api.py tests/test_api_db.py tests/test_fetch.py tests/test_pipeline_api.py -q
74 passed

cd web && npm test -- --run
7 test files passed; 44 tests passed

cd web && npm run typecheck
passed

cd web && npm run lint
passed
```

Coverage includes unauthorized-source zero-fetch behavior on both pathways, registered Open Food Facts extraction through mocks, redirect confinement, cache isolation, candidate non-persistence, candidate missing/conflict/provenance states, and existing saved analysis, comparison and recommendation tests.

## Remaining limit

Retailer URLs remain blocked until documented authorization is added to the source registry. The candidate preview does not save, score, compare, or recommend, by design.
