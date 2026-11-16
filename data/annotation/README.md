# Research annotation dataset

This directory is isolated from production PostgreSQL and existing product-analysis behavior. Do not put unlicensed package photos or private reviewer details here. The original `data/sample/off_india_subset.jsonl` and pack-check sheet are inputs/reference candidates only; keep them unchanged and preserve their source IDs when annotating.

## Versioned layout

```text
data/annotation/
  README.md
  schema_v1.json
  annotation_template.jsonl      # blank schema template; not a product record
  review_log_template.jsonl      # blank event template
  v1/
    dataset.jsonl                 # future frozen annotation release; currently absent
    manifest.json                 # future release counts, hashes, taxonomy and license summary
  splits/
    .gitkeep                      # generated manifests go here by dataset version
```

Create `v1/` (and later version directories) only when real manual annotation records exist. Never mark existing OFF rows as manually verified. Preserve raw source snapshots separately and link to them with `source_records`; do not duplicate the entire OFF dataset into annotation storage.

## Proposed taxonomy `india-packaged-food-v1`

Assign exactly one primary leaf category per in-scope product. If none fits, annotate `not_applicable` and propose a taxonomy change rather than forcing a label.

| Category ID | Scope note |
|---|---|
| `biscuits_cookies` | Biscuits, cookies, crackers and wafers primarily sold as those products. |
| `chips_savoury_snacks` | Chips, crisps, extruded/puffed savoury snack products other than traditional namkeen. |
| `namkeen` | Indian namkeen/mixture/sev and comparable traditional savoury snack mixes. |
| `breakfast_cereals_muesli` | Ready-to-eat cereal, granola and muesli products. |
| `oats_millet_products` | Packaged oats or millet-based grain products not better classified as ready cereal or mix. |
| `noodles_pasta` | Instant noodles, pasta and packaged noodle/pasta products. |
| `ready_to_eat_ready_to_cook` | Packaged meals, meal components and mixes primarily prepared as a dish. |
| `protein_bars_snacks` | Products explicitly positioned as protein bars/snacks; otherwise classify by form. |
| `spreads` | Nut/seed butters, jams and other spreads. |
| `nuts_makhana_trail_mix` | Packaged nuts, seeds, makhana and trail mixes. |
| `dairy_dairy_alternatives` | Packaged dairy foods/drinks and plant-based dairy alternatives. |
| `packaged_beverages` | Packaged non-dairy beverages, concentrates and drink mixes. |
| `sauces_condiments_dips` | Sauces, chutneys, condiments and dips. |
| `packaged_staples_mixes` | Flours, grains, pulses, salts, oils and staple/cooking mixes not better classified above. |
| `childrens_packaged_foods` | Products explicitly formulated/marketed for infants or children; age scope must be recorded from label. |
| `bakery_confectionery` | Packaged bakery products and confectionery not captured by biscuits/cookies or snack categories. |

This taxonomy is a research proposal, not the production database enum. Record the category definition version with every release. When product form makes two leaves plausible, record `requires_review` and adjudicate before supervised use.

## File policy and release process

- `annotation_template.jsonl` contains one `record_type: "template"` object with missing values; it is ignored by validation/splitting unless explicitly requested.
- Future records use one canonical annotated variant/pack row per reviewed source context. Multiple source assertions can live in `evidence.source_records[]`; if derivative source records are separate rows, they must share the same stable variant/family/pack IDs.
- Maintain stable IDs in a controlled register. IDs are opaque and never regenerated from names.
- Pin `dataset_version`, `schema_version`, `taxonomy_version`, source snapshot IDs and SHA-256 hashes in a release manifest. Corrections create a new version/revision; never overwrite a frozen release.
- Keep `review_log.jsonl` append-only. Do not commit personal names; use approved stable reviewer IDs.
- Do not include the OFF source file or image binaries in the annotation release. Preserve links, source IDs, license and attribution; ensure source terms allow each use.

## Commands

```bash
python scripts/validate_annotation_dataset.py data/annotation/v1/dataset.jsonl
python scripts/create_grouped_splits.py data/annotation/v1/dataset.jsonl \
  --output data/annotation/splits/v1-family.json \
  --mode family --seed 20261116
python scripts/create_grouped_splits.py data/annotation/v1/dataset.jsonl \
  --output data/annotation/splits/v1-brand-held-out.json \
  --mode brand_held_out --seed 20261116
```

The first command reports source/label quality and duplicate candidates; it never modifies records. Split generation excludes templates, synthetic fixtures, unverified records and unresolved/missing group IDs. Both utilities fail rather than produce leakage-prone splits. See [data dictionary](../../docs/annotation_data_dictionary.md) and [annotation guidelines](../../docs/annotation_guidelines.md).
