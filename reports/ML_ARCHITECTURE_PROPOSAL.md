# Proposed ML architecture for packaged-food analysis

**Status:** design recommendation; not implemented. Existing deterministic and extraction behavior should remain the fallback and source of truth until a model passes offline and shadow evaluation.

## Design principles

1. Preserve the current request contract: product evidence flows through extraction → normalization → analysis/scoring → response. Models propose labels/candidates; they do not silently overwrite declared evidence.
2. Separate source evidence from model inference. Persist raw text, provenance, timestamps and current deterministic outputs; attach model predictions with model/version, confidence, evidence span and status.
3. Use explicit abstention. Low-confidence, out-of-taxonomy, conflicting or unsupported inputs remain `unknown`/review-needed, not guessed.
4. Keep deterministic rules for units, nutrient arithmetic, regulatory checks, hard eligibility constraints and safety-relevant missing-data behavior. ML can classify noisy text, retrieve candidates or rank approved alternatives.
5. Make deployment reversible: versioned artifacts, pinned feature/label schemas, canary or shadow comparison, rollback to existing deterministic modules.

## Proposed logical components

```text
Web UI
  │ existing API contracts
FastAPI routes → services/orchestrator
  ├─ Evidence extraction adapters (existing JSON-LD, HTML, OCR, optional LLM)
  ├─ Deterministic normalization and validation (existing, improved with reviewed data)
  ├─ Model registry/loader (proposed; loads a pinned local artifact, no training at request time)
  │    ├─ Category predictor (proposed)
  │    ├─ Ingredient span/canonicalizer (proposed, only after annotation)
  │    ├─ Identity candidate ranker (proposed, after pair labels)
  │    └─ Recommendation ranker (later, after relevance data)
  ├─ Deterministic scoring / eligibility / explanation (existing)
  └─ Product/source/evidence persistence (existing schema; future additive versioning may be needed)

Offline data preparation → label QA → family/brand grouped split → train/evaluate → signed/versioned artifact
                                                               └→ shadow/canary evaluation → promote/rollback
```

The diagram is a target shape, not current code. No model registry, trained artifact, training CLI, inference service, or model monitoring pipeline is evidenced in this checkout.

## Integration boundaries and model choices

| Task | Recommended progression | Proposed inference boundary | Keep deterministic |
|---|---|---|---|
| Category | Start with TF-IDF word/character n-grams + logistic regression or linear SVM after label review; compare against existing keyword rules. A compact pretrained multilingual encoder is a later option only if language/domain errors justify it and data/license/runtime allow. | Return top candidates, calibrated confidence, taxonomy version and abstain reason. Use only as an interpreted suggestion; user/source-declared category takes precedence. | Category allowlist, unknown/out-of-scope handling, source evidence. |
| Ingredient recognition/normalization | Continue parser + dictionary/INS rules as baseline. After diverse span annotation, compare CRF or multilingual token classifier with lexicon/rule hybrid. For normalization, use exact aliases first; embedding similarity retrieves candidate canonical terms for review, not autonomous medical/health claims. | Return ordered spans, canonical candidate, confidence, evidence offsets, label source, model version; preserve raw label and ambiguous aliases. | Ingredient order, percentages only when present, INS validation, allergen/advisory rules and abstention. |
| Nutrition profile | Retain arithmetic/threshold rules. A supervised classifier only makes sense if an independent target is defined and not simply the current score/grade. Potential later model: interpretable calibrated model on verified per-100g/ml nutrient features, with missingness and category explicitly handled. | Return a prediction separate from declared values, target definition and reference version; expose limitations and confidence. | Unit conversion, salt↔sodium derivation, regulatory threshold calculation and missing values. |
| Product identity | Start with hierarchical deterministic candidate generation: exact valid GTIN, source-scoped IDs, normalized brand/name/variant/net pack; then a pair classifier or cross-encoder only after hard-negative and adjudicated pair data. | Never auto-merge on a name score alone. Produce candidate links and field-level agreements/conflicts for review. | GTIN validation, barcode mismatch gates, distinct variants/packs, reversible crosswalk. |
| Alternatives | Preserve existing eligibility rules. Collect expert/user pairwise relevance and context before learning-to-rank. Begin with a small LambdaMART/LightGBM-style ranker only if enough group/query judgments exist; compare against current preference ranking. | Rank only eligible stored candidates. Return model/version, feature explanations and deterministic reason codes. | Same-category/basis gates, user constraints, price freshness, allergen exclusions, no-candidate behavior. |
| Packaging OCR | Existing Tesseract path remains baseline. Evaluate modern OCR/vision-language systems on licensed, diverse photographs before considering fine-tuning. OCR text extraction is different from ingredient entity recognition; keep them separate. | OCR returns transcription, boxes/confidence where available; parsers/normalizers map text to fields and retain reviewable evidence. | Unit/range validation, label grounding, manual review for low confidence and conflict handling. |

## Serving and versioning proposal

- Introduce a small `ModelProvider` interface behind services, with typed inputs/outputs and a deterministic no-model implementation. Load immutable, local model artifacts at process start; do not train or fit on requests. Existing `src/recommend/similarity.py` fitting TF-IDF to a candidate set is runtime retrieval, not a reusable trained model artifact.
- Each prediction record should include `task`, `model_name`, `model_version`, `artifact_hash`, `taxonomy_or_label_version`, `prediction`, calibrated confidence if available, abstention/review status, evidence IDs/spans, inference timestamp and runtime. Do not label a prediction `verified`.
- Keep `EvidenceLabel` semantics: declared/verified values stay intact; inference should be marked interpreted/proposed. Avoid writing predictions into `ProductRow` as though they were package facts.
- `services.py` should orchestrate optional calls and handle timeouts/absence gracefully. Hard constraints and scoring run on the accepted deterministic data path. Add shadow mode first: return/log predictions internally while the existing output drives the UI.
- API response changes, prediction storage, family identity tables, model registry and background retraining are future design work requiring separate schema/API review. No migration is recommended as part of this assessment.
- Frontend should distinguish “label says” from “model suggests” and expose uncertainty only when it helps resolve a meaningful decision; never present a classifier score as a health grade.

## Training and evaluation lifecycle

1. **Specification:** define one task, label ontology, intended use, error costs and an out-of-scope/abstain label. Version the annotation guide and taxonomies.
2. **Data assembly:** retain immutable source snapshot, record IDs, package/label evidence rights, original strings/images and per-field provenance. Keep synthetic records out of task training and final test.
3. **Annotation:** use trained reviewers, double-label a meaningful subset, adjudicate disagreements and measure inter-annotator agreement. Preserve missing/illegible/unavailable distinct from negative or zero.
4. **Deduplication and partitions:** assign brand/family/variant groups before splitting. Keep all packs, images, OCR variants and derivative OFF-derived copies of one family within one partition. Use train/validation/test grouped by family; add brand-held-out and temporal holdout tests.
5. **Baselines:** first score deterministic code; compare simple rules, TF-IDF/linear models and only then pretrained transformer/embeddings. Establish meaningful majority/lexicon baselines and class support.
6. **Metrics:** category macro-F1/per-class recall/coverage; ingredient span precision/recall/F1 plus canonical accuracy; nutrition absolute error/calibration or class macro-F1 as defined; matching precision-recall at threshold and false-merge rate; recommendation NDCG/Recall@K with judged queries. Report abstention coverage and error slices.
7. **Promotion:** freeze artifact/feature schema, test once, review failures and rights/security, then shadow deployment. Promote only when it beats the incumbent on predefined metrics without unacceptable subgroup regressions. Monitor drift, coverage, latency and human corrections; rollback on regressions.

## Reusable modules and future work

**Reuse now:** `src/pipeline.py`/`services.py` orchestration; `Product`/`Evidence`; `normalise/ingredients.py` and `units.py`; `analyse/` and `score/` deterministic rules; `recommend/alternatives.py` eligibility; `recommend/similarity.py` as a transparent text baseline; `database` provenance and snapshots; `src/evaluation/metrics.py` metric primitives; existing fixture tests and notebook as harness starting points.

**Future development:** versioned family/variant annotation data; task-specific annotation schemas and quality tooling; group-split dataset builder; deterministic baseline CLI and reproducible evaluation manifests; calibration/abstention; model artifact loading/versioning; model-output evidence schema; shadow inference and telemetry; regression gates; improved category taxonomy; rights/retention rules for label images; and a human review path. These are proposals and are not implemented by the current repository.

## Single recommended next implementation task

Build a **read-only real-product annotation and grouped evaluation dataset workflow for 200–300 variants**. Add a versioned annotation specification plus a dataset validation/split script that records brand-family/variant groups, source/licence/evidence provenance, field-level missingness and label review status. Populate it by manual label/package verification before training. This is the highest-value next step because it addresses the shared blocker for every proposed model and prevents synthetic data or same-family leakage from creating false confidence.
