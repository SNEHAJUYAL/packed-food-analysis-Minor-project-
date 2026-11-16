# Native product data acquisition: repository audit

## Scope and evidence

This is a read-only audit of the repository and the five supplied workbooks. The attached pasted text requests live product verification, price research, and creation of a revised Excel workbook and CSV deliverables. Those are separate instructions from this request. This audit does not perform those actions, validate retailer listings, import workbook data, or change the source workbooks.

Workbook names such as “verified” and cell values such as “Verified Barcode” are not treated as proof. The workbook samples show that at least some such columns contain placeholders (for example, “Pending Physical Scan” and “Pending Field Capture”), and a photo column in one workbook is a click-to-view label rather than a supplied image. These files are useful as examples of input structure, not as verified acquisition records.

## Existing codebase

The repository already has the main building blocks for product extraction and storage:

- `src/extract/fetch.py` provides safe HTTP fetching for product pages: HTTP(S)-only URLs, public-address checks, redirect revalidation, robots handling, per-host pacing, response limits, timeouts, and caching.
- `src/extract/jsonld.py` and `src/extract/html_parser.py` extract structured and fallback product fields from a URL. `src/extract/image_validation.py` validates image references without downloading image bodies.
- `src/normalise/build.py` combines source extractions, preserves field evidence labels, detects conflicts, normalizes package units and parses MRP/discount/availability/retailer/multipack values.
- `src/normalise/units.py` converts mass to grams, volume to millilitres, parses common multipacks, and calculates unit price. It does not infer mass-volume equivalence.
- `src/database/ingest.py` plus `scripts/fetch_off_india.py` implement Open Food Facts acquisition and ingestion. The project labels OFF as crowdsourced reference data and documents ODbL attribution/share-alike obligations.
- `src/database/prices.py` implements an existing manual CSV import for observed prices. It checks price, platform, same-product confirmation, timestamp, pack size and product match; it skips invalid/unmatched rows and de-duplicates a limited observation key.
- `src/database/repository.py` persists the normalized `Product` object, provenance, evidence, nutrients, ingredients, and price observations.

There is no general source-adapter interface, source registry, acquisition run record, or reusable staged validation/quarantine layer today. The current URL pipeline is a single page-analysis path, while OFF and price ingestion use separate scripts/functions.

## Dependency and runtime assessment

`pyproject.toml` requires Python 3.11 or newer. Existing relevant dependencies include `httpx`, `beautifulsoup4`, `extruct`, `pydantic`, SQLAlchemy, Alembic, PostgreSQL driver, pandas, and pytest. `openpyxl` appears in the root `requirements.txt` but is not in the `pyproject.toml` core dependency list; workbook import should not become a mandatory package dependency without intentionally updating dependency metadata. The existing JSON/CSV pathways do not require adding a new dependency for an adapter framework.

## Supplied workbook structure, at a glance

Read-only workbook inspection found:

| Workbook | Sheet | Non-empty data rows after header | Main shape |
|---|---|---:|---|
| `authentic_multi_retailer_dataset.xlsx` | Field Data & Multi-Retailer | 76 | Repeated product-retailer rows; 12 columns, including price, availability, date and location context |
| `verified_project_data_with_urls_full.xlsx` | Verified Data Collection | 31 | Product/listing rows; 13 columns, includes URL, selling price, MRP, collection date/time and PIN/location |
| `verified_project_data_with_urls.xlsx` | Verified Data Collection | 31 | Similar shape to full workbook; 13 columns |
| `verified_real_market_pricing_and_photos.xlsx` | Verified Procurement Data | 30 | Wide product rows with five retailer-price text cells, barcode and a photo link label; 11 columns |
| `authentic_multi_retailer_dataset_with_invoices.xlsx` | Verified Invoice Additions | 27 | Repeated product-retailer rows; 12 columns |

These counts describe workbook rows, not unique validated products or genuine retailer observations. The wide five-retailer sheet is not a normalized observation table and embeds prices in text. No image assets were extracted or tested. The proposed importer should preserve each workbook and its rows as source records, normalize only into a staging representation, and report unresolved claims rather than silently promoting them to verified data.

## Audit conclusion

The repository is suitable for a small, staged acquisition framework by reusing existing fetch, extraction, normalization, evidence, OFF, price, and persistence components. The principal architectural gap is not another scraper: it is a common, typed source contract and validation boundary that preserves raw inputs and field-level provenance before any write. Retailer-specific collection must remain disabled unless the relevant source offers an expressly permitted interface or written authorization. BigBasket is explicitly excluded from automated listing/price collection unless the authorization condition in the task is met.
