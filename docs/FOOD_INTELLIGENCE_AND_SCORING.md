# Food intelligence and scoring

Methodology **v0.1.0 (prototype)**. Every number below is read from `config/scoring.json`,
`data/reference/*.csv` or the code in `src/normalise/`, `src/analyse/` and `src/score/` (checked
16 November 2026). Weights and curves are design choices still to be calibrated; the score is consumer
decision support, **not medically or clinically validated**. Rule sources and dates are in
[methodology.md](methodology.md) and [regulatory_rules.md](regulatory_rules.md).

## 1. Product extraction and normalised record

`core/schema.Product` holds every field as an `Evidence` object (`value`, `label`, `source`, `note`):

| Group | Fields |
| --- | --- |
| Identity | `name`, `brand`, `category`, `variant`, `pack_size`, `pack_unit`, `multipack_count` |
| Commercial | `price_inr`, `mrp_inr`, `discount_percent` (derived only when price and MRP are both present), `availability`, `retailer` |
| Label | `ingredients_raw`, `nutrition` (10 nutrients), `nutrition_basis`, `nutrition_original` (printed values and basis text), `additives_ins`, `allergens`, `claims_raw` |
| Media and source | `image_url` (HTTPS only, reference), `source_url`, `collected_at`, `conflicts`, `warnings` |

Evidence labels: **declared** (stated on listing/pack), **derived** (calculated from declared data),
**interpreted** (judged against a rule, e.g. category), **verified** (checked against an authoritative
source; only the evaluation set), **unknown** (missing, shown as unknown, never zero). Serving size is used
to scale per-serving panels; the product description is used for claim detection and category keywords.

## 2. Nutrition normalisation

Nutrients: energy (kcal), protein, carbohydrate, total sugars, added sugars, total fat, saturated fat,
trans fat, fibre (g), sodium (mg).

| Rule | Implementation |
| --- | --- |
| Basis | per 100 g for solids, per 100 ml for liquids (`nutrition_basis`) |
| Per serving → per 100 | `value × 100 ÷ serving size` when the serving size is stated; labelled **derived**. A panel without a stated basis is not used |
| Energy | kJ → kcal by ÷ 4.184 |
| Salt and sodium | sodium (mg) = salt (g) ÷ 2.5 × 1000, labelled derived; salt is kept distinct from sodium; benchmarks are applied to salt |
| Conflicts | two sources differing by more than 2 % set `conflict_flag` and list the conflict |
| Missing | `None` + `unknown`; the database rejects a number on an unknown nutrient |

## 3. Ingredient intelligence (`normalise/ingredients.py`)

1. **Split** the list at top level, bracket-aware; compound ingredients are parsed recursively.
2. **Additives**: INS codes in forms such as `INS 322`, `E322`, `500(ii)` and bare codes in brackets are
   looked up in `ins_codes.csv` (64 codes, status `seed_verify`, to be checked against Codex CXG 36-1989
   and FSSAI additive regulations).
3. **Match** each ingredient to `ingredient_terms.csv` (219 terms) exactly or by containment, then by
   RapidFuzz `ratio` ≥ 90. Status: `matched`, `fuzzy_match` (with score) or `uncertain` (not classified).
4. **Classify** into the 36 classes of `ingredient_classes.csv`: sugars and sweeteners (`added_sugar`,
   `artificial_sweetener`, `non_nutritive_sweetener`, `polyol`); grains (`whole_grain`, `refined_flour`,
   `grain_unspecified`, `modified_starch`, `carbohydrate_additive`); fats and oils (`oil_palm`,
   `oil_specified`, `oil_unspecified`, `hydrogenated_fat`); additives (`preservative`, `antioxidant`,
   `synthetic_antioxidant`, `emulsifier`, `thickener` (stabilisers), `acidity_regulator`, `raising_agent`,
   `anticaking_agent`, `carbonating_agent`, `flavour_enhancer`, `flavouring`, `artificial_flavour`,
   `generic_additive` (class named without an INS code)); colours (`natural_colour`, `caramel_colour`,
   `synthetic_colour`, `colour`); and others (`salt`, `salt_substitute`, `cocoa`, `caffeine`,
   `micronutrient`, `common_ingredient`). Each class has a neutral explanation of what it is, not a
   health verdict.
5. **Allergens** from `allergens.csv` (9 FSSAI groups: gluten cereals, crustacean, milk, egg, fish,
   peanut, tree nuts, soy, sulphite); "may contain" advisories are kept separately.
6. Label order is kept; a percentage is shown only when printed.

Protein and fibre sources appear through the nutrient values and the whole-grain class; there is no
separate protein-source classifier. **The system does not claim any ingredient is harmful**: classes are
processing and disclosure signals.

## 4. Dimension scores

### 4.1 Nutrition score N

Benchmarks (`thresholds.csv`; a category-specific row would override these generic rows, none exist yet):

| Nutrient | Foods per 100 g green / red | Drinks per 100 ml green / red | Direction |
| --- | --- | --- | --- |
| Total fat | 3 / 17.5 g | 1.5 / 8.75 g | lower better |
| Saturated fat | 1.5 / 5 g | 0.75 / 2.5 g | lower better |
| Total sugars | 5 / 22.5 g | 2.5 / 11.25 g | lower better |
| Salt | 0.3 / 1.5 g | 0.3 / 0.75 g | lower better |
| Fibre | 3 g | 1.5 g | higher better |
| Protein | 5.4 g | 2.7 g | higher better |
| Energy | TODO | — | no benchmark yet → left out |

Green bounds come from FSSAI Advertising and Claims Regulations 2018 Schedule I ("low"/"source of");
red bounds are the UK DH/FSA 2016 front-of-pack scheme as a **labelled placeholder** because FSSAI has no
final "high" cut-off; protein 5.4 g is 10 % of the ICMR-NIN RDA of 54 g.

Sub-score curve (`score/category_rules.subscore`):

* lower-better: value ≤ green → 100; linear to 40 at red; linear to 0 at 2 × red.
* higher-better: 0 → 0, linear to 100 at the green bound.

Traffic lights: green ≤ green bound; red > red bound; otherwise yellow.

Category weights (`category_weights.csv`, prototype):

| Category | Weights |
| --- | --- |
| Breakfast cereals | sugars 0.25, saturated fat 0.20, sodium 0.15, energy 0.10, fibre 0.15, protein 0.15 |
| Biscuits and cookies | sugars 0.25, saturated fat 0.25, energy 0.25, fibre 0.25 |
| Instant noodles | sodium, saturated fat, total fat, fibre, protein 0.20 each |
| Beverages | sugars 0.50, energy 0.50 |
| Namkeen and chips | sodium, saturated fat, energy 0.333 each |

**N = Σ wᵢ sᵢ / Σ wᵢ over known nutrients** (renormalised), only if the known weight is at least 50 %
(`min_nutrition_coverage`); otherwise N is unknown. Because energy has no benchmark, beverages can be
scored only on sugars (50 % coverage, just enough).

### 4.2 Ingredient Quality Indicator I

Start at 100, apply deductions from `ingredient_deductions`, clamp to 0–100:

| Signal | Points |
| --- | --- |
| Added sugar in the first three ingredients / elsewhere | −15 / −5 |
| Hydrogenated fat | −20 |
| Palm oil, artificial sweetener, synthetic colour, refined flour first | −10 each |
| Flavour enhancer, synthetic antioxidant, preservative, artificial flavour | −5 each |
| Whole grain first | +10 |

No ingredient list → I unknown. Unmatched ingredients are listed in the explanation.

### 4.3 Transparency score T

`100 × (core fields disclosed ÷ 10)` over ingredients, pack size, price, energy, protein, carbohydrate,
total sugars, total fat, saturated fat and sodium; +3 each for added sugars, trans fat and fibre;
−5 per additive class named without an INS code; −8 if the oil source is not disclosed; deductions capped
at 40; clamped 0–100. Transparency is kept separate from nutrition: a complete label can describe a poor
product.

### 4.4 Marketing Claim Assessment C

Claims are found by regex in name, description and bullet text (`fssai_claims.csv`, 18 rules: nutrient
content claims from Schedule I, "no added sugar" from reg. 6(1), "natural" from reg. 9(2) + Schedule V).
A shorter match inside a longer one is dropped. Each claim gets one of four statuses:

| Status | Score | Meaning |
| --- | --- | --- |
| consistent with available evidence | 100 | Declared values meet the condition |
| requires context | 60 | May be accurate but needs a qualifier (e.g. naturally occurring sugars) |
| cannot be verified from available information | 50 | A value or condition is missing |
| potential inconsistency for review | 0 | Declared values do not meet the condition; a prompt for review, not an accusation |

C = mean of claim scores; no claims → C not scored. Protein claims also test the per-100 kcal route; the
per-serving route is not checked and the reason says so.

### 4.5 Value-for-Money score V

Unit price = price ÷ pack size × 100 (₹ per 100 g/ml). V = 50 − 50 × log₂(unit ÷ category median),
clamped 0–100: 50 at the median of stored products in the same category and basis, 100 at half, 0 at
double. No price, no pack size or no comparison set → V unknown. V changes as more products are stored;
`./run.sh rescore` recomputes everything.

## 5. Combined Food Intelligence score S

**S = 0.40 N + 0.25 I + 0.15 T + 0.10 C + 0.10 V**, each dimension rounded half-up first, weights
renormalised over known dimensions. **If N is unknown there is no overall score or grade.**
Grades: A ≥ 85, B ≥ 70, C ≥ 55, D ≥ 40, E < 40.

Status: *complete* (all core fields, every dimension scored, no conflicts), *partial* (something missing
or conflicting, listed), *insufficient_data* (N cannot be scored).

Worked example (`tests/test_scoring.py`, master doc section 8.4): N = 52.5 → 53, S = 57.75 → 58, grade C.

## 6. Front-of-pack warning simulation

`analyse/fop_warning.py` would simulate the draft FSSAI front-of-pack warning. `fop_warning.csv` is TODO
until the rule is final, so the report shows "not simulated".

## 7. Limitations

* Prototype weights; red bounds are a foreign placeholder; energy has no benchmark.
* Category is assigned by keywords or OFF tags; five categories only.
* Ingredient dictionary and INS list are seed lists awaiting verification.
* OFF data is crowdsourced; 0 of the 466 seeded records are complete.
* Agreement with Nutri-Score (ρ = 0.76, n = 339) is not accuracy.
