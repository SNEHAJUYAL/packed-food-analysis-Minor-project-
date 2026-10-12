# Food Decision Intelligence: build report

12 October 2026 · methodology v0.1.0 · Minor project, MSIT (GGSIPU). Idea by Sneha Juyal; team Sneha
Juyal, Radhika, Shinjini; guides Dr. Sudesh Pahal, Dr. Neeru Rathee.

## 1. Implemented

**Vertical slice, working end to end:** product URL → safe fetch → JSON-LD / HTML extraction (optional
grounded LLM fallback) → normalised, evidence-labelled record in PostgreSQL → nutrition, ingredient,
transparency, claim and value analysis → explainable score and grade → alternatives from stored records →
rendered report in the Next.js app.

| Area | Delivered |
| --- | --- |
| Backend | FastAPI with the 7 spec endpoints plus a product list; typed response models; one error shape with codes; request size limit; per-client rate limit; request logging; OpenAPI docs at `/docs` |
| Fetch safety | http(s) only, no credentials, ports 80/443, DNS-resolved addresses must be public, redirects re-validated (max 5), timeout, streaming size limit, HTML only, robots.txt, per-host spacing, cache |
| Database | SQLAlchemy models for all 10 spec entities, Alembic migration `0001` (upgrade, downgrade and `alembic check` verified on PostgreSQL 16), CHECK constraints (evidence labels, categories, claim statuses, grades, unknown ⇒ NULL) |
| Data | OFF ingestion (`scripts/fetch_off_india.py` + `python -m database.ingest`), category map, regulatory rules loaded into `regulatory_rule`; 40 labelled synthetic demo records |
| Normalisation | Original printed values kept beside normalised ones; salt kept distinct from sodium; per-serving scaling labelled derived; conflicts over 2 % flagged; complete / partial / insufficient-data status |
| Ingredients | Label order kept; declared percentages only; matched / fuzzy_match / uncertain status; functional categories and neutral explanations with references |
| Claims | 18 FSSAI rules with exact criteria, clause, source URL, jurisdiction and check date; four statuses; missing information listed; extraction, rule selection, comparison and status kept separate |
| Alternatives | Stored records only, same category and basis, eligibility by preference, TF-IDF + kNN tie-break, three picks with reasons, explicit message when none qualify; stored in `recommendation` |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind 4, Recharts 3: landing, product report (score, nutrition, ingredient explorer, claims, evidence and data quality, alternatives), products, compare, alternatives and methodology pages; loading, error, partial and empty states; mobile layout; tooltips |
| Docs | README, `.env.example`, Docker Compose (db, migrate, api, web), `docs/` architecture, methodology, data sources, regulatory rules, API, deployment, screenshots |
| Evaluation | `notebooks/evaluation.ipynb` (executed) and `python -m evaluation.run` → `reports/evaluation_results.json` |

## 2. Tested results (commands actually run)

| Check | Result |
| --- | --- |
| `pytest` (SQLite for DB tests) | **140 passed** |
| `pytest tests/test_api_db.py` with `TEST_DATABASE_URL` (PostgreSQL 16, Alembic migration) | **18 passed** |
| `npm test` (Vitest + Testing Library) | **33 passed** (6 files) |
| `npm run lint`, `npm run typecheck`, `npm run build` | all exit 0 |
| Live run: API + Next.js + PostgreSQL in this environment | URL analysis, report, alternatives, compare, methodology, blocked-URL error and insufficient-data report all rendered; screenshots in `docs/screenshots/` |
| `docker compose config` | valid. **`docker compose up` was not run**: no Docker daemon in the build environment |

### Evaluation (small, team-labelled, partly synthetic sets; not accuracy claims)

| Evaluation | n | Result |
| --- | --- | --- |
| Extraction, field level, deterministic extractors | 4 synthetic pages, 60 fields | precision 0.97, recall 0.79, exact match 0.83. Misses: the unstructured page (needs the LLM fallback, no key set) and a product name that kept its pack size |
| Ingredient classification | 50 phrases | P = R = F1 = 1.00. Labels and dictionary come from the same team, so this checks consistency, not generalisation |
| Claim checks (positive = potential inconsistency) | 22 hand-worked FSSAI cases | status accuracy 1.00, FPR 0.00. Tests that the rules are implemented as written |
| Product matching | 90 perturbed queries on the synthetic sample | correct-match rate 0.99 (one typo case wrong) |
| Conflict detection | 6 constructed source pairs | 3/3 flagged, 0 false flags |
| Weight sensitivity (±20 % per dimension) | 38 scored sample products | grade changed for 0–5 products per perturbation; mean score change 0.4–1.3 points |
| Missing-field ablation | 26–38 products per nutrient | removing sugars stopped scoring for 10 of 37 (coverage below 50 %), by design |
| Nutri-Score rank correlation | – | **not run**: needs OFF records with `nutriscore_grade` |
| Expert rankings, Precision@3, NDCG@5 | – | **not run**: no expert rankings or relevance judgements yet (metric code ready and tested) |

## 3. Limitations

* **No real product data yet.** Open Food Facts was blocked by the build environment's network policy, so
  the stored products are 40 synthetic records plus synthetic test pages. All comparison, alternative and
  value results shown are therefore illustrative.
* Spec targets **not met**: 500–1,000 OFF India records; 100–200 product verified set.
* Methodology v0.1.0 weights and curves are prototype choices. Red nutrient bounds are UK FSA 2016
  placeholders; FSSAI front-of-pack thresholds are unpublished; energy has no benchmark.
* Protein claim grams depend on the 54 g/day RDA choice (to confirm). The per-serving claim route is not
  checked.
* Extraction covers JSON-LD/microdata and common HTML tables; many retailer pages render with JavaScript,
  and Playwright rendering is not used.
* The SSRF check resolves DNS before connecting; DNS rebinding needs an egress firewall in production.
  The rate limiter is per process.
* Value scores depend on which products are stored; rerun `--rescore` after loading data.

## 4. Future scope (not implemented)

Barcode lookup, label OCR (multimodal), cross-source validation, personalisation (allergens, goals),
basket optimisation, lab or verified evidence, Playwright rendering where permitted, a calibrated
methodology v0.2 from the verified set, and a trained category classifier to replace keyword rules.
