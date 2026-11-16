# Project overview

**AI-Based Multimodal Packaged Food Analysis and Consumer Decision Support System**
(application name: *Food Decision Intelligence*, tagline "Understand. Evaluate. Compare. Decide.")

Minor project, MSIT (GGSIPU), New Delhi. Idea originated by Sneha Juyal. Team: Sneha Juyal, Radhika,
Shinjini. Guides: Dr. Sudesh Pahal, Dr. Neeru Rathee. Repository:
<https://github.com/SNEHAJUYAL/packed-food-analysis-Minor-project->.

This document was consolidated on 16 November 2026 from the code in this repository. Every figure in it
was rechecked against the files or re-run on that date; see
[reports/COMPLETE_REPOSITORY_CONSOLIDATION_REPORT.md](../reports/COMPLETE_REPOSITORY_CONSOLIDATION_REPORT.md).

## 1. The problem

A packaged-food listing in India mixes a nutrition table, an ingredient list, front-of-pack marketing
claims and a price, each in its own unit and format. Some values are per 100 g, some per serving; some
pages print salt, others sodium; claims such as "high protein" or "no added sugar" have exact FSSAI
conditions that shoppers cannot check by eye. Comparing two products fairly takes time, and it is hard to
tell which numbers were printed, which were calculated and which are simply missing.

## 2. What the system does

The system takes a product as evidence (an authorized product URL, a saved product page, a pack photo or
screenshot, or values typed by the user), and:

1. **acquires** it under a central source-authorization policy (only registered and permitted sources are
   fetched; everything else is blocked before any DNS or HTTP access);
2. **extracts** identity, ingredients, nutrition, pack size, claims, price and image references, keeping
   the original printed values beside the normalised ones;
3. **normalises** nutrition to per 100 g or per 100 ml, labels every value with its evidence
   (declared, derived, interpreted, verified, unknown) and flags conflicts;
4. **analyses** ingredients against a dictionary (classes, INS additive codes, allergens), nutrition
   against sourced benchmarks, disclosure completeness, claims against FSSAI conditions and price per unit;
5. **scores** five dimensions and combines them into an explainable 0–100 score and A–E grade, refusing
   an overall grade when nutrition cannot be scored;
6. **compares** stored products in one category and **recommends alternatives** from stored records only,
   each with a written reason; and
7. **shows** all of this in a Next.js web application with evidence badges, missing-data notices and an
   extraction log.

It is an **evidence-driven product intelligence system**: the score is consumer decision support, not a
medical, clinical or safety judgement, and the methodology (v0.1.0) is a prototype whose weights are
design choices still to be calibrated.

## 3. Core principles

| Principle | How the code enforces it |
| --- | --- |
| Never invent data | Missing values stay `null` with label `unknown`; a database CHECK constraint forbids a number on an `unknown` nutrient (`ck_nutrient_unknown_is_null`). The optional LLM fallback can only keep values that appear verbatim in the page or photo transcript. |
| Evidence on every value | `core/schema.py` wraps each field in an `Evidence` object with value, label, source and note. |
| Source authorization before network access | `acquisition/registry.py` fails closed; Open Food Facts is the only enabled external product source. |
| Candidate data is not verified data | Workbook imports, URL candidates, OCR output and manual entries are all marked unverified and kept apart from verified evaluation data. |
| Explain every score | Each dimension returns an `explanation` list; alternatives carry a `rationale`. |
| Honest AI/ML status | No independently trained model exists. The "AI" components are OCR (Tesseract), optional pretrained LLM/vision extraction (Claude), TF-IDF + kNN similarity and rule-based scoring. See [AI_ML_METHODOLOGY.md](AI_ML_METHODOLOGY.md). |

## 4. Scope

Five product categories are scored: biscuits and cookies, breakfast cereals, instant noodles, beverages,
and namkeen and chips. The annotation candidate set uses a wider 14-category research taxonomy that is not
yet connected to scoring.

## 5. Document map

| Read this | For |
| --- | --- |
| [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | Layers, request flows, diagrams |
| [AI_ML_METHODOLOGY.md](AI_ML_METHODOLOGY.md) | What is deterministic, what is pretrained, what is not trained |
| [DATASET_AND_DATA_ENGINEERING.md](DATASET_AND_DATA_ENGINEERING.md) | Datasets, counts, provenance, candidate pipelines |
| [PRODUCT_DATA_ACQUISITION.md](PRODUCT_DATA_ACQUISITION.md) | Source registry, URL candidates, offline paths, error codes |
| [FOOD_INTELLIGENCE_AND_SCORING.md](FOOD_INTELLIGENCE_AND_SCORING.md) | Ingredient, nutrition, transparency, claim and value scoring with formulas |
| [PRODUCT_COMPARISON_AND_RECOMMENDATIONS.md](PRODUCT_COMPARISON_AND_RECOMMENDATIONS.md) | Comparison, alternatives, price intelligence |
| [DATABASE_AND_API.md](DATABASE_AND_API.md) | Tables, migrations, routes (full reference in [api.md](api.md)) |
| [USER_INTERFACE_AND_USER_GUIDE.md](USER_INTERFACE_AND_USER_GUIDE.md) | Pages and user journeys |
| [INSTALLATION_AND_EXECUTION.md](INSTALLATION_AND_EXECUTION.md) | Exact commands |
| [END_TO_END_DEMONSTRATION.md](END_TO_END_DEMONSTRATION.md) | A scripted demo for evaluation |
| [TESTING_AND_TROUBLESHOOTING.md](TESTING_AND_TROUBLESHOOTING.md) | Tests, results, common problems |
| [PROJECT_STATUS_AND_FUTURE_SCOPE.md](PROJECT_STATUS_AND_FUTURE_SCOPE.md) | What is done, partial, planned or blocked |
| [RESEARCH_RESOURCES_AND_DATA_SOURCES.md](RESEARCH_RESOURCES_AND_DATA_SOURCES.md) | Resource register with licences and authorization status |

Earlier documents remain valid and are linked from the new ones: [master_project_doc.md](master_project_doc.md)
(original design document), [architecture.md](architecture.md), [methodology.md](methodology.md),
[data_sources.md](data_sources.md), [regulatory_rules.md](regulatory_rules.md), [api.md](api.md),
[deployment.md](deployment.md) and [nutriscore_comparison.md](nutriscore_comparison.md).
