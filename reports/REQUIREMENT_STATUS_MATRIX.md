# Requirement Status Matrix

Status values: COMPLETE, PARTIALLY COMPLETE, IMPLEMENTED BUT UNRELIABLE, NOT IMPLEMENTED,
NOT VERIFIED, or BLOCKED.

| Area / requirement | Status | Evidence | Missing work / priority |
|---|---|---|---|
| URL fetch safety, redirects, robots, size/time limits | COMPLETE | `src/extract/fetch.py`; fetch tests | Continue regression testing; Medium |
| JSON-LD and HTML product extraction | COMPLETE | `src/extract/jsonld.py`, `html_parser.py`; 4 fixture evaluation | More retailer fixtures; High |
| Blinkit live extraction | IMPLEMENTED BUT UNRELIABLE | `reports/retailer_audit.json`; partial name/brand/75 g | Dedicated adapter and identity checks; High |
| Zepto live extraction | IMPLEMENTED BUT UNRELIABLE | Empty permitted response in retailer audit | Saved-page/API partnership fallback; High |
| Swiggy Instamart live extraction | IMPLEMENTED BUT UNRELIABLE | Empty permitted response in retailer audit | Saved-page/API partnership fallback; High |
| Amazon India live extraction | IMPLEMENTED BUT UNRELIABLE | Dynamic “Adding to Cart...” title | Reject dynamic UI text; adapter/saved-page fallback; High |
| BigBasket/JioMart/other retailer live support | NOT VERIFIED | No live audit evidence or adapters found | Obtain permitted fixtures/access; Medium |
| Retailer-specific adapters | NOT IMPLEMENTED | No adapter package or registry | Design common adapter contract; High |
| Exact same-product matching | NOT IMPLEMENTED | Similarity matcher only in `services.py` | Barcode/SKU/variant/quantity identity model; Critical |
| Similarity reference matching | COMPLETE | Open Food Facts matcher and 90-query evaluation | Must remain labelled as reference; Medium |
| Pack/multipack normalisation | PARTIALLY COMPLETE | `normalise/units.py`, product model | Cross-retailer multipack identity; High |
| Unit price calculations | COMPLETE | Database/recommendation/value tests | Live price inputs remain absent; Medium |
| Price history/timestamps/source attribution | PARTIALLY COMPLETE | Price models and source provenance | Retailer observations and availability ingestion; High |
| Open Food Facts API/barcode/reference use | COMPLETE | `normalise/matcher.py`, `services.py`, OFF data | Barcode workflow and stronger identity validation; Medium |
| BuyHatke authorised API | BLOCKED | No public self-service API/docs/pricing verified | Written partnership approval required; Critical |
| Flash authorised API | BLOCKED | No India food-price API verified | Written partnership approval required; Critical |
| Trustified integration | NOT IMPLEMENTED | No provider adapter/schema/tests | Permission and data-access investigation; Low |
| Tesseract OCR | COMPLETE | `src/extract/label_ocr.py`; Tesseract `eng/osd/snum`; tests | Confidence-aware OCR; Medium |
| Image validation/upload | COMPLETE | `src/api/main.py`, `services.py`, `UploadForm.tsx`; upload tests | Real-photo edge cases; Medium |
| Orientation/resize/contrast | PARTIALLY COMPLETE | Pillow EXIF, grayscale, resize, autocontrast | Rotation/deskew/perspective preprocessing; Medium |
| OpenCV preprocessing | NOT IMPLEMENTED | `cv2` absent and no integration | Benchmark before adding; Medium |
| PaddleOCR comparison | NOT IMPLEMENTED | No package/model or benchmark | Only if real-photo Tesseract baseline is inadequate; Medium |
| OCR confidence handling | NOT IMPLEMENTED | Uses `image_to_string` | `image_to_data` and confidence thresholds; Medium |
| Ingredient splitting/normalisation | COMPLETE | `normalise/ingredients.py`; tests | Expand aliases; Low |
| Ingredient dictionary matching | PARTIALLY COMPLETE | 57-label evaluation passes; Soy Lecithin uncertain | Add reviewed compound aliases; Medium |
| Allergen identification | COMPLETE | Reference CSV and ingredient tests | Verify seed dictionary status; Medium |
| Unknown ingredient handling | COMPLETE | Uncertain status and unmatched output | Keep evidence semantics; Low |
| Semantic NLP/food NER | NOT IMPLEMENTED | No spaCy/Transformers integration | Not justified until deterministic baseline fails; Low |
| Nutrition normalisation/scoring | COMPLETE | `normalise/build.py`, `score`, `analyse`; tests | Real-label validation; Medium |
| Marketing claim verification | COMPLETE | `analyse/claims.py`, FSSAI rules, tests | Broader verified claim set; Medium |
| Recommendations/comparison | COMPLETE | `recommend`, API routes, frontend tests | Relevance judgements and identity constraints; Medium |
| PostgreSQL/migrations/ingestion | COMPLETE | `database`, migrations, seed; DB tests | Dedicated identity/retailer tables; High |
| OCR/lab result persistence | NOT IMPLEMENTED | Transcripts are extraction logs; no lab schema | Add only with approved data model; Low |
| Frontend URL/upload/report/compare | COMPLETE | React components, API client, 40 frontend tests | Browser E2E and real external fixtures; Medium |
| Analytics dashboards | NOT IMPLEMENTED | No dedicated dashboard/KPI implementation | Define requirements before building; Low |
| Local runtime | COMPLETE | API health and web HTTP 200 previously verified | Keep documented startup process; Low |
| Docker/deployment configs | PARTIALLY COMPLETE | Docker/Compose/Vercel/Render files exist | Actual deployment and production smoke tests; Medium |
| Automated QA | PARTIALLY COMPLETE | 164 backend + 40 frontend tests | Real-photo and permitted retailer fixture suites; High |

