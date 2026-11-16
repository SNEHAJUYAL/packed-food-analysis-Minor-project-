# Project Completion Audit

**Audit date:** 16 November 2026  
**Mode:** Audit-only. No production code, dependencies, configuration, schema, database, or deployment was changed.

## Executive conclusion

The repository is a functional academic prototype with a working local URL/upload analysis path, PostgreSQL
storage, deterministic scoring, recommendations, frontend screens, deployment configuration, and substantial
tests. It is not yet a reliable multi-retailer product-intelligence platform.

The most important gap is product identity and live retailer extraction. The generic extractor works on the
four committed synthetic fixtures, but live Blinkit is only partial and Zepto, Swiggy Instamart, and Amazon
are unreliable under the permitted public-fetch test. No retailer-specific adapters, exact cross-retailer
identity resolution, or authorised price-intelligence provider integration exists.

## Evidence reviewed

- Backend: `src/api`, `src/extract`, `src/normalise`, `src/analyse`, `src/score`, `src/recommend`,
  `src/database`, `src/evaluation`, migrations, tests, and reference CSVs.
- Frontend: `web/src/app`, components, API client, tests, package configuration.
- Data: 466 Open Food Facts India records plus synthetic products, reference dictionaries, evaluation labels.
- Runtime checks: backend tests, frontend tests, current evaluation runner, live permitted retailer audit.

## Architecture findings

The pipeline is connected as:

`URL/upload -> fetch or local read -> JSON-LD/HTML/OCR/optional Claude -> normalise -> database -> score -> report`

The database stores products, sources, extraction logs, analyses, prices, and provenance. The application
does not currently persist a dedicated OCR-result table, laboratory-verification table, retailer-catalogue
table, or cross-retailer product-identity table.

## Weighted completion

The estimate follows the requested weights. Credit is conservative: unreliable live functionality receives
only demonstrated reliable credit; unverified functionality receives no assumed credit.

| Category | Weight | Earned | Basis |
|---|---:|---:|---|
| Core product extraction | 15% | 7.5% | Synthetic fixtures work; dynamic retailer coverage is unreliable |
| OCR/computer vision | 12% | 5.4% | Tesseract/upload work; no real-photo set or OpenCV/Paddle benchmark |
| NLP/ingredient intelligence | 10% | 8.0% | Deterministic parser and dictionary tests pass; aliases remain incomplete |
| Nutrition/scoring | 12% | 10.0% | Normalisation, scoring, claims, and explainability are implemented |
| Matching/price intelligence | 12% | 5.0% | Similarity and unit-price logic exist; exact variant identity and live prices do not |
| External data integrations | 8% | 3.0% | Open Food Facts works as reference; BuyHatke/Flash/Trustified not integrated |
| Recommendations | 8% | 6.0% | Deterministic alternatives, comparisons, and explanations exist |
| Database/data engineering | 8% | 6.0% | PostgreSQL, migrations, ingestion, provenance, and seed data work |
| Frontend/UX | 5% | 4.5% | Main flows, loading/errors, report/compare/upload screens work |
| Testing/QA | 5% | 4.0% | 164 backend and 40 frontend tests; no real-retailer or real-photo suite |
| Deployment/security | 5% | 3.0% | Local/Docker/Vercel/Render configuration and SSRF controls exist; deployment not verified |
| **Total** | **100%** | **62.4%** | **Conservative functional implementation estimate** |

**Estimated remaining work: 37.6%.** This is implementation completeness, not production readiness.

## Reliability assessment

| Dimension | Assessment |
|---|---|
| Correctness | Strong for deterministic fixtures and rule-based scoring; weak for dynamic retailer identity |
| Data quality | Provenance and missing-value handling are good; prices are absent from OFF sample |
| Reliability | Local workflow reliable; external retailer extraction unreliable |
| Testing | Broad unit/integration coverage; insufficient real-world evaluation |
| Maintainability | Modular package structure and clear schemas; provider/identity abstractions are missing |
| Security | SSRF checks, robots handling, size limits, rate limiting, and secret environment variables exist |
| Deployment readiness | Configured but not production-verified |

## Priority risks

1. Wrong product/variant can be presented when generic page text or similarity matching is used.
2. Retailer prices and availability are not reliably extracted.
3. OCR quality on real photographs is unknown.
4. Open Food Facts similarity is reference matching, not identity proof.
5. External provider access is not authorised or available.

