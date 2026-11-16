# Task 2A-6.3 — Implementation Report

## Summary

Implemented accurate source-blocking errors and offline extraction paths. URL acquisition remains policy-gated; blocked sources are never retried through a different network path. Users can instead provide saved HTML, product-package images with corrections, or manually entered details. User-supplied evidence is clearly marked unverified.

## Completed

- Centralized public fetch error mapping distinguishes `unsupported_source`, `robots_disallowed`, `source_fetch_failed`, and `product_extraction_failed` with stable HTTP statuses and actionable messages.
- Both saved-product URL pathways apply the central source registry before making network requests. Open Food Facts remains the only enabled external source; unsupported sources are not DNS-resolved or fetched.
- A robots denial returns its own restriction message and does not trigger retries or a bypass.
- Saved HTML is parsed locally with JSON-LD and HTML parsers. Scripts are not executed, external references are not fetched, remote images are not downloaded, and the optional LLM fallback is disabled.
- Packaging-photo analysis supports explicit user corrections for brand, variant, pack size, ingredients, and nutrition. Corrections take precedence while original OCR output remains in the extraction log.
- Added an explicit manual-entry endpoint and form. It runs only after the user submits, requires a product name, validates pack and nutrition units, and labels the saved analysis as manual and unverified.
- URL error states link to saved-page upload, packaging-image upload, and manual entry. Candidate preview remains visibly separate from saved/scored analysis.
- API documentation now describes the error codes and offline workflows.

## Changed files for this task

- `src/extract/fetch.py`
- `src/services.py`
- `src/acquisition/product_url.py`
- `src/api/main.py`
- `web/src/components/AnalyzeForm.tsx`
- `web/src/components/UploadForm.tsx`
- `web/src/components/ReportView.tsx`
- `web/src/lib/api.ts`
- `web/src/lib/types.ts`
- `docs/api.md`
- `tests/test_api_db.py`
- `tests/test_fetch.py`
- `tests/test_pipeline_api.py`
- `tests/test_upload.py`
- `tests/test_product_url_acquisition.py`
- `tests/test_product_url_api.py`
- `web/src/__tests__/AnalyzeForm.test.tsx`
- `web/src/__tests__/UploadForm.test.tsx`
- `web/src/__tests__/ReportView.test.tsx`
- `reports/TASK_2A_6_3_IMPLEMENTATION_REPORT.md`

The repository already contains unrelated, uncommitted work from earlier tasks; that work was left in place.

## Verification

- Backend focused suite: **96 passed** (`tests/test_product_url_acquisition.py`, `tests/test_product_url_api.py`, `tests/test_api_db.py`, `tests/test_fetch.py`, `tests/test_upload.py`, `tests/test_pipeline_api.py`).
- Frontend suite: **47 passed** across 7 test files.
- TypeScript: `npm run typecheck` passed.
- ESLint: `npm run lint` passed.
- `git diff --check` passed.
- Frontend test runtime used the already-installed Node **v24.7.0**. Node v18.20.8 cannot run the installed Vitest 5 / Rolldown stack because `node:util.styleText` is unavailable there.

No new dependencies, retailer authorizations, database schema changes, external network requests, or retailer adapters were added. No model was trained and no data was imported.

## Remaining limitations

- Open Food Facts page fetching remains subject to its robots rules and may be denied for a particular page. The application explains the denial and offers offline input.
- Offline extraction depends on what the saved page contains. Browser-saved pages may omit dynamically rendered product details; package photos may require human corrections or installed OCR support.
- Manual and uploaded values are user supplied and remain unverified; this workflow does not establish ground truth.
- No retailer website access or authorization behavior was expanded.

## Acceptance status

Task 2A-6.3 acceptance criteria are satisfied for the implemented workflows and tested behavior. Source coverage remains intentionally restricted to the existing authorized source, and offline evidence is explicitly represented as unverified.
