# Dataset and project schema comparison

**Checked:** 16 November 2026. This is a read-only contract comparison; no schema or data was changed.

## Source field coverage

Legend: **Yes** = described by source documentation; **Partial** = available/claimed, but incomplete or not verified per row; **No** = explicitly absent/not advertised; **Unknown** = file-level coverage could not be established.

| Source | Barcode / identity | Brand/category/variant | Ingredients | Nutrition | Image | Pack size / multipack | MRP / current price | Time/provenance |
|---|---|---|---|---|---|---|---|---|
| OFF live product database | Yes | Yes / variable | Partial | Partial | Yes / separate image license | Partial | MRP may appear as label/package fact; no reliable current selling-price feed | Product last-modified and source metadata; crowdsourced |
| PackSense India CSV | Barcode, name | Brand, PNNS and category tags; no variant guarantee | **No ingredient text** | Yes/partial, field coverage published | **No image or image URL** | Quantity/serving fields partial; no multipack field advertised | **No** | Build timestamp, last-modified, existence and quality flags |
| Shelfpedia India product CSV | One row per barcode by methodology | Brand/taxonomy | Yes/partial | Yes (selection requires nutrition/100g) | **Photos excluded** | Product quantity in source; no multipack guarantee | **No price data** | OFF snapshot date and per-block source/date |
| Mendeley 852-product dataset | Unknown; no advertised barcode | Names, brands, category/subcategory claimed | Claimed | Claimed | Unknown/not advertised | Serving size claimed; product pack-size not confirmed | Price claimed, historical/current status unknown | Collection/source metadata claimed; exact fields unverified |
| Label-variant dataset | Not a product catalog | Not a product catalog | Alias/canonical mapping | No product nutrition | No | No | No | Mapping source/version needs file inspection |
| OpenMRP | Barcode-keyed | Name, brand, category, multilingual name | Not advertised | Not advertised | Product images described | Pack sizes described | **MRP** described; not retailer sale price | Version/source (`pack`/`brand`/`gov`/`off`) described; dump generation date advertised |
| INDB | No packaged-product identity | No brand/variant | Recipe ingredients and amounts | Food/recipe nutrients | No | Serving/recipe quantities | No | Research methodology and source food tables |

## Reusable project model

The current PostgreSQL/SQLAlchemy architecture already has:

- `product`: `external_product_id`, nullable `barcode`, name, brand, a constrained five-value category, variant, numeric pack size/unit, raw ingredients, `field_evidence` JSON, claims, allergens, additives, warnings, timestamps. Task 1B commercial/media evidence is held in JSON rather than new columns.
- `product_source`: source type, URL, retailer/site, retrieval/verification timestamps, reliability, method and extraction log.
- `nutrient_value`: one nutrient per product with normalized numeric value/unit/basis, original value/basis, evidence status, source and note.
- `ingredient` / `product_ingredient`: canonical dictionary records plus ordered per-product label strings, declared percentages, match status and detail. Original label text is preserved.
- `price_observation`: separate INR price observations with pack size/unit, unit price, source URL/source, evidence and timestamp.
- `analysis_result` and `recommendation`: derived outputs, not source product records.

Existing dictionaries include 219 ingredient terms, 36 ingredient classes, 64 INS rows and 9 allergen rows; category and scoring references are CSV-based. Existing category mapping recognizes only five project categories.

## Gaps relative to Brand → Family → Variant → Pack → Listing

1. **No product-family entity or family-to-variant relation.** Current `product` rows can represent a SKU/pack, but brand family relationships are not modeled.
2. **Barcode is not unique or non-null in the database.** `external_product_id` is unique, but barcode is nullable and has no uniqueness constraint. OFF and URL imports of the same physical variant can therefore coexist without a canonical cross-source identity record.
3. **Retailer listing identity is thin.** `product_source.site`, URL, price source and timestamp exist; structured seller SKU, listing status, city/pincode and currency are not first-class in `price_observation`.
4. **Pack-size granularity needs care.** The numeric `pack_size` is total normalized quantity in g/ml; multipack count is evidence JSON, not a constrained relational field. A per-unit pack quantity plus count is not stored separately.
5. **MRP is not a dedicated numeric field/observation.** It is currently evidence JSON; the price observation table is for sale-price observations and has a hard-coded INR currency contract.
6. **Images are evidence JSON, not a media entity.** URL/source can be preserved but there is no separate image-rights/license, image retrieval status, or variant-match record.
7. **No raw per-field source conflict history.** Current product fields retain one selected value/evidence metadata plus aggregate source logs; multiple sources for the same field are not all stored as independent assertions.
8. **The category check constraint blocks the wider 16-category discovery taxonomy.** A later schema/taxonomy decision is required before adding categories to production.

## Existing Open Food Facts integration

`database.ingest.to_extraction` maps barcodes, names, first brand, category tags, quantity, ingredient text and nutrition fields. It keeps OFF source type, product URL and `last_modified_t` as the collection timestamp. It does **not** map `image_url`, manufacturer, multiple brand strings, MRP or listing prices. It maps sodium and salt, preserves missing values, and maps categories through `off_category_map.csv`.

`external_id="off:" + barcode` makes repeated imports of the same OFF code upsert that OFF-keyed row. URL imports use a URL hash, so they do not automatically deduplicate against OFF barcode rows. API helper `by_barcode` exists; search uses OFF v2-era endpoints/fields, while current OFF docs recommend v3.6 for new integration. Existing `best_match` is token-set similarity with an 85 cutoff and does not require barcode, pack size, formulation or variant agreement. It must remain candidate generation only.

## No live database count in this audit

`DATABASE_URL` was absent in this session. PostgreSQL table counts were not queried. Local filesystem counts are reported separately in `DATA_QUALITY_ASSESSMENT.md`; they must not be presented as production database totals.
