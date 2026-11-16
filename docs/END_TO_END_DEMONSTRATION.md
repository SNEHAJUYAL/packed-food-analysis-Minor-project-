# End-to-end demonstration script

A 10–15 minute walkthrough for the final evaluation. It uses only data already in the repository and one
authorized live source (Open Food Facts). Start the API and web app first
([INSTALLATION_AND_EXECUTION.md](INSTALLATION_AND_EXECUTION.md)): `./run.sh api` in one terminal,
`./run.sh web` in another, then open <http://localhost:3000>.

Before the demo, check the health endpoint shows `"database":"ok"`:

```bash
curl http://localhost:8000/api/health
```

## Step 1. Explain the purpose (landing page)

Point to the tagline, the evidence standards (five labels) and the limitations list. Say clearly: the
score is decision support, not a medical assessment; no trained ML model is claimed.

## Step 2. Source authorization

1. Paste a Blinkit or Zepto product URL and click **Preview candidate (not saved)**. Expected: blocked
   with `unsupported_source` and the advice to upload a saved page or screenshots. Explain that the
   registry is checked before any DNS or HTTP access and that only Open Food Facts is enabled.
2. (Optional, to show the API directly; this sends no request to Blinkit.)

```bash
curl -s -X POST http://localhost:8000/api/product-candidates/from-url -H 'Content-Type: application/json' -d '{"url":"https://blinkit.com/prn/x/prid/1"}'
```

Expected: `"status":"blocked"`, `"error_code":"unsupported_source"`, HTTP 403 (verified 16 Nov 2026).

## Step 3. Candidate preview from Open Food Facts

Paste an Open Food Facts product page, for example one listed in `/products` (each OFF product shows its
`world.openfoodfacts.org/product/<barcode>` source link), and click **Preview candidate (not saved)**.
Show: unverified banner, identity, ingredients, nutrition with basis, image references ("URLs only …"),
missing fields, conflicts, field provenance. Stress that nothing was saved. Needs internet access; if the
network is down, the app shows `source_fetch_failed`, which is itself a valid demonstration.

## Step 4. Offline upload with corrections

1. Save any product page from the browser (⌘S) and upload it, or upload a clear photo of an ingredient
   label or nutrition table.
2. Open **Correct or add details before analysis** and fix the brand or pack size.
3. Click analyse. In the report, open the extraction log: the OCR transcript is there next to the
   corrected values; the banner says the evidence is user-supplied and unverified.

## Step 5. Manual entry

Enter a product by hand (name, brand, pack size 200 g, price, ingredients, nutrition per 100 g). Show it
is saved with `source_type: manual` and an unverified banner, and that fields you left out are "unknown",
not zero.

## Step 6. Read a full report

Open a stored breakfast cereal from `/products`. Walk through:

* overall score and grade, and the dimension chart (N, I, T, C, V with weights 0.40/0.25/0.15/0.10/0.10);
* nutrition per 100 g with traffic lights and printed vs normalised values;
* ingredient explorer (classes, INS codes, allergens, uncertain items);
* claim panel (four statuses; a "High protein" claim that fails is "potential inconsistency for review");
* data quality: missing fields, conflicts, extraction log.

Also open one product with status **insufficient data** to show that no grade is given when nutrition
cannot be scored.

## Step 7. Alternatives and comparison

1. On the report, switch the alternatives preference between balanced, nutrition, price and transparency.
   Read one rationale aloud. Note the "Synthetic demo record" badge on synthetic alternatives; their prices
   are made up.
2. Go to `/compare`, pick 3 cereals, show the picks (best match, lowest price per 100 g, best nutrition)
   and the ingredient differences.

## Step 8. Methodology and evaluation

Open `/methodology`: weights, thresholds with sources, claim rules. Then summarise the evidence from
`reports/evaluation_results.json`: Spearman 0.76 agreement with Nutri-Score on 339 OFF products (not
accuracy), claim rules 22/22 on hand-worked cases, ingredient classes 53/53 on 57 phrases, extraction
recall 0.81 on 4 synthetic pages, OCR measured only on a rendered image.

## Step 9. What is not done

Close with [PROJECT_STATUS_AND_FUTURE_SCOPE.md](PROJECT_STATUS_AND_FUTURE_SCOPE.md): verified pack-check
set and real prices not yet recorded, no trained model, retailer sources not authorized.

## Fallbacks during the demo

| Problem | What to do |
| --- | --- |
| "The analysis service (API) is not running" | Start `./run.sh api` |
| `database_unavailable` | Start PostgreSQL, check `DATABASE_URL`, run `./run.sh migrate` and `./run.sh seed` |
| `photo_reader_missing` | `brew install tesseract`, restart the API; or use a saved `.html` page |
| No internet | Use the upload, manual-entry, report, compare and methodology steps only |
| `rate_limited` | Wait one minute (limit 10 per minute per client) |
