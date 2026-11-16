# Complete documentation audit

16 November 2026. Scope: `README.md`, `docs/`, `reports/`, `data/**/README.md`, checked against the code,
data files, migrations and the live local API.

## 1. New documents

| File | Purpose |
| --- | --- |
| `docs/PROJECT_OVERVIEW.md` | Problem, scope, principles, document map |
| `docs/SYSTEM_ARCHITECTURE.md` | Components, four entry paths, pipelines, data separation (Mermaid) |
| `docs/AI_ML_METHODOLOGY.md` | Component classification, model cards, evaluation evidence, honest status |
| `docs/DATASET_AND_DATA_ENGINEERING.md` | Recounted datasets, OFF pipeline, candidate pipelines, identity, provenance |
| `docs/PRODUCT_DATA_ACQUISITION.md` | Registry, candidate preview, error codes, offline paths |
| `docs/FOOD_INTELLIGENCE_AND_SCORING.md` | All formulas, thresholds, weights, missing-value rules |
| `docs/PRODUCT_COMPARISON_AND_RECOMMENDATIONS.md` | Compare, alternatives, price intelligence |
| `docs/DATABASE_AND_API.md` | Tables, migrations, ER diagram, route table, consistency findings |
| `docs/USER_INTERFACE_AND_USER_GUIDE.md` | Pages, journeys, states, indicators |
| `docs/INSTALLATION_AND_EXECUTION.md` | Verified commands, one per block |
| `docs/END_TO_END_DEMONSTRATION.md` | Evaluation demo script with fallbacks |
| `docs/TESTING_AND_TROUBLESHOOTING.md` | Results, inventory, manual tests, troubleshooting |
| `docs/PROJECT_STATUS_AND_FUTURE_SCOPE.md` | Five-level feature status, blockers, future scope |
| `docs/RESEARCH_RESOURCES_AND_DATA_SOURCES.md` | 44-entry resource register with licence, API, authorization, integration and URL check |
| `reports/COMPLETE_REPOSITORY_CONSOLIDATION_REPORT.md` | Consolidation summary |
| `reports/COMPLETE_DOCUMENTATION_AUDIT.md` | This audit |
| `reports/FINAL_PROJECT_READINESS_REPORT.md` | Readiness matrix |

## 2. Existing documents updated

| File | Change | Reason |
| --- | --- | --- |
| `README.md` | New status block, candidate preview / manual entry / upload corrections, full route list, documentation index, acquisition and annotation folders in the layout, INS count | Status dated 17 Oct and route list missing two endpoints |
| `docs/api.md` | Candidate route added to the rate-limit sentence; consolidation note on unregistered hosts in `analyze-url` | Code rate-limits three routes; behaviour changed at 21:41 |
| `docs/data_sources.md`, `docs/methodology.md` | INS codes 66 → 64 | `ins_codes.csv` has 64 rows |

## 3. Documents left unchanged (still valid, linked from the new set)

`docs/master_project_doc.md` (original design), `docs/architecture.md` (short version; superseded where
it differs by `SYSTEM_ARCHITECTURE.md`), `docs/methodology.md` (apart from the INS count),
`docs/regulatory_rules.md`, `docs/deployment.md`, `docs/nutriscore_comparison.md`,
`docs/DATASET_CONSOLIDATION_GUIDE.md`, `docs/DATASET_FIELD_MAPPING.md`,
`docs/SOURCE_ADAPTER_INTERFACE_SPEC.md`, `docs/annotation_*.md`, `docs/retailer_extraction_assessment.md`,
and all task and assessment reports in `reports/` (they are dated historical records; the new documents
take precedence where they differ).

## 4. Duplicate and overlapping documentation

| Topic | Documents | Resolution |
| --- | --- | --- |
| Architecture | `architecture.md`, `SYSTEM_ARCHITECTURE.md`, `master_project_doc.md` | `SYSTEM_ARCHITECTURE.md` is current; others kept as history |
| Methodology | `methodology.md`, `FOOD_INTELLIGENCE_AND_SCORING.md` | Same numbers; the new file adds category weights and all formulas; both cite `config/scoring.json` |
| API | `api.md`, `DATABASE_AND_API.md` | `api.md` is the full reference; the new file summarises and links |
| Data sources | `data_sources.md`, `RESEARCH_RESOURCES_AND_DATA_SOURCES.md`, `DATASET_AND_DATA_ENGINEERING.md` | Licences of used sources in `data_sources.md`; research register separate; counts in the dataset doc |
| Status | `reports/PROJECT_COMPLETION_AUDIT.md`, `REQUIREMENT_STATUS_MATRIX.md`, `PROJECT_PROGRESS_SUMMARY.md`, `REMAINING_WORK_ROADMAP.md`, `final_report.md` | Superseded by `PROJECT_STATUS_AND_FUTURE_SCOPE.md` and `FINAL_PROJECT_READINESS_REPORT.md` |

## 5. Verification results

| Check | Result |
| --- | --- |
| Routes in docs vs `/openapi.json` | 11 = 11, all match |
| Database description vs models and migrations | 10 tables, constraints and source types match; `alembic current` = `0002 (head)` |
| Scoring descriptions vs `config/scoring.json`, CSVs and code | weights, grade bands, curve, deductions, transparency, claim scores, value curve and thresholds all match |
| Dataset counts | 466, 40, 85, 25 + 75, 125 image refs, 200 pack-check rows, 300 price rows all match files |
| Nutri-Score figure | ρ = 0.763, n = 339 (`reports/evaluation_results.json`, `reports/nutriscore_comparison.json`) |
| Startup and test commands | Every documented command exists in `run.sh` / `package.json`; tests, lint, typecheck, CLI, validator, health check run |
| Mermaid diagrams | 6 diagrams (architecture ×3, dataset, comparison, ER); syntax checked by reading — no Mermaid renderer was run |
| Internal links | Checked with a script (see consolidation report) |
| External links | 42 unique URLs requested; all answered (200/202, or 403 from bot protection on Blinkit, BigBasket, flash.co) |
| Secrets | No keys or passwords added. `.env` (git-ignored) was not read into any document; the documented database password is the public default from `.env.example` |

## 6. Findings not fixed (code left unchanged on purpose)

1. `analyze-url` fetches unregistered hosts (changed 21:41 by another session); documentation flags it.
2. `/api/reference/methodology` data-source text mentions `scripts/ingest_off.py`, which does not exist
   (the loader is `src/database/ingest.py`).
3. Screenshots in `docs/screenshots/` predate the candidate preview, manual entry and the UI shell
   redesign that was in progress during this audit.
4. Synthetic price observations carry the evidence label `declared` in `price_observation`; they are
   identified as synthetic by their source type and badge, not by the label.
