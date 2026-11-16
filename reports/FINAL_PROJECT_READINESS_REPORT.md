# Final project readiness report

16 November 2026 · methodology v0.1.0 · prepared for the November 2026 final evaluation (MSIT, GGSIPU).

## 1. Verdict

The project is **ready to demonstrate as an academic prototype**: the full pipeline runs locally, every
score explains itself, data provenance is honest, and the automated tests pass. It is **not**
production-ready and makes **no accuracy claim on real products**, because the verified pack-check set
and real retailer prices have not been collected and no ML model has been trained.

Two things should be settled before the evaluation:

1. Whether `POST /api/analyze-url` may fetch unregistered public pages (current code) or must block them
   (earlier design and reports).
2. The web UI was being redesigned by another session during this check (new dashboard and insights
   pages); re-run `./run.sh test-web`, `npx tsc --noEmit` and `npm run lint` once it is finished, and
   update `docs/USER_INTERFACE_AND_USER_GUIDE.md` and the screenshots.

## 2. Readiness matrix

Status: 1 implemented and tested · 2 implemented, runtime unverified · 3 partial · 4 planned · 5 blocked.

| Area | Feature | Status | Demo-ready | Evidence |
| --- | --- | :---: | :---: | --- |
| Acquisition | Central source registry (fail closed) | 1 | yes | tests + live 403 |
| Acquisition | URL candidate preview (OFF) | 1 | yes, needs internet | 20 tests |
| Acquisition | Saved URL analysis | 1 | yes | tests; policy decision open |
| Acquisition | Saved HTML upload | 1 | yes | tests |
| Acquisition | Packaging-photo OCR | 2 | yes, with clear photos | parser tests; no photo accuracy |
| Acquisition | Optional LLM / vision | 2 | only with a key | mocked tests |
| Acquisition | Manual entry | 1 | yes | tests |
| Acquisition | Retailer automation | 5 | no | no authorization |
| Data | OFF India 466 + synthetic 40 | 1 | yes | seeded, counted |
| Data | Annotation candidates 85, catalogue 25 + 75 | 1 (pipeline) / 3 (data) | show as research | validator ok |
| Data | Verified real-product set | 4 | no | sheet empty |
| Data | Real retailer prices | 4 | no | sheet empty |
| Intelligence | Normalisation (per 100 g/ml, salt/sodium, kJ) | 1 | yes | 18 + 25 tests |
| Intelligence | Ingredient intelligence | 1 | yes | 53/53 team phrases |
| Intelligence | Nutrition score | 1 | yes | worked example; placeholders documented |
| Intelligence | Transparency, claims, value | 1 | yes | claims 22/22 |
| Intelligence | Front-of-pack warning | 5 | no | FSSAI thresholds unpublished |
| Decision support | Compare | 1 | yes | tests |
| Decision support | Alternatives | 1 (logic) / 4 (relevance) | yes | no relevance judgements |
| Decision support | Price intelligence | 1 (code) / 4 (real data) | synthetic only | 35 synthetic observations |
| AI/ML | Trained model | 4 | no — say so | none exists |
| AI/ML | Nutri-Score agreement | 1 | yes | ρ = 0.763, n = 339 |
| Platform | API + DB + migrations | 1 | yes | running, `0002 (head)` |
| Platform | Web UI | 1 (start of check) | yes | 47 tests, tsc, lint; being redesigned |
| Platform | Docker Compose | 2 | not needed | not run |
| Platform | Hosted (Vercel + Neon) | 2 | check before demo | not re-verified |
| Docs | Documentation set and resource register | 1 | yes | this consolidation |

## 3. Acceptance criteria from the brief

| Criterion | Met? | Where |
| --- | :---: | --- |
| Existing functionality preserved | yes | no code changed by this consolidation except adding `openpyxl` to `requirements.txt`; tests pass |
| Product URL acquisition architecture documented | yes | `PRODUCT_DATA_ACQUISITION.md` |
| Central source authorization documented | yes, with open issue | same + `SYSTEM_ARCHITECTURE.md` |
| Offline saved-page workflow documented | yes | `PRODUCT_DATA_ACQUISITION.md` §5 |
| Packaging-image and manual-entry workflows documented | yes | same, `USER_INTERFACE_AND_USER_GUIDE.md` |
| Ingredient intelligence documented | yes | `FOOD_INTELLIGENCE_AND_SCORING.md` §3 |
| Nutrition scoring documented | yes | §4.1 |
| Product comparison documented | yes | `PRODUCT_COMPARISON_AND_RECOMMENDATIONS.md` |
| Alternative recommendation logic documented | yes | same |
| Price intelligence and limitations documented | yes | same §5 |
| Dataset provenance documented | yes | `DATASET_AND_DATA_ENGINEERING.md` |
| AI/ML status accurate | yes | `AI_ML_METHODOLOGY.md` |
| Full UI workflow documented | yes, for the UI at the start of the check | `USER_INTERFACE_AND_USER_GUIDE.md` |
| Installation and execution instructions verified | yes (except Docker, hosted, fresh setup) | `INSTALLATION_AND_EXECUTION.md` |
| API routes documented accurately | yes | 11 = 11 |
| Research resources registered | yes | resource register |
| Dataset licensing and source limitations recorded | yes | register + `data_sources.md` |
| Test evidence recorded | yes | `TESTING_AND_TROUBLESHOOTING.md` |
| No secrets exposed | yes | only the public default DB password from `.env.example` |
| No unverified information presented as ground truth | yes | candidate, synthetic and OCR data labelled |
| No changes pushed without permission | yes | nothing committed or pushed |

## 4. Before the viva

1. Decide the unregistered-host behaviour and update `docs/api.md` accordingly.
2. Let the UI redesign finish, re-run the frontend checks, refresh screenshots.
3. If possible, check 20–30 real packs in the pack-check sheet so at least one real-data accuracy figure
   exists, and record a few real prices.
4. Rehearse [docs/END_TO_END_DEMONSTRATION.md](../docs/END_TO_END_DEMONSTRATION.md) with the internet off
   as well as on.
