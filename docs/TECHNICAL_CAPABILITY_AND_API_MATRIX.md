# Technical Capability, Data and API Matrix

## 1. System capability matrix

| Area | Implemented | Technology / location | Current evidence | Limitation |
|---|---|---|---|---|
| Product URL analysis | Yes | FastAPI, JSON-LD, HTML, safe fetch | API and tests pass | Dynamic retailer pages are unreliable |
| Product search | Yes | PostgreSQL search + Open Food Facts search | Maggi search returns stored and online matches | Online data is crowdsourced |
| OCR | Yes | Tesseract + pytesseract + Pillow | CER 0.0081 on rendered fixture | Real-photo accuracy not measured |
| Vision fallback | Optional | Anthropic Claude | Code path exists | Disabled without key; not evaluated |
| Ingredient parsing | Yes | Deterministic parser, dictionaries, RapidFuzz | Six-item F1 1.0 | Compound aliases remain incomplete |
| Allergen identification | Yes | Allergen reference dictionary | Soy and gluten detected in sample | Not a clinical allergen guarantee |
| Nutrition normalization | Yes | Unit conversion and per-100 g/ml rules | Covered by tests | Source data may be incomplete |
| Nutrition scoring | Yes | Weighted rules in `config/scoring.json` | Deterministic and explainable | Not clinically validated |
| Claim analysis | Yes | Regex + FSSAI rule table | 22 hand-worked cases pass | Not legal certification |
| Product similarity | Yes | TF-IDF + cosine similarity | 90-query matching rate 0.9889 | Similarity is not identity proof |
| Alternatives | Yes | Eligibility and preference ranking | Nutrition/price/transparency views | Recommendation relevance not measured |
| Price observations | Yes | PostgreSQL dated price records | Unit price and history API | No live retailer price adapter |
| Database | Yes | PostgreSQL + SQLAlchemy + Alembic | Runtime database healthy | Production deployment not verified |
| Frontend | Yes | Next.js, React, TypeScript, Tailwind | 50 frontend tests pass | Browser E2E suite not yet added |

## 2. Data and analytics matrix

| Analytics output | Data used | Status | Honest interpretation |
|---|---|---|---|
| Category distribution | Stored product category | Implemented | Describes this installation's catalogue |
| Grade distribution | Deterministic product scores | Implemented | Distribution of prototype scores |
| Missing-data coverage | Product status and missing fields | Implemented | Shows source completeness |
| Price per 100 g/ml | Dated price + pack size | Implemented | Only where both values exist |
| Product comparison | Same category and nutrition basis | Implemented | Compares available stored evidence |
| Alternative ranking | Score, nutrition, similarity, price, transparency | Implemented | Explainable candidate suggestions |
| Sugar/sodium catalogue distribution | Product-level nutrition aggregation | Not available | Requires aggregate endpoint and consistent data |
| Ingredient/additive/allergen frequency | Product-level ingredient analysis | Not available | Requires catalogue aggregation |
| Recommendation Precision@3/NDCG@5 | Human relevance labels | Not measured | Evaluation set must be collected |

## 3. AI/ML status matrix

| Component | AI/ML status | Trained in project? | Purpose |
|---|---|---:|---|
| Tesseract | Pretrained OCR engine | No | Read label text |
| Claude Vision | Optional hosted pretrained model | No | Transcribe difficult label images |
| Claude text fallback | Optional hosted pretrained model | No | Locate fields on unstructured pages |
| RapidFuzz | Fuzzy string matching | No | Ingredient and reference matching |
| TF-IDF + kNN | Unsupervised information retrieval | No | Product similarity and tie-breaking |
| Ingredient dictionaries | Rule-based NLP | No | Ingredient classes, additives, allergens |
| Nutrition scoring | Rule-based analytics | No | Explainable nutrition indicators |
| Claim verification | Rule-based NLP | No | Compare claims with configured rules |
| Supervised classifier | Not implemented | No | Requires verified labelled dataset |
| Food-specific transformer | Not implemented | No | Not justified until baseline is measured |

## 4. API and key matrix

| Service / key | Required? | Used for | Current status | Where configured | Cost / risk |
|---|---:|---|---|---|---|
| `DATABASE_URL` | Yes for persistence | PostgreSQL connection | Configured locally | `.env` only | Must never be committed |
| `ANTHROPIC_API_KEY` | No | Optional Claude page/photo fallback | Empty locally; deterministic path works | `.env` only | Paid hosted inference; do not expose in frontend |
| Tesseract binary | Yes for offline photo OCR | Local OCR | Installed locally | System package | Free/open source; unavailable by default on Vercel |
| Open Food Facts API | No key | Product search/import/reference | Working with source attribution | Backend only | Rate limits and crowdsourced quality |
| BuyHatke API | No | Price intelligence | Not integrated | No key available | Requires authorised commercial agreement |
| Flash API | No | Price intelligence | No India food API verified | No key available | Do not use unrelated or internal APIs |
| Retailer APIs | No | Live prices and availability | Not integrated | No keys | Requires written authorization |
| `NEXT_PUBLIC_API_BASE_URL` | No | Frontend API routing override | Usually empty | `web/.env` | Never put secrets in `NEXT_PUBLIC_*` |

## 5. API surface

| Endpoint | Function |
|---|---|
| `GET /api/health` | Service and database health |
| `POST /api/analyze-url` | Fetch, extract, persist and score a product |
| `POST /api/product-candidates/from-url` | Authorized preview without persistence |
| `POST /api/analyze-upload` | Analyze photo, screenshot, or saved HTML |
| `POST /api/analyze-manual` | Analyze user-entered product data |
| `GET /api/search` | Search stored products and Open Food Facts |
| `POST /api/products/import-off` | Import one Open Food Facts barcode |
| `GET /api/products/{id}` | Product report |
| `POST /api/products/compare` | Compare stored products |
| `GET /api/products/{id}/alternatives` | Explainable alternatives |
| `GET/POST /api/products/{id}/prices` | Read or add dated price observations |
| `GET /api/reference/categories` | Category list |
| `GET /api/reference/methodology` | Scoring and methodology metadata |

## 6. Security and governance

- API keys stay server-side in environment variables.
- The frontend must never receive `ANTHROPIC_API_KEY` or database credentials.
- URL fetches apply scheme, SSRF, DNS, redirect, robots, timeout, size, and rate controls.
- Unknown acquisition sources fail closed in the candidate workflow.
- Retailer access restrictions are not bypassed.
- Candidate workbook prices are isolated and labelled unverified.
