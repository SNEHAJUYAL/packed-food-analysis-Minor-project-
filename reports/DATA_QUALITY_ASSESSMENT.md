# Data quality assessment

**Profile date:** 16 November 2026  
**Profile type:** read-only file profile plus publisher-reported dataset statistics  
**Live PostgreSQL profile:** unavailable (`DATABASE_URL` was not configured)  
**External raw datasets imported/downloaded:** none

## Existing real project subset: `off_india_subset.jsonl`

The checked-in JSONL contains 466 real OFF-sourced product records. The project README identifies its upstream export date as 12 October 2026 and says it selected India-tagged products in the project's five categories with at least four key nutrients. I profiled the file itself; synthetic demo data is excluded from these figures.

| Measure | Profile result |
|---|---:|
| Product rows | 466 |
| Non-empty / unique barcodes | 466 / 466 |
| Duplicate barcode excess | 0 |
| Product names present / unique after trim+casefold | 466 / 438 |
| Repeated product-name excess | 28 |
| Brand field present / unique raw brand strings | 438 / 233 |
| Unique comma-split brand tokens (simple split) | 230 |
| Category tags present / distinct tags across hierarchy | 466 / 334 |
| Raw quantity present | 331 (71.0%) |
| Quantity parseable with current unit parser | 288 (61.8%) |
| Ingredient text present | 349 (74.9%) |
| At least one nutrition object | 466 (100%) |
| All 10 mapped nutrition fields present | 55 (11.8%) |
| Image field | Not included in this subset's columns |
| Sale price / MRP | Not included |

The 334 category-tag count includes taxonomy hierarchy entries and is **not** 334 comparable leaf categories. Product names repeat 28 times, but no exact duplicate was found on the simple `(raw brands, product_name, quantity)` tuple. That tuple is only a screen, not an identity proof. Barcode uniqueness is within this 466-row file only.

### Key nutrient field coverage

| OFF per-100 g field | Present | Missing |
|---|---:|---:|
| Energy (kcal) | 465 | 1 |
| Total fat | 465 | 1 |
| Saturated fat | 414 | 52 |
| Trans fat | 130 | 336 |
| Carbohydrate | 462 | 4 |
| Total sugars | 460 | 6 |
| Added sugars | 387 | 79 |
| Protein | 461 | 5 |
| Fibre | 234 | 232 |
| Sodium | 446 | 20 |

Only 55 rows have all ten mapped values. The high-level “nutrition object present” figure should not be read as complete nutrition. Quantities are parseable for 288 rather than all 331 rows with quantity text. These fields are crowdsourced declared values and were not checked against physical packs in this profile.

### Category distribution after the project’s current five-category map

| Mapped category | Rows |
|---|---:|
| Beverages | 197 |
| Biscuits and cookies | 99 |
| Namkeen/chips | 80 |
| Breakfast cereals | 55 |
| Instant noodles | 35 |

This distribution describes the project’s filtered subset, not the Indian market. Dairy, spreads, bakery, staples, ready meals, children’s foods, protein snacks, regional products and many other categories are absent or not represented by the current five-category mapping.

## Other local acquisition/evaluation files

- `data/sample/synthetic_products.jsonl`: 40 generated demo records. They are not real products and are excluded from all real-product totals.
- `data/verified/pack_check/pack_check_sheet.csv`: 200 planned rows with system-generated values, but **0** rows have `checked_by`, `checked_on`, `pack_found`, or label pack values. This is a work queue/template, not a manually verified product set.
- `data/verified/prices/price_entry_sheet.csv`: 300 prepared rows, but **0** rows contain `observed_at`, city/pincode, listing name/size, selling price, MRP, stock state or listing URL. No current retailer price observations are recorded. Prefilled platform cells are not observations.
- `data/verified/verified_products_template.csv`: header-only/empty template.
- Reference CSVs include category mapping (10 rows), category keywords (5), ingredient terms (219), ingredient classes (36), INS references (64) and allergen keywords (9). These are dictionaries/rules, not product records.

## Publisher-reported snapshots (not re-profiled locally)

| Source | Reported quality indicators | Interpretation |
|---|---|---|
| PackSense India, 25,209 rows, built 2026-11-03 | README reports 25,209 barcodes, 21,999 names (87.3%), 17,157 brands (68.1%), quantity amount/unit in 8,569 (34%), categories in 12,247 (48.6%), nutrition table in 11,813 (46.9%), fibre in 5,920 (23.5%), allergen tags in 4,780 (19%), trace tags in 588 (2.3%), and 774 rows with an open error flag. It explicitly excludes ingredient text and image/image links. | Publisher computed these from its CSV. It warns rows can be non-food and unverified. Counts are not independent observations from this audit. |
| Shelfpedia India, 6,088 product sheets | Its rule requires valid barcode, name, nutrition per 100 g, and at least 3 of 7 blocks. It says this is 24% of 25,803 India-listed products. | A curated, high-completeness slice, not a population sample. Product source is OFF. |
| Mendeley | 852 product rows and field families are described on its record page. | No exact header/missingness/duplicate profile possible without the actual CSV; publisher descriptions are not a substitute. |
| Ingredient variants DOI | Catalog/project pages describe 2,500+ mappings; associated project material states 2,291 unique variant strings from 896 sampled SKUs. | Different stated counts must be resolved against a versioned artifact. No product/nutrient completeness profile possible from a lexical map. |
| OpenMRP | README advertises a manifest containing row counts and weekly CSV/JSON/SQL dumps. | Manifest could not be fetched here, so no count or completeness claim is made. |
| INDB | Official portal says 1,014 recipes; paper says 1,095 raw foods and 1,014 recipes. | Not a branded packaged-food catalog. Workbook field-level missingness was not profiled. |

## Overlap and conflict results

- No cross-dataset record-level overlap or nutrient/ingredient conflict could be computed because PackSense/Shelfpedia binaries and Mendeley/Kaggle/OpenMRP files were not independently profiled in this environment. Mendeley’s public description does not advertise a barcode, and the Kaggle artifact is an ingredient mapping rather than a SKU catalog.
- PackSense and Shelfpedia explicitly derive from OFF. Treat them as alternate extracts/views of the same lineage until barcode-level overlap is measured; never sum their row counts with OFF.
- Cross-source name similarity is insufficient for merge decisions. The project’s current OFF matcher uses token-set similarity and an 85 cutoff; this can only rank candidates.
- There is no production database count in this report. Only source file counts above are verified locally.

## Data gaps to address before a 1,000-variant pilot

1. The local real subset has no image URLs, no price/MRP, and no manual label verification.
2. Brand and quantity are absent or not parseable for a material share; only 55/466 have all ten mapped nutrient values.
3. Current reference categories cover five broad groups and need a reviewed mapping to the larger food-only taxonomy.
4. Retailer price templates contain no dated observations, location, listing URL or sale price.
5. Pack/formulation changes and duplicate barcodes require explicit review/version history.
6. Production row counts and quality distributions remain unknown until a read-only database profile can connect.
