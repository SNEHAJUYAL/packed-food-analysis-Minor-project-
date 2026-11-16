# Research resources and data source register

Compiled 16 November 2026 from the team's resource list and the project's earlier dataset research.
Original URLs are preserved. Every URL was requested once on 16 November 2026 with a plain HTTP client
(`curl -L`, no login, no scraping); the "Checked" column gives the HTTP status returned. A 403 or 202 from
a large retail site usually means bot protection, not that the address is wrong. Licence and dataset
details were read from each resource's own page where stated.

**Important.**

* Listing a website here is **not** permission to scrape it or collect data from it automatically.
* **Open Food Facts is the only external product source enabled** in the application's source registry
  (`src/acquisition/registry.py`). Nothing else on this list is enabled.
* SerpApi needs a paid API key and a commercial-terms review before any use.
* BuyHatke and Flash integrations must not be assumed available; access, coverage and price have not
  been verified with either company.
* "Discovery link" means a search or listing page that helps find a dataset; it is not a direct download.

Legend for **Integration**: *Integrated* (used by the code), *Reference* (read for design or research),
*Candidate* (could be integrated after review), *Not integrated*.

## 1. Resources supplied for visual search and price comparison

| # | Name | URL | Type | Purpose | Component | Licence | API | Authorization | Integration | Checked / notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | SerpApi Google Lens API | <https://serpapi.com/google-lens-api> | Commercial API docs | Visual product discovery from an image | Future visual search | Commercial terms | Yes; `api_key` required (`engine=google_lens`) | Not authorized; no key | Not integrated | 200. A visual match is not proof of exact variant or pack |
| 2 | GitHub topic: google-lens-api | <https://github.com/topics/google-lens-api> | Discovery link (GitHub topic) | Community implementations | Research | Varies per repository | — | — | Reference | 200 |
| 3 | Web-Database-Analytics (tirthajyoti) | <https://github.com/tirthajyoti/Web-Database-Analytics> | GitHub repository | Web data extraction and analytics patterns | Research | See repository | — | — | Reference | 200 |
| 4 | Amazon-Flipkart Price Comparison Engine (sushantPatrikar) | <https://github.com/sushantPatrikar/Amazon-Flipkart-Price-Comparison-Engine> | GitHub repository | Price-comparison architecture example | Price intelligence research | See repository | — | Its scraping approach is not adopted | Reference | 200 |
| 5 | Price-Comparison-Application (Satya5614) | <https://github.com/Satya5614/Price-Comparison-Application> | GitHub repository | Product and retailer comparison example | Price intelligence research | See repository | — | — | Reference | 200 |

## 2. FMCG and product-category research

| # | Name | URL | Type | Purpose | Component | Licence | API | Authorization | Integration | Checked / notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | India's Top 100 FMCG Grocery Products and Brands (Listberg) | <https://listberg.com/article/indias-top-100-fmcg-grocery-products-and-brands-brands-shaping-everyday-indian-consumption> | Editorial article | Brand and product discovery | Category research | Copyright of publisher | No | Read only | Reference | 200. Editorial, not a market-share dataset |
| 7 | FMCG Products: Complete List and Categories (Rateomatic) | <https://www.rateomatic.in/blog/what-are-fmcg-products-complete-list-and-categories> | Editorial article | Category discovery | Category research | Copyright of publisher | No | Read only | Reference | 200. Editorial |

## 3. Food product datasets and APIs

| # | Name | URL | Type | Purpose | Component | Licence | API | Authorization | Integration | Checked / notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | Open Food Facts | <https://world.openfoodfacts.org/> | Open database | Product names, barcodes, ingredients, nutrition | Seed data, URL analysis, candidate preview | ODbL 1.0 (database), DbCL (contents), CC BY-SA (images) | Yes | **Enabled** in registry (`world.openfoodfacts.org`, robots.txt respected, ≥ 1 s between requests) | **Integrated** | 200. Crowdsourced reference data, not ground truth |
| 9 | Open Food Facts API documentation | <https://openfoodfacts.github.io/openfoodfacts-server/api/> | API docs | Product retrieval | `scripts/fetch_off_india.py` | — | Yes | As above | Integrated | 200 |
| 10 | Open Food Facts data downloads | <https://world.openfoodfacts.org/data> | Bulk download page | Bulk export | `./run.sh off-export` (CSV export on AWS Open Data) | ODbL | — | As above | Integrated | 200 |
| 11 | PackSense India (Hugging Face) | <https://huggingface.co/datasets/PackSense/packsense-india> | Dataset | Indian packaged-food catalogue | Candidate extra source | ODbL (dataset card) | HF download | Not reviewed for integration | Candidate | 200. Release 2026-11-03: 25,209 products derived from Open Food Facts; no ingredient text, no images; values not checked against packs |
| 12 | PackSense CSV | <https://huggingface.co/datasets/PackSense/packsense-india/blob/main/india_products.csv> | Dataset file (viewer page) | Inspect / download the CSV | Candidate | ODbL | — | — | Candidate | 200. This is the file's viewer page; the raw file is served under `/resolve/main/` |
| 13 | PackSense README | <https://huggingface.co/datasets/PackSense/packsense-india/blob/main/README.md> | Dataset documentation | Fields, limitations, licence | Candidate | ODbL | — | — | Reference | 200 |
| 14 | Shelfpedia India | <https://shelfpedia.com/en-in/> | Product catalogue website | Product records, ingredients, nutrition, additives, categories | Research | Mostly derived from OFF (ODbL) | Not confirmed | Not authorized for collection | Reference | 200 |
| 15 | Shelfpedia sources and licences | <https://shelfpedia.com/en-in/sources/> | Source documentation | Data lineage | Research | Lists OFF (ODbL/DbCL, photos CC BY-SA), GS1 prefixes, WFP prices (CC BY-IGO), Open Prices (ODbL) and recall feeds | — | — | Reference | 200 |
| 16 | Indian Packaged Foods Nutritional Composition Dataset (2026), Mendeley Data | <https://data.mendeley.com/datasets/rhswn9z9xr> | Dataset | Indian packaged-food nutrition | Candidate extra source / evaluation | **CC BY 4.0** | Download | Not yet reviewed for integration | Candidate | 200 (redirects to version 1). DOI 10.17632/rhswn9z9xr.1, published 23 June 2026, 852 products with ingredients, serving sizes, nutrition and price information compiled from labels and manufacturer sites |
| 17 | OpenMRP | <https://github.com/openmrp-in/openmrp> | GitHub repository | Indian product registry: barcode, name, brand, pack size, MRP | Future barcode/MRP lookup | Data ODbL-1.0; code Apache-2.0 | Public API (per README) | Not authorized yet | Candidate | 200 |
| 18 | OpenMRP downloads | <https://openmrp.in/downloads> | Dataset downloads | Database exports | Candidate | ODbL | — | — | Candidate | 200 |
| 19 | Indian Nutrient Databank (INDB), Anuvaad | <https://www.anuvaad.org.in/indian-nutrient-databank/> | Dataset portal | Indian food composition (recipes) | Research reference (not packaged foods) | Open access per portal; check terms before reuse | Excel download | — | Reference | 200. 1,014 common recipes, per 100 g and per serving, based on IFCT 2017 and other tables |
| — | IFID ingredient-label variants dataset | **Original DOI / download link requires confirmation** | Research lead | Ingredient name variants and canonical mappings | Future ingredient normalisation | Unknown | — | — | Not integrated | The exact original link could not be recovered; no URL is asserted. Record the DOI here once found |

## 4. Food quality and regulatory references

| # | Name | URL | Type | Purpose | Component | Licence | API | Authorization | Integration | Checked / notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 20 | Trustified | <https://www.trustified.in/> | Independent lab-testing website | Packaged-food test reports | Future lab evidence | Copyright | No | Read only | Reference | 200. Reports are batch-specific evidence, not universal ratings |
| 21 | FSSAI | <https://fssai.gov.in/> | Regulator | Indian food regulation | Claim rules, labelling | Government publication | No | Read only | **Integrated** as rule source (`fssai_claims.csv`) | 200 |
| 22 | FSSAI food testing | <https://fssai.gov.in/food-testing/> | Regulator page | Testing parameters, laboratories | Research | Government | No | — | Reference | 200 |
| 23 | FSSAI labelling and display amendments | <https://fssai.gov.in/food-law/regulations/amendments/labelling-display> | Regulatory documents | Labelling and claims | Allergens, labelling rules | Government | No | — | Reference | 200 |

The claim conditions themselves come from the FSSAI (Advertising and Claims) Regulations 2018 compendium
dated 14-12-2022, recorded with clause numbers in `data/reference/fssai_claims.csv` and
[regulatory_rules.md](regulatory_rules.md). Other rule sources used by the code: ICMR-NIN Nutrient
Requirements 2020 (protein RDA 54 g), UK DH/FSA front-of-pack guidance 2016 (placeholder red bounds,
Open Government Licence), Codex CXG 36-1989 (INS codes).

## 5. Visual product discovery

Same resources as #1 and #2 above (SerpApi Google Lens API and the GitHub topic), listed again in the
team's list under this heading. Status unchanged: not integrated, API key and commercial review required.

## 6. Price comparison and market intelligence

| # | Name | URL | Type | Purpose | Component | Licence | API | Authorization | Integration | Checked / notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 26 | BuyHatke Pricing Intelligence | <https://pricing-intelligence.buyhatke.com/> | Commercial data platform | Price feeds, history, catalogue metadata | Future price intelligence | Commercial | Yes (paid plans; the page advertises Price Feeds, Historical Query, Catalog and Alerts APIs with bearer-token auth) | Not authorized; no account | Not integrated | 200. Access, grocery coverage and cost must be confirmed |
| 27 | BuyHatke | <https://buyhatke.com/> | Consumer price-comparison site | Reference | Research | Copyright | — | Not authorized | Reference | 200 |
| 28 | Flash (flash.co) | <https://www.flash.co/> | Shopping research site | Reference | Research | Copyright | Unknown | Not authorized | Reference | 403 to an automated request (likely bot protection) |
| 29 | Flash (flash.tech) | <https://flash.tech/> | Product insights platform | Reference | Research | Copyright | Unknown | Not authorized | Reference | 200 |

Repositories #3–#5 also belong to this group.

## 7. Academic research (IEEE Xplore)

Titles were read from IEEE Xplore where the page allowed it. Three pages refused automated reading
(HTTP 418 to a fetch service), so their titles are left for the team to confirm; their URLs answered.

| # | URL | Title (as read) | Venue / year (as read) | Relevance |
| --- | --- | --- | --- | --- |
| 30 | <https://ieeexplore.ieee.org/document/8765311> | A Food Recommender System Considering Nutritional Information and User Preferences | IEEE Access, vol. 7, 2019, pp. 96695–96711 (Yera Toledo, Alzahrani, Martínez); open access | Nutrition-aware recommendation |
| 31 | <https://ieeexplore.ieee.org/abstract/document/10426098/> | Title to be confirmed (the team's list names a paper on food recommendation using K-means clustering and random forest; not confirmed against the page) | — | Recommendation |
| 32 | <https://ieeexplore.ieee.org/abstract/document/10923764> | Nutritional Insight: Using OCR to Decode Food Labels for Better Health | IEEE conference publication | OCR of food labels |
| 33 | <https://ieeexplore.ieee.org/abstract/document/10823177> | Automating Nutritional Claim Verification: The Role of OCR and Machine Learning in Enhancing Food Label Transparency | IEEE conference publication | Claim verification |
| 34 | <https://ieeexplore.ieee.org/document/9441889> | Title to be confirmed | — | — |
| 35 | <https://ieeexplore.ieee.org/document/10673543/> | Title to be confirmed | — | — |
| 36 | <https://ieeexplore.ieee.org/document/10394513/> | CNN-Based Visible Ingredients Recognition in a Food Image Using Decision Making Schemes | IEEE SMC 2023 (Fu, Dai, Zhu) | Image-based ingredient recognition |
| 37 | <https://ieeexplore.ieee.org/document/9846887/> | Ingredient-Guided Region Discovery and Relationship Modeling for Food Category-Ingredient Prediction | IEEE journal | Food image category/ingredient prediction |

All eight URLs answered HTTP 200 or 202. Full texts are behind IEEE access except #30 (open access).

## 8. Retailer reference websites

| # | Name | URL | Checked | Authorization | Integration |
| --- | --- | --- | --- | --- | --- |
| 38 | Blinkit | <https://blinkit.com/> | 403 (bot protection) | **Not authorized**; no public price API; automated collection treated as not permitted | Shop name only (`site` for same-shop alternatives); prices by hand |
| 39 | Zepto | <https://www.zeptonow.com/> | 202 | Not authorized | As Blinkit |
| 40 | Swiggy Instamart | <https://www.swiggy.com/instamart> | 202 | Not authorized | Shop option in the upload form |
| 41 | BigBasket | <https://www.bigbasket.com/> | 403 | Disabled placeholder in the registry, no evidence | Shop option in the upload form |
| 42 | Amazon India | <https://www.amazon.in/> | 200 | Not authorized | Not integrated |
| 43 | JioMart | <https://www.jiomart.com/> | 200 | Not authorized | Not integrated |

The team also used an Apify product-extraction run during earlier research. Its link was not retained in
the material supplied for this register, so it is not listed; Apify output from retailer sites would face
the same authorization limits.

## 9. Project repository and local datasets

| # | Resource | Location | Contents | Status |
| --- | --- | --- | --- | --- |
| 44 | Project repository | <https://github.com/SNEHAJUYAL/packed-food-analysis-Minor-project-> | Source code and docs | 200 |
| — | OFF India subset | `data/sample/off_india_subset.jsonl` | 466 OFF records | Real, ODbL |
| — | Synthetic demo products | `data/sample/synthetic_products.jsonl` | 40 records, made-up prices | Synthetic |
| — | Pack-check template | `data/verified/pack_check/pack_check_sheet.csv` | 200 rows to fill from packs | Unfilled |
| — | Price-entry template | `data/verified/prices/price_entry_sheet.csv` | 300 rows | Unfilled |
| — | Verified product template | `data/verified/verified_products_template.csv` | Header only | Template |
| — | `misleading_indian_food_products.xlsx` | `~/Downloads` (not in repo) | 22 candidate products and claim observations | Candidate, unverified |
| — | `indian_packaged_food_annotation_records.xlsx` | `~/Downloads` (not in repo) | 25 candidate records | Candidate, unverified |
| — | `master_verified_food_corpus.xlsx` | `~/Downloads` (not in repo) | 38 candidate records | Candidate, unverified despite its name |
| — | `Complete_Product_Catalog_With_JSON_Photos.xlsx` | not in repo | 25 products, image references, 75 indicative prices | Candidate, unverified |

Workbook names do not establish verification status. All candidate workbooks stay separate from
verified evaluation and training data.

## 10. Review checklist

- [x] Open Food Facts (integrated)
- [ ] PackSense India (licence ODbL confirmed; integration review pending)
- [ ] Shelfpedia India
- [ ] Mendeley Indian Packaged Foods (CC BY 4.0 confirmed; review pending)
- [ ] OpenMRP (ODbL confirmed; review pending)
- [ ] INDB / Anuvaad (recipes, not packaged products)
- [ ] IFID ingredient variants (original link to be found)
- [ ] SerpApi Google Lens (key and terms)
- [ ] BuyHatke, Flash (access and terms)
- [ ] Confirm titles of IEEE 10426098, 9441889, 10673543
