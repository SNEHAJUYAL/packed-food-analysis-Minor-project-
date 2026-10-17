# API reference

FastAPI serves interactive OpenAPI docs at `http://localhost:8000/docs` (JSON at `/openapi.json`).
All endpoints live under `/api`. Errors share one shape:

```json
{"detail": {"code": "blocked_destination", "message": "Plain-language explanation for the user."}}
```

Error codes: `invalid_url` (422), `blocked_destination` (400: private, loopback or link-local address,
or a non-http(s) scheme), `robots_disallowed` (403), `fetch_failed` (502), `timeout` (504),
`too_large` (413), `unsupported_content` (415), `rate_limited` (429), `not_found` (404),
`validation_error` (422), `database_unavailable` (503).

Every nutrient, price and field is an **Evidence** object:
`{"value": any|null, "label": "declared"|"derived"|"interpreted"|"verified"|"unknown", "source": str|null, "note": str|null}`.
A `null` value with label `unknown` means missing. It is never zero.

## GET /api/health

`{"status": "ok", "database": "ok"|"unavailable", "methodology_version": "0.1.0", "product_count": 42}`

## POST /api/analyze-url

Request: `{"url": "https://...", "category": null | "breakfast_cereals" | ..., "refresh": false}`

Fetches the page (SSRF checks, robots.txt, timeouts, size limit, cache), extracts JSON-LD then HTML
(then the optional LLM fallback), normalises, stores the product in PostgreSQL, scores it against
the stored products of the same category and returns a **ProductAnalysis**.

## POST /api/analyze-upload

Multipart form: `file` (required), `page_url` (optional, where the product was listed), `site` (optional,
e.g. `blinkit.com`), `category` (optional). Returns a **ProductAnalysis** like `analyze-url`. Nothing is
fetched.

* **Pack photo or app screenshot** (JPEG, PNG, WebP, GIF, up to 8 MB). Two readers:
  * **Offline OCR (default, free):** Tesseract reads the text and fixed rules take the ingredient list,
    nutrient rows (the per-100 column), net quantity and price from it (`extraction_method` `label-ocr`).
    Needs the Tesseract program (`brew install tesseract`) and the `pytesseract` package.
  * **Claude (optional, when `ANTHROPIC_API_KEY` is set):** the vision model writes a verbatim transcript,
    then fills the schema; a value is kept only if it appears in that transcript (`label-photo`).

  The text that was read is in the extraction log (step `transcript`) so it can be checked against the pack.
  `source_type` is `photo` and the record id is the image's hash, so the same photo replaces its earlier
  record. Optional form field `name` sets the product name when the image does not show it. With neither
  reader available the endpoint answers 503 `photo_reader_missing`.
* **Saved product page** (`.html`, up to 5 MB, e.g. Ctrl+S / ⌘S in the browser): read as saved with the
  same extractors as a URL. If no `page_url` is given, the page's canonical link or `og:url` is used.
  `source_type` is `saved_page`.

`site` is taken from the form, else from the page address (host without `www.`). It decides which shop
same-site alternatives are drawn from. Errors: 413 `too_large`, 415 `unsupported_type`, 422 `empty_file` or
`validation_error` or `unreadable_image`, 503 `photo_reader_missing`.

## GET /api/products?category=&q=&limit=50

`{"products": [ProductSummary], "total": int}`

**ProductSummary**: `{"product_id": int, "name": str|null, "brand": str|null, "category": str|null,
"pack_size": float|null, "pack_unit": "g"|"ml"|null, "price_per_100": float|null, "overall": int|null,
"grade": "A".."E"|null, "status": "complete"|"partial"|"insufficient_data", "source_type": str,
"is_synthetic": bool, "source_url": str|null, "collected_at": str}`

## GET /api/products/{id}

Returns a **ProductAnalysis**:

```jsonc
{
  "product_id": 12,
  "status": "complete" | "partial" | "insufficient_data",
  "is_synthetic": false,            // true for the labelled synthetic demo records
  "source": {
    "source_type": "url" | "photo" | "saved_page" | "open_food_facts" | "synthetic_sample",
    "source_url": "https://...",
    "site": "blinkit.com" | null,          // shop the listing came from; null for OFF and sample records
    "extraction_method": "json-ld+html",   // which extractors produced data
    "collected_at": "2026-10-12T09:00:00+00:00",
    "last_verified_at": null,
    "source_reliability": "brand_or_retailer_page" | "open_food_facts_crowdsourced" | "synthetic"
  },
  "missing_fields": ["added_sugars", "trans_fat", "price_inr"],
  "conflicts": ["total_sugars: json-ld says 28, html-table says 30"],
  "extraction_log": [{"step": "fetch", "outcome": "ok"|"skipped"|"failed", "detail": "..."}],
  "methodology_version": "0.1.0",
  "report": { ...Report... }
}
```

**Report** (also returned by the CLI with `--json`):

* `product`: the normalised product. Evidence fields `name`, `brand`, `category`, `variant`,
  `pack_size`, `pack_unit`, `price_inr`, `ingredients_raw`; `nutrition_basis` (`per_100g`|`per_100ml`|null);
  `nutrition` (`{nutrient: Evidence}` for energy kcal, protein, carbohydrate, total_sugars,
  added_sugars, total_fat, saturated_fat, trans_fat, fibre g, sodium mg); `nutrition_original`
  (`{nutrient: {"value": "12 g", "basis_text": "per 30 g serving", "source": "html-table"}}`, the
  values as printed before normalisation); `additives_ins`, `allergens`, `claims_raw`, `source_url`,
  `collected_at`, `conflict_flag`, `conflicts`, `warnings`.
* `dimensions.nutrition`: `score` (0–100|null), `basis`, `coverage`, `facts` (`{nutrient: {value, unit, evidence}}`),
  `traffic_lights` (`{nutrient: "green"|"yellow"|"red"}`), `subscores`
  (`{nutrient: {subscore|null, reason|null, benchmark_source}}`), `explanation` [str].
* `dimensions.ingredients`: `score`, `groups` (`{class: [ingredient text]}`), `explanation` [str].
* `dimensions.transparency`: `score`, `missing` [str], `explanation` [str].
* `dimensions.claims`: `score`|null, `explanation` [str], `claims`: list of
  `{"claim_id", "claim" (rule label), "matched_text" (the claim as printed), "status", "facts" [str],
  "reason", "missing_information" [str], "rule", "rule_status", "source_url"}`.
  `status` is one of: `consistent with available evidence`, `requires context`,
  `potential inconsistency for review`, `cannot be verified from available information`.
* `dimensions.value`: `score`|null, `price_per_100`, `category_median`, `peer_count`, `explanation` [str].
* `overall`: `score` (int|null), `grade` ("A".."E"|null), `raw`, `coverage`, `missing` [dimension],
  `rows` [{name, score, weight, effective_weight, contribution}], `notes` [str].
* `ingredients_normalised.items`: ordered list of
  `{"position", "text" (original label text), "name" (normalised), "term", "match"
  ("exact"|"contains"|"fuzzy"|"none"), "match_score", "percent" (declared %, or null),
  "classes" [str], "functional_category", "explanation", "reference_source",
  "status" ("matched"|"fuzzy_match"|"uncertain"), "additives" [{ins, name, functional_class, group}],
  "sub_ingredients" [same shape]}`; plus `additives_ins`, `allergens`, `advisory_allergens`, `unmatched`.
* `fop_warning_simulation`: `{status, triggers, reason}`.
* `disclaimer`: str.

## POST /api/products/compare

Request: `{"product_ids": [1, 2, 3], "priorities": {"nutrition": 0.4, ...} | null}` (2–6 ids, one category).

```jsonc
{
  "category": "breakfast_cereals",
  "basis": "per_100g",
  "methodology_version": "0.1.0",
  "products": [{
    "product_id": 1, "name": "...", "brand": "...", "is_synthetic": false,
    "overall": 64, "grade": "C",
    "dimensions": {"nutrition": 61, "ingredients": 80, "transparency": 90, "claims": null, "value": 55},
    "nutrition": {"energy": {"value": 380, "label": "declared"}, ...},   // per 100 g/ml
    "price_per_100": 48.0,
    "completeness": 0.8,               // share of core fields known
    "ingredient_classes": ["whole_grain", "added_sugar"],
    "claims": [{"matched_text": "High Protein", "status": "..."}],
    "source_url": "...", "site": "blinkit.com" | null, "collected_at": "..."
  }],
  "ingredient_differences": {"shared_classes": ["added_sugar"], "only_in": {"1": ["whole_grain"], "2": ["oil_palm"]}},
  "picks": {
    "best_match": {"product_id": 1, "reason": "..."} | null,
    "lowest_price_per_100": {"product_id": 2, "reason": "..."} | null,
    "best_nutrition": {"product_id": 1, "reason": "..."} | null
  },
  "rationale": ["..."]
}
```

## GET /api/products/{id}/alternatives?preference=balanced&limit=5&scope=same_site

`preference`: `balanced` (methodology weights) | `nutrition` | `price` | `transparency`.
`scope`: `same_site` (default) uses only products analysed from the same shop as this one when that shop
is known and at least one of them qualifies; otherwise all stored products are used and `message` says so.
`all` always uses every stored product. The shop's catalogue is never crawled, so same-site results grow
only as more of its products are analysed.
Candidates are stored products only: same category, same nutrition basis, an overall score, and
not the product itself. They are ranked by the preference with TF-IDF similarity as a tie-break.

```jsonc
{
  "source_product_id": 12,
  "preference": "balanced",
  "methodology_version": "0.1.0",
  "eligible_count": 7,
  "site": "blinkit.com" | null,
  "scope": "same_site" | "all",          // where the alternatives were actually drawn from
  "alternatives": [{
    "product_id": 3, "rank": 1, "name": "...", "brand": "...", "is_synthetic": false,
    "overall": 74, "grade": "B", "nutrition": 70, "transparency": 85, "price_per_100": 39.5,
    "similarity": 0.41, "preference_score": 72.3,
    "matching_attributes": ["same category", "same basis (per 100 g)", "whole grain first"],
    "rationale": "Scores 74 against 58 for this product; lower sugar (12 g vs 28 g per 100 g).",
    "source_url": "...", "collected_at": "..."
  }],
  "picks": {"best_match": {...}|null, "lowest_unit_price": {...}|null, "best_nutrition": {...}|null},
  "message": null | "No stored product in this category scores higher on nutrition."
}
```

## GET /api/reference/categories

`{"categories": [{"id": "breakfast_cereals", "label": "Breakfast cereals", "product_count": 8}]}`

## GET /api/reference/methodology

`{"version", "dimension_weights", "grade_bands", "scoring" (full config), "thresholds" [rows],
"claim_rules" [rows], "category_weights" [rows], "evidence_labels" {label: meaning},
"claim_statuses" {status: meaning}, "data_sources" [{name, licence, use}], "limitations" [str]}`

## Limits

Request bodies over 64 KB are rejected, except `analyze-upload` (`MAX_UPLOAD_BYTES`, default 9 MB, and a
Content-Length is required). `analyze-url` and `analyze-upload` are rate limited per client
(`RATE_LIMIT_PER_MINUTE`, default 10). Fetches time out after `FETCH_TIMEOUT_SECONDS` (default 15)
and stop reading after `FETCH_MAX_BYTES` (default 3 MB).
