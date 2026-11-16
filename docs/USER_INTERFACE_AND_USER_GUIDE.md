# User interface and user guide

The web app is in `web/` (Next.js 16 App Router, React 19, TypeScript, Tailwind 4, Recharts 3). The
browser calls `/api/*` on its own origin and Next.js forwards it to the FastAPI server
(`API_BASE_URL`). All pages below returned HTTP 200 on the local app (`localhost:3000`) on
16 November 2026. Screenshots from an earlier build are in [screenshots/](screenshots/) (taken in
October 2026, before the candidate preview, manual entry and correction fields were added).

## 1. Pages

| Route | File | What the user sees | API calls |
| --- | --- | --- | --- |
| `/` Landing | `app/page.tsx` | Service status, URL form with **Analyse** and **Preview candidate (not saved)**, upload form, manual entry form, illustrative sample (labelled synthetic), "How it works", evidence standards, limitations | `GET /api/health`, `GET /api/reference/categories`, `POST /api/analyze-url`, `POST /api/product-candidates/from-url`, `POST /api/analyze-upload`, `POST /api/analyze-manual` |
| `/products` Catalogue | `app/products/page.tsx`, `ProductsBrowser.tsx` | Stored products with category filter and search, score, grade, status, source type, synthetic badge | `GET /api/products`, `GET /api/reference/categories` |
| `/products/{id}` Product report | `ProductReport.tsx`, `ReportView.tsx` | Status banner; score summary and dimension chart; product overview; price and pack details; source and extraction; nutrition table with traffic lights and printed vs normalised values; ingredient explorer; claim panel; evidence and data quality (missing fields, conflicts, extraction log); alternatives | `GET /api/products/{id}`, `GET /api/products/{id}/alternatives` |
| `/products/{id}/alternatives` | `AlternativesPanel.tsx` | Preference selector (balanced, nutrition, price, transparency), ranked alternatives with reasons, three picks, "none qualify" message | `GET /api/products/{id}/alternatives` |
| `/compare` | `CompareClient.tsx`, `CompareView.tsx` | Choose 2–6 products in one category; side-by-side dimensions, nutrition, unit price, ingredient differences, picks with reasons | `GET /api/products`, `POST /api/products/compare` |
| `/methodology` | `MethodologyView.tsx` | Weights, grade bands, thresholds with sources, claim rules, category weights, evidence labels, claim statuses, missing-data rules, data sources and licences, limitations | `GET /api/reference/methodology` |
| any other | `app/not-found.tsx` | Not-found page | — |

## 2. User journeys

### 2.1 Analyse a product page (saved)

1. Paste a product URL (the field checks it starts with http(s)) and optionally pick a category.
2. Click **Analyse**. Progress steps advance ("Validating URL", "Fetching page", "Reading structured
   data", …) while the API works; the final step completes when the result arrives.
3. On success the report opens. On error a plain message appears with the step it belongs to, for
   example `unsupported_source` or `robots_disallowed` ("upload a saved copy or screenshots instead"),
   `product_extraction_failed` (with a link to manual entry), `rate_limited`, or "The analysis service
   (API) is not running. Start it with ./run.sh api" when the backend is down.

### 2.2 Preview a candidate (not saved)

Click **Preview candidate (not saved)** instead. An amber panel titled **"Unverified product
information"** shows product, brand, category, variant, pack size, serving size, ingredients, nutrition
with basis, **image references** ("URLs only. Image availability, contents and product match have not
been verified."), **"Not found on this page"** (missing fields), **"Conflicting or invalid details need
review"**, and a collapsible **"Source and field provenance"**. Nothing is saved, scored or compared.

### 2.3 Upload a saved page or packaging photo

Section **"Continue without automatic page access"**: choose a saved `.html` page or an image (pack front,
ingredient label, nutrition table or app screenshot), optionally the product link and the shop (Blinkit,
Zepto, Swiggy Instamart, BigBasket or "not from a shop"), and optionally open **"Correct or add details
before analysis"** to enter brand, variant, pack size, ingredients, nutrition basis and nutrition values
(one `nutrient: amount unit` per line). The report labels the evidence user-supplied and unverified and
shows the OCR transcript in the extraction log.

### 2.4 Manual entry

**"Enter product details manually"** (also linked from extraction errors): product name (required),
brand, variant, pack size + unit, selling price (INR), category, ingredients, nutrition basis and values.
The form checks a name is given, nutrition has a basis, and numbers are positive before sending.

### 2.5 Browse, compare and find alternatives

`/products` → open a product → read the report → change the alternatives preference, or go to
`/compare`, select products in one category and read the picks.

## 3. States and indicators

| State | How it is shown |
| --- | --- |
| Loading | Spinner with a label ("Loading stored products…", "Finding alternatives…", "Loading methodology…"); buttons show "Previewing…" and are disabled |
| Error | `ErrorState` with the API message and a retry where useful; service-down message names the command to start the API |
| Empty | `EmptyState` (no products match, no alternatives qualify, no claims found) |
| Missing data | Values shown as "unknown", never 0; missing-fields list; status banner *partial* or *insufficient data* (no grade) |
| Evidence | `EvidenceBadge` per value: declared, derived, interpreted, verified, unknown |
| Synthetic | "Synthetic demo record" badge on every synthetic product and its prices |
| Unverified | Candidate preview panel, saved-page and photo banners, manual-entry banner |
| Conflicts | Listed in the data-quality section and in the candidate panel |

## 4. Accessibility and layout

Forms use labels and `aria-label`s, progress uses `aria-current="step"`, the candidate panel is
`aria-live="polite"`, and the layout adapts to mobile (see `screenshots/10_mobile_report.png`). A full
WCAG audit has not been done.
