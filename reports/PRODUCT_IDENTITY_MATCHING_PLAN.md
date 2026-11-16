# Product identity and matching plan

**Scope:** proposed matching rules for the 1,000-variant research pilot. No records were merged or modified.

## Identity model

Treat the physical, labeled product variant as the canonical product identity. A retailer listing is a time- and location-specific offer for that product; a brand family is a parent grouping; and each source record is an assertion about identity or a field. Keep those concepts distinct. Preserve source IDs and raw values even after normalization.

The existing project has an OFF barcode-based key for OFF imports and URL-hash IDs for URL imports, but no general cross-source canonical ID or field-assertion history. Its fuzzy matcher is candidate generation only.

## Candidate matching sequence

1. **Normalize identifiers without destroying originals.** Preserve GTIN/barcode text including leading zeroes; normalize whitespace and permitted separators for comparison. Validate GTIN length/check digit. Keep invalid or absent codes as source-scoped IDs, never invent a barcode.
2. **Exact GTIN candidate.** Same valid GTIN is a strong candidate, not unconditional proof: compare brand, variant/flavour, net quantity, multipack count and package evidence. Flag a mismatch for review; do not silently overwrite. A recycled, mistyped or package-changed code is possible.
3. **Source crosswalk.** Exact manufacturer SKU, retailer seller SKU or source product ID is useful only within its documented namespace. Link it through a crosswalk to the canonical variant after confirming package identity.
4. **No-code evidence match.** Require agreement across normalized brand, distinctive product name, variant/flavour, total net quantity/unit and package/label evidence. Ingredient/nutrition agreement can corroborate, but reformulation differences may signal distinct dated variants.
5. **Fuzzy search.** Use normalized brand+name similarity to rank candidates for human review only. Never auto-merge on name similarity, brand alone, shared ingredients, image similarity or category.

## Decision tiers

| Tier | Evidence | Action |
|---|---|---|
| A: verified same variant | Valid exact GTIN plus compatible name, brand and pack details; or primary-label/manufacturer evidence establishes same variant | Link source records to one variant; preserve each field assertion and source |
| B: likely, review required | Exact GTIN but one or more pack/brand conflicts; or strong no-code agreement with label evidence | Hold as candidate; resolve against current package/manufacturer evidence |
| C: search candidate | Similar name/brand, category, image, or incomplete pack data | Keep separate; human review may request more evidence |
| D: distinct | Different GTIN with variant/size evidence, clear formula/flavour difference, or incompatible package | Keep separate; optionally connect to same family |

## Variant and package rules

- Different flavour, recipe/formulation, dietary claim, preparation form or other consumer-relevant label variant is a distinct variant, even if the family name is shared.
- Different net quantity or multipack configuration is a distinct sellable pack/SKU. Store total quantity consistently in g/ml where possible, while retaining the stated quantity, unit, per-unit count and pack count as raw evidence.
- Never convert serving size into pack size. Never interpret MRP as sale price.
- A formula or label change with the same barcode should keep dated assertions; do not erase older evidence.
- Retailer offers for a matching variant remain separate observations keyed by seller/listing, place, observed time, price and stock state.

## Conflict handling and provenance

Store source-scoped values with source URL/ID, field name, raw value, normalized value/unit, observed or published timestamp, retrieval timestamp, method, license and confidence. Resolve conflicts per field rather than choosing one “best” source for the entire record. Prefer current package photographs/manufacturer materials for identity, ingredients and declared nutrition; use OFF or derivative snapshots for discovery and corroboration. Keep historical values with their dates. Where claims disagree and no primary evidence resolves them, retain both and mark the canonical field unresolved.

For dataset overlap, first compare exact normalized valid GTINs. Then report exact matches, GTIN conflicts (same code but incompatible pack/name), and unmatched rows separately. Compare name/brand/pack candidates only after exact-code matching; publish thresholds and manual-review outcomes. PackSense and Shelfpedia are OFF-derived, so their agreement with OFF is not independent corroboration. Never count OFF, PackSense and Shelfpedia overlap as separate unique products.

## Pilot review log

For every proposed link, capture: source record IDs; canonical variant ID; match tier; barcode validation; brand/name/variant and quantity agreement; conflicting fields; package evidence; reviewer/date; and final decision. Do not count unresolved candidates toward the target of 1,000 distinct variants. Keep a reversible crosswalk rather than destructive deduplication.
