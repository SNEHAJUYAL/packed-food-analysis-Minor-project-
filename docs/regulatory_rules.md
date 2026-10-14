# Regulatory rules

**Jurisdiction:** India (IN). **Source:** Food Safety and Standards (Advertising and Claims) Regulations,
2018, compendium dated 14-12-2022,
<https://www.fssai.gov.in/upload/uploadfiles/files/Compendium_Advertising_Claims_Regulations_14_12_2022.pdf>.
**Last checked:** 12 October 2026. **Effective date:** left blank in `fssai_claims.csv` until the
commencement date is confirmed from the gazette text; the compendium is the consolidated current text.

The rules live in [`data/reference/fssai_claims.csv`](../data/reference/fssai_claims.csv) and are loaded
into the `regulatory_rule` table (`python -m database.ingest --rules-only`), with the exact criteria,
required fields and verification logic stored per rule. Thresholds are per 100 g for solids and per 100 ml
for liquids unless stated.

| Claim | Nutrient | Condition | Solid | Liquid | Per 100 kcal | Energy share | Clause | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sugar free / Zero sugar | total sugars | ≤ | 0.5 g | 0.5 g | - | - | Schedule I, Sl. 10 (Sugars: Free), reg. 5(3) | verified official text |
| Low sugar | total sugars | ≤ | 5 g | 2.5 g | - | - | Schedule I, Sl. 10 (Sugars: Low) | verified official text |
| No added sugar | added sugar ingredients | none listed | - | - | - | - | Reg. 6(1)(a)(i)–(iv); 6(1)(b) | verified official text |
| High protein / Rich in protein | protein | ≥ | 10.8 g | 5.4 g | 5.4 g | - | Schedule I, Sl. 11: 20 % RDA /100 g, 10 % /100 ml, 10 % /100 kcal | derived from official text |
| Source of protein | protein | ≥ | 5.4 g | 2.7 g | 2.7 g | - | Schedule I, Sl. 11: 10 % RDA /100 g, 5 % /100 ml, 5 % /100 kcal | derived from official text |
| Low fat | total fat | ≤ | 3 g | 1.5 g | - | - | Schedule I, Sl. 2 | verified official text |
| Fat free | total fat | ≤ | 0.5 g | 0.5 g | - | - | Schedule I, Sl. 2 | verified official text |
| Low saturated fat | saturated fat | ≤ | 1.5 g | 0.75 g | - | ≤ 10 % of energy | Schedule I, Sl. 4 | verified official text |
| Saturated fat free | saturated fat | ≤ | 0.1 g | 0.1 g | - | - | Schedule I, Sl. 4 | verified official text |
| Trans fat free | trans fat | < | 0.2 g | 0.2 g | - | - | Schedule I, Sl. 6 | verified official text |
| Low calorie | energy | ≤ | 40 kcal | 20 kcal | - | - | Schedule I, Sl. 1 | verified official text |
| High fibre | fibre | ≥ | 6 g | 3 g | 3 g | - | Schedule I, Sl. 14 | verified official text |
| Source of fibre | fibre | ≥ | 3 g | 1.5 g | 1.5 g | - | Schedule I, Sl. 14 | verified official text |
| Low sodium | sodium | ≤ | 120 mg | 120 mg | - | - | Schedule I, Sl. 13 | verified official text |
| Very low sodium | sodium | ≤ | 40 mg | 40 mg | - | - | Schedule I, Sl. 13 | verified official text |
| Sodium free | sodium | ≤ | 5 mg | 5 mg | - | - | Schedule I, Sl. 13 | verified official text |
| Made from natural ingredients | ingredient classes | no synthetic additives | - | - | - | - | Reg. 9(2); Schedule V | verified official text |
| Natural | ingredient classes | single ingredient, nothing added | - | - | - | - | Reg. 9(2); Schedule V | verified official text |

**Protein in grams.** Schedule I states protein conditions as a % of the RDA. The system uses
54 g/day (ICMR-NIN 2020 RDA, sedentary adult man), so 20 % = 10.8 g. The woman's RDA is 45.7 g. This is a
team choice to confirm with the guides; the per-serving route is not checked because serving sizes are
rarely known, so a failed protein check is reported as *potential inconsistency for review*.

## How a claim is checked (`src/analyse/claims.py`)

Four separate steps, so no step can override another:

1. **Extraction:** claim phrases are found in the listing text with the `patterns` column; a phrase inside
   a longer one is dropped ("very low sodium" is not also "low sodium").
2. **Rule selection:** the rule row for that claim type.
3. **Evidence comparison:** the declared values against the rule's thresholds (and the per 100 kcal or
   energy-share route where the regulation gives one); the facts used are listed.
4. **Status:** one of four, never an accusation:
   * *consistent with available evidence*
   * *requires context* (for example "no added sugar" on a product with naturally occurring sugars,
     which reg. 6(1)(b) says must be stated)
   * *potential inconsistency for review*
   * *cannot be verified from available information* (with the missing information listed)

An LLM is never the final authority: the optional LLM step only locates text on a page, and its values
must appear verbatim in the page.

## Not yet encoded

* **FSSAI front-of-pack warning label:** a draft under Supreme Court supervision; no per-100 g cut-offs
  are published, so `fop_warning.csv` stays `TODO` and the simulation reports "not simulated".
* **"High" nutrient bounds** for traffic lights: no final Indian values; UK FSA 2016 placeholders are used
  and labelled.
* Claims outside Schedule I / reg. 6 / Schedule V (health claims, "light", comparative claims) are not
  detected.
