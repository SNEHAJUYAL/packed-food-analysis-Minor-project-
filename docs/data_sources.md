# Data sources

| Source | Licence and terms | How it is used | Status in this repository |
| --- | --- | --- | --- |
| **Open Food Facts** (world.openfoodfacts.org API v2) | Database: Open Database License (ODbL) 1.0; contents: Database Contents License; images: CC BY-SA. Credit Open Food Facts and share-alike any derived database | Baseline product records for India in the five categories. Crowdsourced reference data, not ground truth. A match never overwrites a listing | **Loaded 12 Oct 2026** from the official CSV export on AWS Open Data (`./run.sh off-export`, streams 1.3 GB and keeps 2,692 India records). 466 records with at least 4 key nutrients are committed as `data/sample/off_india_subset.jsonl` under ODbL. The OFF API route (`./run.sh off`) also works where the API is reachable |
| **Synthetic demo records** (`data/sample/synthetic_products.jsonl`) | Project-generated | 40 records (8 per category) in OFF JSON format with made-up prices, so value for money and price-based alternatives can be shown (OFF has no prices) | **Synthetic, not real products.** Names start with "Sample", brands with "Demo Brand", codes with `SYN-`; flagged `_synthetic` and shown with a "Synthetic demo record" badge. Prices and nutrient values are drawn with a fixed seed from broad ranges (`scripts/make_synthetic_sample.py`). Remove them with `python -m database.ingest --purge-synthetic` once real data is loaded |
| **Prices recorded by hand** (Zepto, Blinkit, shops, pack MRP) | Platform terms not verified (sites unreachable from the build environment); no automated collection | Price per 100 g/ml for value for money, with platform, place and time per observation | Sheet in `data/verified/prices/`, imported with `./run.sh prices`; none recorded yet |
| **Product pages analysed by URL** | Each site's own terms | Fetched on request only, robots.txt honoured, cached locally for the demo. Public pages are not a licence to redistribute; the cache (`data/cache/`) is git-ignored | Runtime only |
| **Uploaded photos, screenshots and saved pages** | Photos: whoever took them. Saved pages: each site's own terms, as for URLs | Read once on upload; the photo is read on the machine with Tesseract OCR, or sent to the Anthropic API only when a key is configured; the image is not stored by the app, only the extracted values and transcript. Saved pages are read as saved, nothing is fetched | Runtime only; not committed. Do not commit label photos without permission |
| **Synthetic test pages** (`tests/fixtures/*.html`) | Project-generated | Unit and API tests; `./run.sh demo-pages` serves them for a local URL demo | Synthetic, written for testing |
| **FSSAI (Advertising and Claims) Regulations, 2018**, compendium dated 14-12-2022 | Government publication | Claim conditions (`data/reference/fssai_claims.csv`, `regulatory_rule` table) | Copied and checked 12 Oct 2026; see [regulatory_rules.md](regulatory_rules.md) |
| **ICMR-NIN Nutrient Requirements for Indians, 2020** | Government publication | Protein RDA (54 g/day) used to turn "% of RDA" claim conditions into grams | Team choice of reference adult; to be confirmed by the guides |
| **UK DH/FSA front-of-pack guidance (2016)** | Open Government Licence | Placeholder "high" (red) bounds for traffic lights until FSSAI publishes final cut-offs | Labelled provisional in `thresholds.csv` |
| **Codex CXG 36-1989** (INS) | Codex Alimentarius | INS codes and functional classes (`ins_codes.csv`, `ingredient_classes.csv`) | Seed list of 66 codes, status `seed_verify` |

## Freshness

Every product has `collected_at` per source; prices are `price_observation` rows with `observed_at`.
The UI shows when a product was last checked. Regulatory rows carry `date_checked`; recheck them before a
demo, because the FSSAI front-of-pack rule is still a draft.

## What is not in the repository

Raw downloads (`data/raw/`), cached pages (`data/cache/`), label photographs and any `.env` file are
git-ignored. No personal data is collected.
