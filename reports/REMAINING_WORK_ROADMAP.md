# Remaining Work Roadmap

Estimates are engineering ranges, excluding external approval delays.

## Phase 1 — Protect product identity (Critical)

1. Define canonical product identity: barcode/SKU, brand, canonical name, variant, pack count, unit quantity.
2. Reject or flag ambiguous generic extraction instead of saving it as a confident product.
3. Add identity conflict tests for same-name different-size and multipack products.
4. Add retailer adapter interface and fixture-based adapter tests.

**Estimate:** 32–48 hours. Dependencies: schema/API design. Complexity: High. External permission: no for fixtures,
yes for live retailer access.

## Phase 2 — Build real evaluation evidence (High)

1. Collect and manually transcribe permitted food-label photographs.
2. Include flat, angled, blurred, low-light, rotated, glossy, and multilingual cases.
3. Add CER/WER, field precision/recall/F1, latency, and failure-rate reporting.
4. Run Tesseract baseline, then evaluate OpenCV preprocessing.
5. Evaluate PaddleOCR only if measurable improvement justifies its dependency cost.

**Estimate:** 24–40 hours plus data-collection time. Dependencies: labelled images. Complexity: Medium/High.
External permission: required for image licensing.

## Phase 3 — Improve ingredient resolution (Medium)

1. Review and add compound aliases, including `soy lecithin`.
2. Preserve exact/contains/fuzzy/uncertain evidence.
3. Add OCR-error cases and regression tests.
4. Re-run the existing 57-item evaluation and the six-item audit sample.

**Estimate:** 8–16 hours. Dependencies: domain review. Complexity: Low/Medium.

## Phase 4 — Price and provider integration (Blocked/High)

1. Contact BuyHatke and Flash for written API/partnership terms.
2. If authorised, implement optional provider adapters behind configuration.
3. Normalise prices, quantity, timestamps, availability, and source reliability.
4. Keep retailer extraction and Open Food Facts as fallback.

**Estimate:** 24–60 hours after access approval. Dependencies: contracts, credentials, API documentation.
Complexity: High. Paid access must not be activated without approval.

## Phase 5 — Production readiness (Medium)

1. Add browser E2E tests against local fixtures.
2. Run deployment smoke tests for Docker/Vercel/Render.
3. Add operational metrics and structured extraction failures.
4. Review privacy, data licences, rate limits, and production egress controls.

**Estimate:** 24–40 hours. Dependencies: deployment environments. Complexity: Medium.

## Three completion scenarios

| Scenario | Scope | Estimated effort |
|---|---|---:|
| Minimum academic demonstration | Real labelled photo set, OCR metrics, Soy Lecithin alias, identity warnings, fixture adapters | 60–90 hours |
| Complete minor-project implementation | Above plus retailer fixtures/adapters, price observations, stronger identity model, deployment smoke tests | 120–180 hours |
| Production-oriented implementation | Above plus authorised providers, monitoring, privacy/licence review, robust E2E and failure recovery | 220–350+ hours, excluding access delays |

## Recommended next five actions

1. Freeze a product-identity contract before adding retailer adapters.
2. Build the real manually verified food-label dataset.
3. Add confidence-aware Tesseract output and benchmark it.
4. Add reviewed ingredient aliases and uncertainty tests.
5. Seek written BuyHatke/Flash API terms before any provider implementation.

