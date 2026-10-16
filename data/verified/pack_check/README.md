# Pack-checking sheet

`pack_check_sheet.xlsx` (and the same rows as `pack_check_sheet.csv`) is the checklist for comparing the
system with real packs. It holds 150 real Open Food Facts India products drawn at random within each category
(seed 2026), plus 10 reserves per category:

| Category | Main | Reserve |
| --- | --- | --- |
| Beverages | 50 | 10 |
| Biscuits and cookies | 30 | 10 |
| Namkeen and chips | 30 | 10 |
| Breakfast cereals | 20 | 10 |
| Instant noodles | 20 | 10 |

Each category has at least 20 products so that agreement can be reported per category. Synthetic records are
never sampled.

* **Grey columns** identify the product. `off_code` is the barcode, the stable key; `product_id` depends on
  load order.
* **Blue `sys_` columns** show what the system stored and concluded, including its top three alternatives.
* **Yellow columns** are for the checker, filled from the printed pack only.

The "How to check" tab in the workbook has the rules. In short: use the pack or a clear photo of it, copy values
per 100 g or 100 ml exactly as printed, leave unprinted values empty (never 0), and rate each alternative 1 to 5
as a swap a shopper would accept. Photos stay in the team drive, not in git.

When the sheet is filled, save it as CSV under the same name and run:

```bash
PYTHONPATH=src .venv/bin/python -m evaluation.pack_check data/verified/pack_check/pack_check_sheet.csv
```

That gives the following, each with its n:

* how many packs were found;
* whether the category was right;
* for each nutrient, agreement within 2 % and within label rounding, and the mean error;
* ingredient-list agreement;
* claim agreement;
* mean recommendation rating and Precision@3, counting a rating of 4 or 5 as relevant.

To regenerate the sheet after a methodology change, start the seeded API and run
`python scripts/make_pack_check_sheet.py`. The sample stays the same because the seed and the product order
are fixed; only the `sys_` columns change. Do this before checking starts, not halfway through.

Known before checking starts:

* Categories come from OFF tags and some are wrong. For example, PC-005 is a sev murmura snack filed under
  breakfast cereals. The `category_correct` column records these.
* 16 of the 50 sampled drinks have no stored basis, because OFF gives no pack unit. These rows have no
  nutrition grade.
* The suggested alternatives repeat. Within biscuits and within namkeen, every product gets the same first
  alternative. The ratings will show how much this matters.
