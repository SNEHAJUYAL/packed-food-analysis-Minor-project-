# Complete Product Catalog Field Mapping

This is a proposed, reviewable mapping from the workbook to the existing annotation/acquisition structures. Original cells are retained in `source_workbook_rows.jsonl` and `source_fields`; normalized values are candidate interpretations and retain provenance. No existing verified records are updated.

| Workbook field | Candidate representation | Notes |
|---|---|---|
| `Product Submission ID` | `identity.source_product_id.value`; annotation source identifier | Preserved verbatim as the source ID; worksheet and row locator retained. |
| `Product name` | `identity.name`; annotation identity name | Source text retained. |
| `Brand name` | `identity.brand` | Source text retained; no alias resolution. |
| `Product category` | `identity.category`; annotation category candidate | Existing taxonomy mapping is conservative. Unmapped values stay unmapped and source text remains. |
| `Product variant/flavour` | `identity.variant`; annotation variant name/flavour | Source text retained; not independently verified. |
| `Pack size` | `identity.pack_quantity`, `pack_unit`, annotation declared quantity | Original pack string preserved; parser output is only a candidate. Quantity ranges are flagged and not resolved. Multipack count is parsed only when explicitly represented. |
| `Barcode number` | Acquisition `identity.gtin`; annotation pack GTIN only for text cells | Original Excel cell type/value remains in `source_fields` and the workbook snapshot. Text barcodes preserve leading zeroes and receive checksum validation. Numeric cells remain numeric in acquisition records, are flagged for review, and are omitted from the string-typed annotation GTIN candidate; their raw value/type is recorded in `candidate_source_metadata.barcode_original_cell`. No leading zeroes are reconstructed and numeric cells are not treated as valid GTIN strings. |
| `Ingredients (copy from pack)` | Annotation `label.ingredients_original`; source field | Exact source transcription retained. Not normalized or verified against package images. |
| `Nutritional information (per 100 g/ml)` | Annotation nutrition panel text and conservative parsed amounts; source field | Panel text, basis, original amount and original unit (e.g. mg, g, kJ, kcal) are retained. Normalized amount/unit stay null because no conversion is performed. |
| `Marketing claims (exact wording)` | Annotation claims; research assertion `front_of_pack_marketing_claim` | Semicolon-separated source wording is split into candidate claim entries; original string remains in `source_fields`. |
| Front packaging photo JSON | `ImageReference` (`front_packaging_photo`, index 1) | Parsed URL/PVID/platform/type/index/status and source cell provenance. |
| Back packaging photo JSON | `ImageReference` (`back_packaging_photo`, index 2) | Same. |
| Ingredient-label photo JSON | `ImageReference` (`ingredient_label_photo`, index 3) | Same. |
| Nutrition-table photo JSON | `ImageReference` (`nutrition_table_photo`, index 4) | Same. |
| Barcode photo JSON | `ImageReference` (`barcode_photo`, index 5) | Same. |
| `Product source URL` | Product/listing `listing_url` and retailer-name provenance | URL is syntax-validated only; no request is made. When its host supports Zepto attribution, both `listing.retailer_name` and `listing.listing_url` provenance point to the exact `Sheet1` source URL cell, preserve the URL as `raw_value`, and use it as `source_url`. Unsupported or missing URLs leave retailer identity unknown. Image metadata does not determine retailer identity. No Blinkit/Instamart URLs are provided. |
| Indicative planning range | Original source field only | Not a retailer quote and never mapped to a retailer price observation. |
| `Blinkit price (₹)` | Blinkit candidate price record | A populated positive value is an unverified price observation; missing or invalid values stay null placeholders and are counted separately. No individual listing URL. |
| `Zepto price (₹)` | Zepto candidate price record | A populated positive value is an unverified price observation; missing or invalid values stay null placeholders and are counted separately. Zepto URL retained where valid. |
| `Swiggy Instamart price (₹)` | Swiggy Instamart candidate price record | A populated positive value is an unverified price observation; missing or invalid values stay null placeholders and are counted separately. No individual listing URL. |
| `Price checked date` | `PriceObservation.observed_date` | Date only. `observed_at` remains null; no time or PIN is inferred. |
| `Photo/source notes` | Annotation candidate source metadata and original source field | Preserved as a workbook assertion, not treated as proof of verification. |

## Price record status counts

All three price columns retain a candidate record slot per source product row. The quality report and manifest distinguish: populated positive values (unverified price observations), missing-value placeholders, and invalid-value placeholders. Only populated positive values contribute to `price_observation_record_count`; placeholders are not described as collected observations. The 25-row supplied workbook has 75 populated unverified price observations and no missing or invalid price placeholders.

## Acquisition record persistence and identity

For each product row, `acquisition_observations.jsonl` contains one product/listing record with no `observation`, followed by one separate price-observation record for each retailer column. For the 25-row workbook the expected total is 25 product/listing records plus 75 price observations, or 100 records. The manifest and quality report expose the counts separately and in total.

Acquisition record IDs include the source ID, worksheet row number, and a truncated SHA-256 fingerprint of ordered original header/value pairs. The original `Product Submission ID` remains in product identity and duplicate IDs remain reported. Exact duplicate rows on different worksheet rows therefore receive distinct record IDs; unchanged input rows receive stable IDs across reruns.

## Provenance and status mapping

Every imported source field identifies `complete_product_catalog`, worksheet `Sheet1`, row number, source column and raw value. Image references carry their source JSON cell locator. Retailer prices point back to their specific source price column; source URLs and date fields have separate field provenance. Product annotations use `pending_review` and `unverified`; acquisition records use `verification_status: candidate`. The workbook license is recorded as unknown because it is not stated in the file.

The second sheet is preserved cell-for-cell in the raw snapshot, including formulas, rather than interpreted as new product records. It is a summary view derived from the product sheet and does not contribute extra candidate identities.
