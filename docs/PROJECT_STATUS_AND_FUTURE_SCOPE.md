# Project status and future scope

Status as checked on 16 November 2026. Classification key:

1. **Implemented and tested**: code exists and automated tests pass.
2. **Implemented, runtime unverified**: code and tests exist, but the real-world path was not exercised
   (for example on real photos, live retailers or the hosted deployment).
3. **Partially implemented**.
4. **Planned**: design or template only.
5. **Blocked**: cannot proceed without something outside the team's control.

## 1. Feature status

| Feature | Status | Evidence / gap |
| --- | --- | --- |
| Source registry, fail-closed policy | 1 | `test_acquisition_foundation.py`, `test_product_url_*`; live 403 for Blinkit preview |
| Product URL candidate preview (OFF) | 1 (synthetic fixtures); live OFF fetch not re-run in this check | 20 candidate tests; UI panel tested |
| Saved URL analysis (OFF and user-submitted pages) | 1 | `test_api_db.py`; unregistered hosts fetched once as user-submitted pages (confirmed intended, 16 Nov) |
| Saved HTML upload (local only) | 1 | `test_upload.py` |
| Packaging photo OCR | 2 | Tesseract parsing tested; accuracy on camera photos not measured |
| Claude vision / text fallback | 2 | Grounding rule tested with mocks; never run with a key in recorded tests |
| User corrections on upload | 1 | `test_upload.py`, `UploadForm.test.tsx` |
| Manual entry | 1 | `test_api_db.py`, frontend tests |
| Unit and nutrition normalisation | 1 | `test_units.py`, `test_extraction.py` |
| Ingredient intelligence | 1 | `test_ingredients.py`; 53/53 on 57 team phrases; dictionary is a seed list (3) |
| Nutrition score | 1 | `test_scoring.py`; energy benchmark missing, red bounds placeholder |
| Ingredient, transparency, claim, value scores | 1 | tests + evaluation; claim rules 22/22 |
| Combined score and grade | 1 | worked example reproduced |
| FSSAI front-of-pack warning simulation | 5 | thresholds not published (`fop_warning.csv` TODO) |
| Comparison | 1 | `test_api_db.py`, `CompareAndMethodology.test.tsx` |
| Alternatives (rule-based + TF-IDF) | 1 for logic; relevance 4 | relevance judgements not collected |
| Same-shop alternatives | 3 | works only for shops whose products were analysed; catalogue never crawled |
| Price observations and unit price | 1 | `test_prices.py`; synthetic prices only in the DB |
| Real retailer prices | 4 | price sheet (300 rows) empty; manual recording planned |
| Automated retailer extraction (Blinkit, Zepto, Instamart, BigBasket, Amazon, JioMart) | 5 | no authorization; scraping not permitted |
| BuyHatke / Flash / SerpApi integration | 4 / 5 | not integrated; commercial access and API keys required |
| Annotation schema, validator, grouped splits | 1 | `test_annotation_tools.py` |
| Workbook candidate consolidation (85) and catalogue import (25 + 75) | 1 | tests; data unverified |
| Verified evaluation set (100–200 real products) | 4 | pack-check sheet of 150 + 50 unfilled |
| Trained ML model | 4 | none exists; needs a verified dataset first |
| Barcode scanning | 4 | deferred |
| Web UI (landing, report, products, compare, alternatives, methodology) | 1 | 47 Vitest tests, TypeScript, ESLint; the shell/branding was being edited by another session during this check |
| Database and migrations | 1 | `0002 (head)` on the local database |
| Local runtime (API + web + PostgreSQL) | 1 | running and answering on 16 Nov |
| Docker Compose | 2 | config exists; not run here |
| Hosted Vercel + Neon deployment | 2 | configured in earlier commits; not re-verified |
| Expert ranking evaluation | 4 | not collected |

## 2. Outstanding blockers

1. **No verified real-product set.** Fill the pack-check sheet from real packs; until then no accuracy
   figures can be claimed and no model should be trained.
2. **No real prices.** Value for money on real products stays unknown until prices are recorded by hand.
3. **Regulatory placeholders.** FSSAI "high" cut-offs and front-of-pack warning thresholds are not final;
   energy has no benchmark; INS and allergen lists need verification.
4. **Retailer authorization.** No retailer has given permission for automated access.
5. **Protein RDA choice (54 g/day)** and code licence (MIT or AGPL-3.0) need the guides' decision.

## 3. Future scope

* Fill the pack-check and price sheets; run `python -m evaluation.pack_check` and report real accuracy.
* Review the 85 + 25 annotation candidates, then create family-grouped splits.
* Only then, train and evaluate supervised components (for example a category classifier replacing the
  keyword rules, or an ingredient-class model), each with a model card.
* Collect relevance judgements and run Precision@3 / NDCG@5 for alternatives.
* Barcode lookup through Open Food Facts or OpenMRP (both ODbL), with attribution and share-alike.
* Evaluate PackSense India, Shelfpedia and the Mendeley 852-product dataset as additional sources after a
  licence review (see the resource register).
* Personalisation (allergen and dietary filters), basket optimisation, lab evidence (e.g. Trustified
  batch reports, treated as batch-specific).
* Calibrate weights with experts; replace placeholder thresholds when FSSAI publishes final rules.

## 4. Production readiness

The project is a working prototype for academic evaluation. It is **not production-ready**: no verified
dataset, no measured photo accuracy, placeholder thresholds, a single-process rate limiter, and a DNS
check that does not fully exclude DNS rebinding without an egress firewall.
