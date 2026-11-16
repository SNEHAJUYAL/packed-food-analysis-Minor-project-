# Database compatibility assessment

## Current schema

The SQLAlchemy schema is defined in `src/database/models.py`; migrations are Alembic `0001_normalised_schema.py` and `0002_site_and_upload_sources.py`.

- `product` stores a canonical-ish product row: external ID, barcode, name, brand, one constrained category, variant, normalized pack size/unit, ingredients, nutrition basis, field evidence JSON, claims, conflicts and warnings.
- `product_source` stores source type, source URL, optional site, collection/verification times, reliability, extraction method and log. It is linked to a product rather than to a retailer listing identity.
- `price_observation` stores positive INR price, optional pack size/unit and derived price per 100g/ml, source URL/text, evidence status and observation timestamp.
- `nutrient_value`, `product_ingredient` and `product_claim` support existing analysis data and should be populated through the existing repository/normalizer rather than by a new acquisition-specific implementation.

`Product` in `src/core/schema.py` already includes evidence-wrapped name, brand, category, variant, pack size/unit, selling price, image URL, MRP, discount, availability, multipack count and retailer. It also has a source URL, collected timestamp and last-verified timestamp. `Evidence` stores a value, evidence label, source string and note.

## Field mapping and limitations

| Acquisition concept | Existing representation | Compatibility |
|---|---|---|
| Product name, brand, category, variant | `product` scalar columns and `field_evidence` JSON | Direct for supported categories; category enum is intentionally narrow |
| GTIN/barcode | `product.barcode` | Direct string storage; no database check digit or uniqueness constraint |
| Pack quantity/unit | `product.pack_size`, `product.pack_unit` | Direct after conversion to `g` or `ml`; multipack total size can lose unit count/detail |
| Product image reference | `product.field_evidence.image_url` | Value/source/note possible; not a dedicated image asset/evidence table |
| Retailer identity | `product_source.site`, `product.field_evidence.retailer`, or textual `price_observation.source` | Partial; no normalized retailer table or listing identity |
| Listing URL | `product_source.source_url` and `price_observation.source_url` | Direct URL fields, but neither row is keyed to a distinct listing entity |
| Selling price and time | `price_observation.price_inr`, `observed_at` | Direct; append-only behavior is intended, although duplicate matching is implemented in importer logic only |
| Pack size for priced listing | `price_observation.pack_size`, `pack_unit`, derived unit price | Direct and already normalized by manual importer |
| MRP / discount | Product-level `field_evidence` JSON | Can be stored, but is mutable/latest product-level state, not historical observation-level state |
| Availability | Product-level `field_evidence` JSON | Can be stored but is not tied to one listing observation; history is lost |
| Location/PIN | No dedicated column | Current importer embeds location text in the `source` string; not safely queryable or canonical |
| Field-level provenance | `field_evidence` maps field to label/source/note; `ProductSource` stores record provenance | Partial: provenance is a source string, not a foreign-key reference to a source record plus raw field/value locator |
| Source license/attribution/raw row locator | Not first-class in DB | Keep in acquisition run/staging manifest and/or extend schema only after review |
| Listing name, listing SKU, listing pack variant | Not represented separately | Requires a listing entity for lossless multi-retailer support |

## Existing ingestion semantics and risks

`repository.save_product()` resolves by `external_product_id`, replaces current scalar/product analysis fields on repeat, and appends sources and price observations. Thus product updates and price history are already separate at a basic level, but price observations remain attached directly to the product. `database.prices.import_rows()` only imports hand-recorded rows that identify an OFF product, have positive price, an allowed platform, an exact/different-size match value, parseable date and pack size. It does not consume MRP, availability, or structured location fields. The allowed platform set is currently small. Duplicate detection uses product ID, source string, timestamp and price, so it does not distinguish every possible listing/location/pack conflict.

The URL ingestion currently treats the page URL as the product source and can persist parsed offer values in product-level evidence. Repeated URLs therefore update current product data while retaining earlier source records; retailer listing history is not modeled explicitly.

## Recommended approach

### Phase 1: no migration

Use the canonical acquisition envelope and staging validation layer. For product identity, call `normalise.build` and `repository.save_product` with a source-specific external ID. For a retailer price, append `PriceObservation` only after an explicit identity and pack match. Preserve listing URL, source name, timestamp, evidence status, and normalized pack/price. Keep non-queryable values such as PIN, source license, raw source locator, and observation-specific MRP in a sidecar acquisition manifest until product requirements justify a migration. Do not encode structured fields into strings if downstream querying is required.

This phase supports Open Food Facts and an operator-file/manual-price adapter with existing schema. OFF does not supply retailer prices; its data must remain labeled crowdsourced reference data.

### Phase 2: listing-level migration, separately approved

For robust retailer history, introduce `retailer` and `retailer_listing` entities, then link `price_observation` to a listing. Add observation-level MRP, discount, availability, location/PIN, source record/evidence reference, capture timezone and source-run ID. Add unique/idempotency keys and supporting indexes based on observed requirements. Preserve `product` as the product identity. Plan data backfill and downgrade behavior before migration; do not run this as part of the audit.

## Compatibility decision

The existing database can accept a bounded first implementation using product identity, sources, and timestamped prices without migration. It cannot faithfully model multiple retailer listings and observation-specific location/MRP/availability over time. Any implementation claiming full multi-retailer fidelity on the current schema would either lose fields or overload unrelated fields. The limitation must remain explicit until a separately reviewed schema change is approved.
