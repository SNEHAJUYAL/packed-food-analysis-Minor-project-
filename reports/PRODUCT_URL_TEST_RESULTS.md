# Product URL Extraction Test Results

## Focused regression run

```text
.venv/bin/python -m pytest tests/test_product_url_acquisition.py tests/test_product_url_api.py tests/test_fetch.py tests/test_extraction.py tests/test_units.py tests/test_acquisition_foundation.py -q
100 passed
```

Coverage includes synthetic JSON-LD and HTML-only pages, missing attributes, invalid URLs, blocked/denied sources, a supported hostname resolving to a private IP, redirect host confinement, missing/malformed/page-level image references, conflicting and ambiguous pack values, nutrition units and currency ambiguity, provenance, duplicate page Product entities, and candidate status.

## Wider suite

```text
.venv/bin/python -m pytest -q
```

Collection stopped because `openpyxl` is absent from the active `.venv`; the two workbook test modules could not import. No dependency was installed. The rest of the suite was run with those two modules excluded:

```text
.venv/bin/python -m pytest -q --ignore=tests/test_catalog_workbook_candidate.py --ignore=tests/test_dataset_consolidation.py
208 passed
```

All tests use local fixtures or mock transports. No live product URL or image request was made.
