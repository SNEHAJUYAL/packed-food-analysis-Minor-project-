# India packaged-food data acquisition roadmap

**Status:** planning recommendation only. No external files were imported and no products are represented as collected. Targets below are quotas, not observed records.

## Recommended source roles

- **Open Food Facts:** broad barcode-led discovery baseline and candidate nutrition/ingredient/image fields. Respect ODbL/DbCL and the separate CC BY-SA image terms. Use bulk exports for scale, retain snapshot/source provenance, and verify on-pack.
- **PackSense India and Shelfpedia:** use as quality-filtered OFF-derived discovery views and completeness comparisons. They are lineage duplicates, not additive supply. PackSense omits ingredient text and images; Shelfpedia omits photos and prices.
- **Manufacturer/package evidence:** primary verification source for identity, ingredients, nutrition, declared net quantity, variant and MRP. Record image/label capture date and source rights.
- **OpenMRP:** conditional identity/pack/MRP cross-check only after obtaining and profiling the actual manifest/dump. MRP is not a current selling price; verify against package evidence.
- **Mendeley packaged-food dataset:** conditional candidate set after direct CSV/header, date, license and row-level quality inspection. Treat its reported prices as historical until dated and revalidated.
- **Ingredient-variant DOI:** optional, versioned alias dictionary; inspect mappings and ambiguity before use. It contributes no product identities.
- **INDB:** nutrient context for foods and recipes, not branded packaged-product label values. Confirm workbook reuse terms before reuse.

## Pilot quota: 1,000 distinct packaged-food variants

The categories are proposed food-only coverage targets. Some can overlap conceptually; assign each product one primary category under a reviewed taxonomy. This is not a market-share estimate.

| Primary category | Target variants |
|---|---:|
| Biscuits and cookies | 100 |
| Chips and savoury snacks | 90 |
| Namkeen | 70 |
| Breakfast cereals and muesli | 60 |
| Oats and millet products | 60 |
| Noodles and pasta | 70 |
| Ready-to-eat / ready-to-cook | 60 |
| Protein bars and snacks | 60 |
| Peanut butter and spreads | 45 |
| Nuts, makhana and trail mixes | 50 |
| Dairy and dairy alternatives | 75 |
| Packaged beverages | 75 |
| Sauces, condiments and dips | 50 |
| Packaged staples and mixes | 60 |
| Children's packaged foods | 45 |
| Bakery and confectionery | 30 |
| **Total** | **1,000** |

## Conditional source contribution plan

These are maximum planned primary-source contributions, deduplicated at variant level, not source row counts. Reallocate any shortfall only to label/manufacturer-verified records; do not lower evidence requirements to reach 1,000.

| Contribution route | Planning ceiling | Role and gate |
|---|---:|---|
| OFF discovery and candidate records | 450 | Select Indian packaged foods across categories; retain OFF ID, snapshot and license lineage. Count only after identity review and required label verification. |
| Direct manufacturer/package verification | 250 | Independent primary evidence route; may also verify OFF leads. Count once per distinct variant. |
| OpenMRP | 150 | Only after actual dump/manifest is available, profiled and barcode/pack evidence passes review. Not independent for fields sourced from OFF. |
| Mendeley | 150 | Only after exact file, schema, collection date, rights and duplicates are checked. Candidate provenance remains Mendeley even if later label-verified. |
| **Total maximum planned routes** | **1,000** | Routes can overlap; deduplicate globally and replace overlap/shortfall with verified primary-label records. |

PackSense and Shelfpedia do not add a separate quota because they derive from OFF. The ingredient mapping dataset and INDB do not contribute SKU variants. Do not use editorial “top products” lists as product records or rankings; they may seed discovery searches only.

## Completeness and verification targets

For each counted pilot variant, target:

- **Required identity:** product name, brand (or explicitly unknown), primary category, exact variant/flavour when stated, declared pack quantity/unit, and barcode where present; preserve explicit missingness.
- **Required provenance:** source record/reference, source license, retrieval/observation date, evidence method and at least one reviewable package/manufacturer reference.
- **Label fields:** ingredients and nutrition per 100 g/ml where declared on the verified pack. Keep absent/illegible/not-declared distinct from numeric zero. Store the original string and normalized unit/value together.
- **Images:** package image only when source and variant association are defensible; record URL or capture provenance and reuse rights. Do not copy images from datasets where excluded or separately licensed.
- **MRP:** capture only when printed on verified packaging or a documented source; retain currency and date. Retailer selling price requires a separate listing URL, retailer, location, observation time, pack size and availability; no current price is assumed from static product datasets.
- **Confidence:** all included rows must pass matching review. Nutrition and ingredient transcription should receive a second check for high-impact fields before downstream consumer guidance.

Expected completeness is a target, not a claim about the candidate sources: identity/pack evidence ≥95%; barcode when printed/present ≥90%; ingredients ≥90%; core energy, protein, carbohydrate, total sugars, total fat and sodium/salt ≥85%; source and evidence date 100%; price/MRP only where captured, no minimum coverage promise. Track coverage by category and source; disclose actual denominators and missingness.

## Staged execution and gates

1. **Access and rights gate:** obtain artifacts through official download/API routes, save version/hash/license/attribution metadata, and inspect headers before parsing. Do not bypass access controls or use paid APIs.
2. **Read-only profiling gate:** measure record counts, exact headers, missingness, duplicate IDs/barcodes, units, date range, malformed values and internal duplicates. Profile each snapshot independently; keep raw files immutable outside production.
3. **Candidate generation:** use OFF barcode/category search and conditional Mendeley/OpenMRP leads. Do not count derivative datasets as independent source contribution.
4. **Identity resolution:** apply `PRODUCT_IDENTITY_MATCHING_PLAN.md`; exact GTIN matches are candidates and incompatible pack/formula evidence is reviewed. No name-only merges.
5. **Label verification:** verify variant, ingredients, nutrition and pack size against exact package/manufacturer evidence. Keep raw label capture and field-level provenance under appropriate rights.
6. **Pilot QA:** sample-check transcription, duplicate decisions, taxonomy, unit conversions, source attribution and category balance. Report included, unresolved, rejected and missing fields separately.
7. **Production decision:** only after separate approval, map the approved export to existing product/source/nutrient/ingredient/price structures and resolve licensing, retention, schema and refresh policy. No import is part of this task.

## Effort estimate and risks

At an estimated 8–12 minutes for package/source review and core-field verification per variant, 1,000 records require roughly **133–200 reviewer-hours**, excluding source access, label image acquisition, second checks, code, and conflict resolution. This is a planning estimate; sparse or conflicting records may take longer. The current local OFF subset already shows gaps in brand, pack-size parsing and complete nutrition, and the project has no manually verified product rows or current price observations in its prepared sheets. Plan for category/source shortfalls rather than filling quotas with inferred data.

Key risks: OFF-derived source overlap; unverified publisher-reported schemas/counts; stale product or price records; barcode conflicts and pack revisions; regional-language label transcription; unclear workbook/media reuse terms; and current project category/schema limits. Keep source provenance and licensing attached through every transformation.
