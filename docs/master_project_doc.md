# Food Decision Intelligence — Master Project Doc

Oct 12, 2026 · @Sneha Juyal

## 1. Project identity

This is the single source of truth for the minor project. It merges the recovered synopsis, scoring notes, literature notes, presentation scripts and the ZS pitch brief. Duplicates are removed and unverified claims are corrected (see section 18).

| Item | Detail |
| --- | --- |
| Title | AI-Based Multimodal Packaged Food Analysis and Consumer Decision Support System |
| One-line positioning | A food-product intelligence platform that turns fragmented label, claim and price data into explainable, comparable purchase decisions |
| Core framing | Packaged-food selection is a multi-criteria decision problem: nutrition, ingredients, transparency and price can conflict, and the system must explain the trade-offs |
| Idea originator | Sneha Juyal |
| Team | Sneha Juyal, Radhika,Shinjini |
| Guides | Dr. Sudesh Pahal, Dr. Neeru Rathee |
| Institution | MSIT, GGSIPU, New Delhi |
| Final evaluation | November 2026 |
| Current scope (MVP) | Product URL → extraction → normalisation → ingredient, nutrition and claim analysis → scoring → comparison → alternatives |
| Future scope | Barcode identification, package-label OCR, cross-source verification, personalisation, verified safety evidence |

Status as of October 2026: concept, synopsis and presentation are complete. No code is implemented yet. "Multimodal" in the title describes the planned evolution, not current capability.

Build rule: do not claim barcode, OCR, accuracy figures or user numbers until they exist and are measured.

## 2. Problem statement

The problem is not missing information. Consumers lack a unified, understandable and comparable way to use the information that already exists.

- **Fragmented sources.** Product pages hold descriptions, claims, price and pack size. The label holds ingredients and the nutrition panel. These are rarely read together.
- **Technical ingredients.** INS numbers, oil types, sweeteners and additives are hard to interpret. Some details, such as the specific oil, may appear only in fine print.
- **Claims need context.** "Zero Sugar", "No Added Sugar", "High Protein" and "Natural" each have regulatory conditions. A claim can be technically true and still mislead.
- **Price comparison is misleading.** Pack sizes differ, so the cheaper packet is often not the cheaper product per 100 g.
- **Healthier options are hard to find.** Identifying a better alternative means comparing several attributes across several products.

**Illustrative example (not real products)**

|  | Product A | Product B |
| --- | --- | --- |
| Pack price | ₹120 | ₹110 |
| Pack size | 200 g | 300 g |
| Price per 100 g | ₹60.00 | ₹36.67 |
| Nutrition profile | Less favourable | More favourable |

The cheaper packet is not automatically cheaper per unit. A lower price does not imply better nutrition. The system makes these trade-offs visible and explains each recommendation.

**Motivation (India context).** Packaged food is a daily purchase for most urban households, and label literacy is low. The project addresses this information asymmetry. It does not diagnose disease or detect adulteration. Any health or safety claim in the final report must cite a published source.

## 3. Introduction (synopsis-ready)

Packaged food products are widely consumed, but consumers often struggle to understand complex ingredient lists, nutrition information, food additives and promotional claims. Information on sugar, sodium, saturated fat, oils, additives and allergens may be available, but it is scattered across product descriptions and nutrition labels and is hard to interpret quickly.

This project proposes an AI-Based Packaged Food Analysis and Consumer Decision Support System that uses a product URL as its primary input. The system extracts publicly available product information, including name, ingredients, nutrition values, claims, pack size and price. It processes this information using rule-based analysis, Natural Language Processing and, where appropriate, machine learning.

The system analyses nutritional and ingredient information, interprets additives and technical ingredient names, examines marketing claims against available evidence, and compares similar products on nutrition, transparency and price per unit. It returns an explainable product assessment and ranked alternatives.

The prototype focuses on URL-based food intelligence. Barcode scanning and OCR of package labels are planned extensions that will enable faster identification and cross-verification of online and physical product information.

## 4. Literature survey

Prior work solves the parts of this pipeline separately: nutrition-aware recommendation, OCR label extraction, label-based scoring and food image recognition. Governments use front-of-pack schemes to simplify nutrition, and none of them covers claims, ingredients and price together.

### 4.1 Research areas

| Area | What existing work shows | Representative work | Use in this project |
| --- | --- | --- | --- |
| Nutrition-aware recommendation | Nutritional data and user preferences can be combined with multi-criteria decision making to recommend food | [Yera Toledo, Alzahrani and Martínez, IEEE Access 2019](https://sinbad2.ujaen.es/sites/default/files/publications/On-line-food-nutrition.pdf) | Recommendation and MCDM framing |
| Label OCR and extraction | Nutrition tables can be transcribed from photos, but warped, glossy or multilingual packaging lowers accuracy | [Fuentes et al., ICPRAM 2022](https://unpaywall.org/10.5220%2F0010827600003124); [OCR on food packaging, arXiv 2025](https://arxiv.org/pdf/2510.03570) | Future OCR phase; justifies URL-first MVP |
| Label-based scoring | OCR-extracted nutrients can feed a weighted score validated against Nutri-Score | [Akshay et al., IEEE CONECCT 2025](https://www.amrita.edu/publication/developing-the-harmfulness-score-h-score-a-novel-framework-for-evaluating-packaged-food-content/) | Closest prior work; benchmark our scoring against it |
| Food recognition with CNNs | Deep models can recognise dishes and estimate calories or nutrients from images | [DeepFood, IEEE Access 2020](https://doaj.org/article/f7f9c33b9f9f4254b8d3556b9e8cb58f); [FoodieCal, IEEE NCCC 2021](https://dspace.bracu.ac.bd/items/3adf4980-e2d1-4c71-bfc0-f32a0d2bf963) | Background for the multimodal roadmap only |
| Ingredient text processing | Ingredient lists are unstructured text that NLP can normalise into entities and categories | Open Food Facts ingredient and additive taxonomies | Ingredient intelligence module |

### 4.2 International front-of-pack systems

Each country simplifies nutrition differently. The project borrows one principle from each rather than copying a single scheme.

| Country | System | Status | How it works | Principle to borrow |
| --- | --- | --- | --- | --- |
| France, Germany and others | [Nutri-Score](https://www.santepubliquefrance.fr/en/les-actualites/signing-nutri-score-decree-another-step-toward-better-nutritional-information-consumers) | Voluntary; revised algorithm in France from March 2025 | Points for nutrients to limit and to encourage per 100 g, mapped to A–E; separate algorithms for general foods, beverages, and fats/oils/nuts | A–E grade with category-specific algorithms |
| Norway, Sweden, Denmark, Iceland | [Keyhole](https://helsenorge.no/en/kosthold-og-ernaring/keyhole-healthy-food) | Voluntary, rules binding if used | A product qualifies only if it meets thresholds for its food group (fat, sugar, salt, fibre, whole grain); being best in category is not enough | Category-specific absolute thresholds |
| Russia | ["Svetofor" traffic light](https://dairy-news.ru/news/pepsico-has-started-to-label-products-in-three-col.html) | Voluntary, Rospotrebnadzor | Green, yellow or red per nutrient for fat, saturated fat, trans fat, added sugar and salt per 100 g | Per-nutrient colour indicators |
| Japan | [Front-of-pack guideline, 26 Feb 2026](https://www.cirs-group.com/en/food/japan-caa-publishes-voluntary-front-of-pack-nutrition-labelling-guidelines-for-processed-foods) | Voluntary; mandatory nutrition table remains | Standardised front display whose values must match the nutrition table; salt highlighted | Show actual nutrient values, not only a grade |
| China | [GB 28050-2025](https://leap.unep.org/en/countries/cn/national-legislation/national-food-safety-standard-general-rules-nutrition-labelling) | Mandatory from 16 March 2027 | Energy, protein, fat, saturated fat, carbohydrate, sugars, sodium with NRV%; salt/oil/sugar advisory | Nutrient values with % reference value |
| India | [FSSAI front-of-pack proposal](https://thesouthfirst.com/health/fssai-proposes-front-of-pack-warning-labels-for-food-products-high-in-added-fat-sugar-after-sc-rebuke/) | Draft, under Supreme Court supervision | Proposed red hexagonal warning for foods high in added sugar, fat or salt; in Sept 2026 FSSAI told the Court it would consider a warning for even one high nutrient ([LiveLaw](https://www.livelaw.in/top-stories/will-consider-warning-labels-on-foods-high-in-any-single-nutrient-of-concern-fssai-revises-stand-in-supreme-court-549577)) | India-specific warning layer; check final rules before the November demo |

Nutri-Score itself is a point system, not a weighted 0–100 percentage. The literature review must describe its real algorithm, not the simplified example in section 8.

## 5. Research gaps and research questions

The contribution is integration: one explainable workflow from a product URL to a ranked, justified alternative. Do not claim that no similar system exists anywhere; that requires a systematic competitor and literature review.

| # | Gap | What this project adds |
| --- | --- | --- |
| 1 | Fragmented analysis: prior work does recognition, OCR, nutrition or recommendation alone | One pipeline from extraction to recommendation |
| 2 | Few systems start from a product URL; most need manual entry, barcodes or fixed datasets | URL-first extraction with source tracking |
| 3 | INS numbers, oils, sweeteners and additives are shown without interpretation | Ingredient normalisation into functional categories |
| 4 | Claims are displayed but rarely tested against the product's own data and the regulation | Evidence-status labels for each claim |
| 5 | Shopping tools compare price; food apps compare nutrition; few do both | Joint nutrition, transparency and price-per-unit comparison |
| 6 | Single scores rarely explain themselves | Per-dimension explanation for every ranking |
| 7 | International schemes do not fit Indian categories, and India's own front-of-pack rule is still a draft | India-specific, category-aware framework aligned to FSSAI rules |

**Research questions**

1. How accurately can structured product fields be extracted from product URLs?
2. How reliably can ingredient and nutrition data be normalised?
3. Can claim inconsistencies be identified using explicit evidence and regulatory criteria?
4. Do the rankings match defined nutritional and price-value priorities, and how do they compare with Nutri-Score where both apply?
5. How much does source completeness change the final recommendation?

## 6. Proposed solution

The MVP turns a product URL into an explainable report in seven stages. Each stage keeps its source, so every number in the final report can be traced back.

1. **URL input.** The user pastes a link to a supported brand or retailer listing.
2. **Extraction.** Name, brand, category, ingredients, nutrition table, claims, pack size and price are pulled from structured metadata (JSON-LD, schema.org) first, then HTML, then an LLM for unstructured text. Source URL and timestamp are recorded.
3. **Normalisation and validation.** Units convert to per 100 g or 100 ml. Ingredient names and INS codes map to standard entries (for example, INS 322 → lecithins → emulsifier). Missing values stay missing, never zero. Conflicting sources are flagged, not silently resolved. The product is matched to an Open Food Facts record where possible.
4. **Ingredient and nutrition analysis.** Sugars, sweeteners, oils and fats, additives, preservatives, colours, flavourings and allergens are classified. Nutrients are compared with category-specific benchmarks.
5. **Claim and transparency analysis.** Claims such as "Zero Sugar", "No Added Sugar", "High Protein", "Low Fat" and "Natural" are extracted and checked against the nutrition data and FSSAI conditions.
6. **Scoring.** Category-aware rules produce dimension scores, an overall score, an A–E grade and nutrient traffic lights (section 8).
7. **Comparison and recommendation.** Products in the same category are ranked. The system returns the best match for the user's priorities, the lowest price per 100 g, and the best nutrition option separately, each with a reason.

**Evidence principle.** Every field carries one of five labels so the system never invents data:

| Label | Meaning | Example |
| --- | --- | --- |
| Declared | Stated by the listing or package | Sugar 28 g/100 g |
| Derived | Calculated from declared data | ₹48 per 100 g |
| Interpreted | Judged against a defined benchmark | Sugar high for breakfast cereals |
| Verified | Checked against an authoritative source or regulation | Matches Open Food Facts and the label photo |
| Unknown | Cannot be established from available evidence | Palm oil percentage not disclosed |

**Claim outcomes** are evidence statuses, not accusations: consistent with available evidence · requires context · potential inconsistency for review · cannot be verified from available information.

## 7. Dataset strategy

Four data sources serve four different jobs. Keep them separate in the repo and the report.

| Source | Role | Scope for the minor project | Notes |
| --- | --- | --- | --- |
| A. [Open Food Facts](https://www.kaggle.com/datasets/openfoodfacts/world-food-facts/data) | Baseline product, ingredient and nutrition reference | Filter to India-sold products; 500–1,000 records across 4–5 categories | Community-contributed: reference data, not ground truth |
| B. FSSAI regulations | Regulatory reference for claims and labelling | Labelling and Display Regs 2020; Advertising and Claims Regs 2018; front-of-pack draft | Store each rule with source, effective date and date checked |
| C. Verified evaluation set | Ground truth for measuring accuracy | 100–200 products checked by hand against the physical label | Built by the team; the most valuable asset |
| D. Runtime URL data | Live input, current price and pack size | Whatever the user submits | Time-stamp price; show price history only once real observations exist |

**Suggested starting categories:** biscuits and cookies, breakfast cereals, instant noodles, packaged beverages, namkeen and chips. These are high-volume in India and differ enough to need category-specific rules.

**Product schema (core fields)**

| Field | Unit / type |
| --- | --- |
| product\_id, name, brand, category, variant | text |
| pack\_size, pack\_unit, price\_inr | number, g or ml, ₹ |
| energy | kcal per 100 g or 100 ml |
| protein, carbohydrate, total\_sugars, added\_sugars | g per 100 g or 100 ml |
| total\_fat, saturated\_fat, trans\_fat, fibre | g per 100 g or 100 ml |
| sodium | mg per 100 g or 100 ml (salt converted: sodium = salt ÷ 2.5) |
| ingredients\_raw, ingredients\_normalised, additives\_ins, allergens | text, list |
| claims\_raw | list |
| source\_url, collected\_at, last\_verified\_at, evidence\_label per field | text, timestamp, enum |
| conflict\_flag | boolean |

Total sugars and added sugars are not interchangeable. Store both when available, and never fill one from the other.

**Licensing.** The Open Food Facts database is under the Open Database License, and product photos are CC BY-SA ([OFF licence page](https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/tutorials/license-be-on-the-legal-side/)). Credit it and share-alike any derived database. A public product page is not permission to scrape; check each retailer's terms and prefer APIs or structured metadata.

## 8. Scoring framework

The score has two layers: a nutrition layer grounded in established nutrient profiling, and a Food Intelligence layer that adds ingredients, transparency, claims and value. All weights and cut-offs below are prototype choices to be justified and tested, not validated science.

### 8.1 Three levels of output

1. **Raw fact:** sugar = 28 g per 100 g.
2. **Interpretation:** sugar is high for breakfast cereals (red).
3. **Decision support:** nutrition 53/100, overall 58/100 (C); alternative B scores 78/100.

The raw fact is always shown, so the number never hides the data.

### 8.2 Category-aware nutrition score

Following the Keyhole principle, each category scores the nutrients that matter for it, against its own thresholds.

| Category | Nutrients weighted most |
| --- | --- |
| Biscuits and cookies | Sugar, saturated fat, energy, fibre |
| Breakfast cereals | Sugar, fibre, whole grain, protein, sodium |
| Instant noodles | Sodium, saturated fat, total fat, fibre, protein |
| Beverages | Sugar, energy, sweeteners |
| Namkeen and chips | Sodium, saturated fat, energy |

Each nutrient is converted to a 0–100 sub-score from its category thresholds (higher is better), then weighted:

```latex
N = \sum_{i} w_i \, s_i, \qquad \sum_{i} w_i = 1
```

### 8.3 Food Intelligence score and grade

```latex
S = 0.40\,N + 0.25\,I + 0.15\,T + 0.10\,C + 0.10\,V
```

N = nutrition, I = ingredient profile, T = transparency, C = claim accuracy, V = value for money (price per 100 g against the category median). Weights are illustrative.

| Score | Grade |
| --- | --- |
| 85–100 | A |
| 70–84 | B |
| 55–69 | C |
| 40–54 | D |
| 0–39 | E |

Transparency and nutrition are separate: a complete label can still describe a poor nutritional profile.

### 8.4 Worked example (illustrative cereal)

Per 100 g: 410 kcal, fat 10 g, saturated fat 5 g, carbohydrate 72 g, sugar 28 g, protein 7 g, fibre 4 g, sodium 400 mg. Ingredients: whole grain wheat, sugar, cocoa, vegetable oil, emulsifier, flavouring. Front claim: "High Protein".

| Nutrient | Sub-score | Weight | Contribution |
| --- | --- | --- | --- |
| Sugar | 35 | 0.25 | 8.75 |
| Saturated fat | 45 | 0.20 | 9.00 |
| Sodium | 65 | 0.15 | 9.75 |
| Energy | 55 | 0.10 | 5.50 |
| Fibre | 70 | 0.15 | 10.50 |
| Protein | 60 | 0.15 | 9.00 |
| **Nutrition N** |  |  | **52.5 → 53** |

| Dimension | Score | Weight | Contribution |
| --- | --- | --- | --- |
| Nutrition | 53 | 0.40 | 21.20 |
| Ingredients | 61 | 0.25 | 15.25 |
| Transparency | 72 | 0.15 | 10.80 |
| Claims | 30 | 0.10 | 3.00 |
| Value | 75 | 0.10 | 7.50 |
| **Overall** |  |  | **57.75 → 58 (C)** |

Correction from the earlier draft: it scored the "High Protein" claim 80 as consistent. Protein supplies only about 7% of energy here (7 g × 4 kcal ÷ 410 kcal), which is unlikely to meet a high-protein condition. The claim is now marked "potential inconsistency for review", pending confirmation of the exact FSSAI condition. The overall score moves from 63 to 58; the grade stays C.

**Traffic lights shown with it:** sugar red · saturated fat yellow · sodium yellow · fibre green · protein green.

### 8.5 Rules versus ML

| Task | Method | Why |
| --- | --- | --- |
| Unit conversion, nutrient thresholds, scores | Deterministic rules | Arithmetic must be exact and auditable |
| Claim conditions | Rules from FSSAI text | Legal criteria are explicit |
| Ingredient recognition and normalisation | NLP: dictionary + fuzzy matching, then a classifier | Messy free text |
| Claim extraction from page text | NLP classifier or LLM | Wording varies |
| Product categorisation and similarity | ML (TF-IDF or embeddings + kNN) | Finding comparable alternatives |
| Unstructured page extraction | LLM with schema-constrained output | Fallback when no structured metadata exists |

### 8.6 Calibrating the weights

1. Build a threshold table: parameter, source, threshold, category, unit. Use FSSAI, ICMR-NIN and WHO references; never invent thresholds.
2. Run the score on the Open Food Facts subset.
3. Compare grades with Nutri-Score where Open Food Facts provides one, using rank correlation.
4. Ask one nutritionist to rank 30 products blind; compare with the system's ranking.
5. Run a sensitivity check: change each weight by ±0.05 and report how many rankings flip.
6. Freeze version 1 of the methodology and document it.

## 9. System architecture and tech stack

&#91;embedded content: MVP architecture · 3 stages, 4 analysis modules, 1 output\]

Extraction feeds four analysis modules in parallel; their outputs meet in the scoring engine. Reference data is read-only and versioned.

**Final stack** (one stack replaces the two conflicting versions in the drafts):

| Layer | Choice | Why |
| --- | --- | --- |
| Backend and API | Python 3.11, FastAPI | Same language as data and ML code |
| Data processing | Pandas, NumPy | Normalisation and EDA |
| Extraction | httpx/Requests, BeautifulSoup, extruct (JSON-LD), Playwright only if a page needs JavaScript | Structured metadata first |
| NLP | RapidFuzz dictionary matching, spaCy; LLM API for fallback extraction | Simple, testable baseline |
| ML | scikit-learn (TF-IDF + kNN for similarity, logistic regression for claim classification) | Interpretable, enough for MVP |
| Database | PostgreSQL | Relational product schema, joins for comparison |
| Frontend | Next.js (React), Tailwind; Streamlit acceptable for the first demo | Shareable web UI |
| Charts | Recharts in the UI; Matplotlib/Seaborn in the report |  |
| Evaluation | pytest, scikit-learn metrics, notebooks | Reproducible numbers |
| Deployment | Docker; Render or Railway free tier | Single command to run |
| Future | ZXing/pyzbar (barcode), PaddleOCR or EasyOCR (labels) | Phases 2–3 |

Dropped from the drafts: Node.js backend, MongoDB, XGBoost and Firebase. They add a second language and a document store without a clear need. Use the dropped items only if a later phase justifies them.

## 10. Evaluation plan

Each component is measured against the verified evaluation set, never with one headline "model accuracy". Targets are set only after a baseline exists.

| Component | Metric | Measured against |
| --- | --- | --- |
| Field extraction | Field-level precision, recall, exact-match accuracy | Verified set (label photos) |
| Unit normalisation | % values within ±2% of the label | Verified set |
| Ingredient classification | Precision, recall, F1 per category | 300+ hand-labelled ingredient strings |
| Claim analysis | Precision, recall, false-positive rate | Hand-labelled claims with FSSAI conditions |
| Product matching | Correct-match rate | Products with a known Open Food Facts barcode |
| Scoring validity | Spearman correlation with Nutri-Score; agreement with a nutritionist's ranking | OFF Nutri-Score field; 30-product expert panel |
| Recommendation | Precision@3, NDCG@5 | Expert-rated relevance of alternatives |
| Robustness | Rank flips under ±0.05 weight changes | Sensitivity analysis |
| User value | Task completion, time to decide, comprehension quiz | 15–20 users in a moderated test |

Report every number with its sample size. Never present a target as an achieved result.

## 11. Expected outcomes

By the November evaluation the team should demonstrate a working prototype that accepts a supported product URL and returns a structured, explainable analysis.

1. **Automated extraction** of ingredients, nutrition, claims, price and pack size from supported listings.
2. **Ingredient intelligence** classifying sugars, sweeteners, oils, additives, preservatives, colours and allergens.
3. **Nutrition analysis** on a per 100 g basis with category-specific traffic lights.
4. **Claim and transparency insights** with evidence-status labels.
5. **Explainable assessment:** dimension scores, overall score and A–E grade, each with reasons.
6. **Comparison** of similar products on nutrition, transparency and price per 100 g.
7. **Ranked alternatives** for user-selected priorities.
8. **A measured evaluation** on the verified set, with the metrics in section 10.

The score is a consumer decision-support assessment, not a medical or clinical score.

## 12. Build process to the November final

The plan fits six weeks if scope stays URL-first and the verified set is built alongside the code. Replace 23 November with the real evaluation date once the department confirms it.

&#91;embedded content: Build timeline · 7 workstreams, 2 milestones\]

The verified evaluation set runs in parallel from week 1, because every metric depends on it.

**Team split**

| Workstream | Lead | Support |
| --- | --- | --- |
| Extraction, normalisation, database | Sneha | Radhika |
| Verified evaluation set (label photos, hand-checking) | Radhika | Sneha |
| Ingredient and claim rules (FSSAI tables) | Radhika | Sneha |
| Scoring, comparison, recommendation | Sneha | Radhika |
| Frontend and report page | Radhika | Sneha |
| Evaluation, report, slides | Both |  |

Swap leads as you prefer; the point is one owner per workstream.

**Weekly checkpoints**

- [ ] Week 1: repo live, schema fixed, OFF India subset loaded, 5 categories chosen
- [ ] Week 2: 3 retailer or brand sites extract end to end; 50 products verified
- [ ] Week 3: ingredient, nutrition and claim modules pass unit tests; 100 verified
- [ ] Week 4: scoring v1 and comparison working; first Nutri-Score correlation
- [ ] Week 5: UI demo flow complete; feature freeze
- [ ] Week 6: metrics computed, report and slides final, mock viva

**Repository structure**

```
food-decision-intelligence/
  README.md            # problem, demo GIF, how to run, results table
  docs/                # this doc exported, methodology, threshold table with sources
  data/
    raw/               # OFF download (git-ignored, script to fetch)
    reference/         # fssai_claims.csv, thresholds.csv, ins_codes.csv
    verified/          # evaluation set + label photos index
  src/
    extract/           # jsonld.py, html_parser.py, llm_fallback.py
    normalise/         # units.py, ingredients.py, matcher.py
    analyse/           # nutrition.py, ingredients.py, claims.py, value.py
    score/             # category_rules.py, scorer.py, grade.py
    recommend/         # similarity.py, ranker.py, explain.py
    api/               # FastAPI app
  web/                 # Next.js frontend
  notebooks/           # EDA, calibration, evaluation
  tests/
  docker-compose.yml
```

Work on branches with pull requests, so each person's contribution is visible in the commit history.

## 13. Making it a great initiative

The project becomes more than a minor project by being trusted, measured and timely. Timing is its biggest asset: India's front-of-pack warning rule is being decided now, under Supreme Court supervision.

### 13.1 Why now

In April 2025 the Supreme Court directed work on front-of-pack labelling norms. In August 2026 FSSAI proposed a red hexagonal warning for packaged foods high in added sugar, fat or salt ([South First](https://thesouthfirst.com/health/fssai-proposes-front-of-pack-warning-labels-for-food-products-high-in-added-fat-sugar-after-sc-rebuke/)). In September 2026 FSSAI told the Court it would consider a warning for foods high in even one nutrient of concern ([LiveLaw](https://www.livelaw.in/top-stories/will-consider-warning-labels-on-foods-high-in-any-single-nutrient-of-concern-fssai-revises-stand-in-supreme-court-549577)).

This gives the project a concrete, India-specific feature: **simulate the proposed FSSAI warning on any product today**, before it appears on packs. Few student projects can say their output anticipates a regulation in progress. Recheck the latest hearing before the demo, since the rule may change.

### 13.2 Roadmap

&#91;embedded content: Initiative roadmap · 4 phases, 3 gates\]

No phase starts until the previous gate is met, which keeps effort tied to evidence.

**Product versions inside these phases**

1. V1 URL intelligence (current MVP)
2. V2 Barcode lookup via Open Food Facts
3. V3 Package-label OCR
4. V4 Cross-source verification: listing vs database vs label, with discrepancy flags
5. V5 Personalised ranking by budget, diet preference and nutrient priorities
6. V6 Verified safety evidence: FSSAI recalls, regulatory alerts, accredited lab reports only; never infer adulteration from a photo
7. V7 Basket optimisation under a budget and a B2B API

### 13.3 Five moves that raise its standing

| Move | Concrete action | Payoff |
| --- | --- | --- |
| Publish | Write up methodology and evaluation for an IEEE conference (for example, an INDICON or CONECCT track) after the final | A citation-worthy contribution with your names on it |
| Compete | Enter Smart India Hackathon or a health-tech or consumer-AI hackathon with the working demo | External validation and visibility |
| Get an expert | Have one nutritionist or food-science faculty member review thresholds and rankings | Turns "our score" into "expert-reviewed score" |
| Give back | Push verified Indian products and corrections to Open Food Facts | Builds goodwill and data coverage; required in spirit by ODbL share-alike |
| Show users | Run a 15–20 person test: does the tool change which product they pick? | The single most persuasive number for interviews and investors |

### 13.4 Trust rules (non-negotiable)

- Brands can never pay to change a score. Sponsored placements, if any, are labelled and kept outside the ranking.
- Every warning cites its evidence and rule. No "fraud" or "adulteration" language without regulatory or laboratory proof.
- The methodology is published, versioned and dated.

### 13.5 Competitors and differentiation

Check each competitor's current features before claiming a gap; the table states hypotheses.

| Product | Main strength | Proposed distinction |
| --- | --- | --- |
| Buyhatke | Price tracking and comparison | Food-specific nutrition, ingredient and claim interpretation |
| Flash | AI shopping research and comparison | A specialised food decision framework |
| Yuka-type scanners | Food and ingredient ratings | Adds price-per-unit value and claim evidence |
| Open Food Facts | Open product database | An analytical decision layer on top of it (also a data partner) |
| Trustified | Independent lab testing | Online product intelligence; lab results as future evidence |

Positioning line: **Understand → Evaluate → Compare → Decide.**

### 13.6 Business model (to validate, not to assume)

| Stream | How it earns | Validation needed |
| --- | --- | --- |
| Affiliate commerce | Commission on qualifying purchases via partner links | Traffic, conversion, partner terms |
| Premium subscription | Price history, household profiles, alerts; test ₹99–199/month | Willingness to pay |
| B2B food-intelligence API | Grocery and health apps embed analysis and comparison | Pilot with one platform |
| B2B category analytics | Benchmarks for brands and retailers | Demand from one paying customer |

Illustrative arithmetic, not a forecast: at 10,000 monthly users, 2% paying ₹149 gives 200 × ₹149 = ₹29,800 per month. 1,000 affiliate purchases at ₹10 commission give ₹10,000. Combined: ₹39,800 per month before costs and taxes.

The flywheel: useful analyses bring users; users submit products and corrections; better coverage makes recommendations more reliable; reliability builds trust. It only works if usage actually improves data quality.

### 13.7 Credit and ownership

Sneha originated the idea; record that in the README and the report's acknowledgements. Decide the licence before going public. MIT maximises reuse; AGPL-3.0 keeps derivative hosted versions open. Data derived from Open Food Facts must stay ODbL either way. If a commercial path is likely, discuss ownership with the guides and the college IPR cell before publishing code.

## 14. Risks and mitigations

The two risks most likely to hurt the November demo are sites blocking extraction and a thin verified set. Address those first.

| Risk | Likelihood for MVP | Mitigation |
| --- | --- | --- |
| Retailer sites block or change markup | High | Support 3 sources well; prefer JSON-LD; cache pages for the demo; fall back to Open Food Facts by product name |
| Verified set too small to trust metrics | High | Start week 1; target 100 minimum; photograph labels in local stores |
| Incomplete product data | Medium | Show missing fields and confidence; never fabricate values |
| Outdated formulation or price | Medium | Store dates and variants; support re-verification |
| Wrong claim interpretation | Medium | Explicit FSSAI rule table with citations; human review for uncertain cases |
| Misleading universal score | Medium | Category-specific rules; show each dimension and the raw nutrients |
| FSSAI front-of-pack rule changes before demo | Medium | Keep warning thresholds in a config file, not in code |
| Scraping terms or licence breach | Medium | Respect robots and terms; credit Open Food Facts under ODbL |
| Strong existing competitors | Long-term | Validate the India-specific angle with user research |
| Low willingness to pay | Long-term | Test free use and affiliate economics before paid features |
| Commercial conflicts of interest | Long-term | Separate sponsorship from scoring; disclose links |
| False adulteration claims | Long-term | Alerts only from regulatory or accredited lab sources |

## 15. Presentation script (merged final)

One version replaces the two drafts: the plain wording of the second draft, with the detail of the first. About 7 minutes at a calm pace.

**Slide 1 – Title.** Good morning everyone. Today we present our minor project, AI-Based Multimodal Packaged Food Analysis and Consumer Decision Support System, guided by Dr. Sudesh Pahal and Dr. Neeru Rathee. When we buy packaged food, we see ingredients, a nutrition table, claims and a price. Understanding all of it, and comparing products, is hard. Our aim is to use AI to turn that information into a clear, explainable choice.

**Slide 2 – Overview.** We are building a food intelligence platform. Instead of the consumer checking the ingredient list, nutrition table, claims and price separately, the system brings them together. We plan four phases. Phase 1, our current focus, is URL intelligence: the user gives a product link and we analyse it. Phase 2 adds barcode scanning, Phase 3 reads label photos with OCR, and Phase 4 cross-checks all these sources. Today we are presenting Phase 1.

**Slide 3 – Proposed solution.** The user pastes a product URL. We extract the name, brand, ingredients, nutrition, claims, pack size and price. We then clean and standardise it: convert units to per 100 grams, and map ingredient codes such as INS 322 to their names and roles. Next we analyse sugars, fats, additives, allergens, protein, fibre and sodium. We check claims such as "high protein" or "no added sugar" against the product's own data and FSSAI conditions. Finally we score the product on several dimensions and compare it with similar products to suggest alternatives. One principle runs through all of it: we never invent data. Every value is labelled as declared, derived, interpreted, verified or unknown.

**Slide 4 – Literature survey.** We studied four areas. First, nutrient profiling: schemes like Nutri-Score in Europe, the Nordic Keyhole and Russia's traffic-light labels show how nutrients can be turned into simple signals. Second, nutrition-aware recommendation, such as Yera Toledo and colleagues in IEEE Access, 2019, which combines nutrition with multi-criteria decision making. Third, OCR and label extraction, which works but struggles with real packaging. Fourth, label-based scoring, such as a 2025 IEEE paper that validated a score against Nutri-Score. Each solves one part of the problem.

**Slide 5 – Research gaps.** Existing work is fragmented: recognition, OCR, nutrition or recommendation alone. Few systems start from a product URL. Ingredients are shown without interpretation. Claims are displayed but rarely tested. Shopping tools compare price, food apps compare nutrition, and few do both. And single scores rarely explain themselves. India adds one more gap: its front-of-pack warning rule is being finalised right now, so there is no India-specific consumer tool built around it.

**Slide 6 – Expected outcome.** Suppose I enter a product URL. The dashboard shows the key nutrients with green, yellow or red indicators, the ingredients grouped into meaningful categories, and each claim with an evidence status. It shows an overall score and grade, with the reason for each part. It compares price per 100 grams with similar products and suggests better alternatives. This is a consumer decision-support score, not a medical one. We will measure extraction accuracy, classification F1 and ranking quality against a hand-verified set of products.

**Slide 7 – Architecture.** The pipeline runs from URL to extraction, then normalisation, then four analysis modules in parallel: ingredients, nutrition, claims, and price. Their outputs meet in a rule-based scoring engine, then a comparison and ranking step, and finally an explainable report. We use rules where arithmetic and regulation must be exact, and ML where text is messy or we need similar products. The stack is Python with FastAPI, PostgreSQL, scikit-learn and a Next.js frontend.

**Closing.** To conclude, we are combining extraction, normalisation, ingredient and nutrition analysis, claim checking, scoring and comparison into one platform. The goal is to help consumers move from seeing label information to understanding it and acting on it. Thank you. We are happy to take questions.

## 16. Viva and interview Q&A

The one line to remember: "We treat packaged-food selection as a multi-criteria decision problem, where nutrition, ingredient transparency and price can conflict, and the system must explain the trade-offs."

| Question | Answer |
| --- | --- |
| Why this problem? | It is a frequent purchase decision, and the information exists but is fragmented and hard to compare. We turn it into a structured decision. |
| Where is the AI/ML? | NLP for ingredient normalisation and claim extraction, ML for categorisation and finding similar products, an LLM for unstructured pages. Rules handle arithmetic and regulation, because those must be exact and auditable. |
| Why not train a healthy/unhealthy classifier? | No validated ground-truth labels exist for Indian products. A transparent rule-based score is more defensible, and we validate it against Nutri-Score and an expert. |
| How do you know the score is right? | Rank correlation with Nutri-Score where available, agreement with a nutritionist's blind ranking, and a sensitivity test on the weights. We never equate the score with medical truth. |
| Why Open Food Facts? | Large open product, ingredient and nutrition database. We treat it as reference data, not ground truth, and evaluate against our own verified set. |
| How is this different from Nutri-Score? | Nutri-Score grades nutrition only. We add ingredients, claim evidence, transparency and price per unit, and explain each part. |
| How is it different from Buyhatke or Flash? | They compare shopping and price. We add the food-specific layer: nutrition, ingredients, claims and value in one workflow. |
| What if a site blocks you? | We prefer structured metadata and APIs, support a few sources well, and fall back to Open Food Facts. We respect site terms. |
| What about FSSAI's front-of-pack rule? | The proposed warning is a config layer in our system, so we can show it today and update thresholds when the rule is final. |
| Business model? | Affiliate commerce, premium personalisation, a B2B API and category analytics. All need validation; the first milestone is evidence of user demand. |
| What did you personally build? | Answer per person from the team-split table in section 12, with commit history as proof. |
| What next? | Validate URL extraction and scoring, grow the verified set, then barcode and OCR. |

**60-second pitch (ZS / interviews).** My minor project is an AI-based packaged food decision-support system. Consumers struggle to compare packaged foods because ingredients, nutrition, claims and prices are scattered. Our MVP takes a product URL, extracts and standardises the data, and analyses nutrition, ingredients, claims and price per 100 grams. A category-aware, multi-criteria framework ranks products in the same category and explains why. We use Open Food Facts as a baseline, keep FSSAI rules as a separate reference, and evaluate against hand-verified products. The core idea is turning fragmented data into an explainable, actionable purchase decision, not just an AI score.

## 17. Verified references

Every entry below was located on a publisher, repository or official page on 12 October 2026. Confirm page numbers on IEEE Xplore before final submission.

1. R. Yera Toledo, A. A. Alzahrani and L. Martínez, "A Food Recommender System Considering Nutritional Information and User Preferences," *IEEE Access*, vol. 7, pp. 96695–96711, 2019, doi: 10.1109/ACCESS.2019.2929413. [Link](https://sinbad2.ujaen.es/sites/default/files/publications/On-line-food-nutrition.pdf)
2. S. Akshay, A. Yuvadeep, M. K. Shreevatsa, B. M. Laveen and S. Hemanth Bharadwaj, "Developing the Harmfulness Score (H Score): A Novel Framework for Evaluating Packaged Food Content," *2025 IEEE CONECCT*, 2025, doi: 10.1109/CONECCT65861.2025.11306359. [Link](https://www.amrita.edu/publication/developing-the-harmfulness-score-h-score-a-novel-framework-for-evaluating-packaged-food-content/)
3. J. M. Fuentes, R. Paredes, E. Fulladosa, M. del Mar Giró and A. Claret, "Automatic Transcription System for Nutritional Information Charts of Spanish Food Products," *ICPRAM 2022*, doi: 10.5220/0010827600003124. [Link](https://scitepress.org/publishedPapers/2022/108276/pdf/index.html)
4. "Evaluating OCR performance on food packaging labels in South Africa," arXiv:2510.03570, 2025. [Link](https://arxiv.org/pdf/2510.03570) (add authors from the PDF)
5. "DeepFood: Food Image Analysis and Dietary Assessment via Deep Model," *IEEE Access*, 2020. [Link](https://doaj.org/article/f7f9c33b9f9f4254b8d3556b9e8cb58f) (add authors, volume and pages from IEEE Xplore)
6. S. A. Ayon, C. Z. Mashrafi, A. B. Yousuf, F. Hossain and M. I. Hossain, "FoodieCal: A Convolutional Neural Network Based Food Detection and Calorie Estimation System," *2021 National Computing Colleges Conference (NCCC)*, pp. 1–6, doi: 10.1109/NCCC49330.2021.9428820. [Link](https://dspace.bracu.ac.bd/items/3adf4980-e2d1-4c71-bfc0-f32a0d2bf963)
7. K. He, X. Zhang, S. Ren and J. Sun, "Deep Residual Learning for Image Recognition," *Proc. IEEE CVPR*, pp. 770–778, 2016.
8. Food Safety and Standards Authority of India, *Food Safety and Standards (Labelling and Display) Regulations, 2020*.
9. Food Safety and Standards Authority of India, *Food Safety and Standards (Advertising and Claims) Regulations, 2018*.
10. Santé publique France, "Nutri-Score" (revised algorithm in force from March 2025). [Link](https://www.santepubliquefrance.fr/en/les-actualites/signing-nutri-score-decree-another-step-toward-better-nutritional-information-consumers)
11. Helsenorge (Norwegian Directorate of Health), "The Keyhole – for healthier food." [Link](https://helsenorge.no/en/kosthold-og-ernaring/keyhole-healthy-food)
12. National Health Commission and SAMR (China), *GB 28050-2025 General Rules for Nutrition Labelling of Prepackaged Foods*, effective 16 March 2027. [Link](https://leap.unep.org/en/countries/cn/national-legislation/national-food-safety-standard-general-rules-nutrition-labelling)
13. Consumer Affairs Agency (Japan), front-of-pack nutrition labelling guidelines, 26 February 2026. [Link](https://www.cirs-group.com/en/food/japan-caa-publishes-voluntary-front-of-pack-nutrition-labelling-guidelines-for-processed-foods)
14. Open Food Facts, licence and API documentation. [Link](https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/tutorials/license-be-on-the-legal-side/)
15. 3S and Our Health Society v. Union of India, MA 1177/2025 in W.P.(C) 437/2024, Supreme Court of India, hearing of 10 September 2026. [Link](https://www.livelaw.in/top-stories/will-consider-warning-labels-on-foods-high-in-any-single-nutrient-of-concern-fssai-revises-stand-in-supreme-court-549577)

For items 8 and 9, cite the FSSAI gazette PDFs from fssai.gov.in and copy exact claim conditions (sugar-free, low sugar, high protein) into `data/reference/fssai_claims.csv`.

## 18. Corrections log

These changes were made while merging the recovered drafts. Update the old synopsis and slides to match.

| Area | Recovered draft said | Corrected to | Why |
| --- | --- | --- | --- |
| Reference \[1\] | "M. M. M. Elahi et al." | Yera Toledo, Alzahrani and Martínez, IEEE Access 2019 | Author list verified on the publisher record |
| References \[2\]–\[5\] | Four IEEE titles with no authors | Replaced with verified papers (refs 2–6 in section 17) | The original titles could not be found as written |
| Tech stack | Node.js or FastAPI; MongoDB or PostgreSQL; XGBoost; Firebase | One stack: FastAPI, PostgreSQL, scikit-learn, Next.js, Docker | Two drafts contradicted each other |
| Worked example | "High Protein" claim scored 80 (consistent); overall 63 | Claim flagged for review; overall 58, grade C | Protein supplies about 7% of energy in that example |
| Russia traffic light | Included energy/calories | Fat, saturated fat, trans fat, added sugar, salt | Matches Rospotrebnadzor's pilot description |
| International table | "Germany" only for Nutri-Score | France, Germany and others; revised algorithm from 2025 | Nutri-Score is multi-country and was updated |
| India | Not covered | FSSAI front-of-pack warning proposal and Supreme Court case added | Live, directly relevant regulation |
| Duplicates | Synopsis sections a–f pasted twice; two script versions | Single copy of each | Cleanup |
| Tone | Health claims (anaemia, knee pain, adulteration) as project motivation | Removed from the formal write-up | Unsourced; keep only claims with citations |
| Spelling | "Sneha Jayal" | Sneha Juyal | Name correction |
