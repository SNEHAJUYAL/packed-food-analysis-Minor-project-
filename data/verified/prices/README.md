# Price-entry sheet

Open Food Facts has no prices, so real products get prices only from people recording what they see.
`price_entry_sheet.xlsx` (same rows in `price_entry_sheet.csv`) has two rows for each of the 150 pack-check
products, one for Zepto and one for Blinkit. Add rows for other platforms, a shop shelf, or the MRP printed
on a pack. The "How to record" tab has the rules.

Import a filled sheet (saved as CSV) with:

```bash
./run.sh prices data/verified/prices/price_entry_sheet.csv
```

The import does the following:

* It stores each price with its platform, place and observation time.
* It computes the price per 100 g or 100 ml from the listed pack size.
* It recomputes value for money.
* It skips any row that has no price, no date, an unreadable pack size, or a listing not confirmed as the same
  product, and reports how many rows it skipped for each reason.

## Why prices are recorded by hand

* **No scraping.** Zepto and Blinkit offer no public price API. Their websites could not be reached from the
  build environment, so their terms of use and robots.txt were not read. The project's data rules forbid
  bypassing logins, location gates or anti-bot controls, and collecting from these platforms automatically
  would need all three. Until a platform gives written permission, the safe assumption is that automated
  collection is not allowed.
* **Hand recording.** A person can open the app as an ordinary shopper and note a few hundred prices for a
  college research project. This is ordinary use, not bulk copying. Keep screenshots as evidence, but keep
  them in the team drive and out of git.
* **Bulk data needs permission.** For larger volumes, ask the platform for data access for academic use, or
  use a source whose terms allow reuse.
* **Prices vary.** Prices on these apps change with the pin code, time of day and offers, so every row records
  where and when the price was seen. Different places and times are not averaged.
