# Architecture

```
Browser (Next.js, web/)  ──/api/* rewrite──▶  FastAPI (src/api)  ──▶  services.py  ──▶  PostgreSQL
                                                     │                    │              (SQLAlchemy models,
                                                     │                    │               Alembic migrations)
                                                     ▼                    ▼
                                         extract/ → normalise/ → analyse/ → score/ → recommend/
```

## Layers

| Layer | Where | Contents |
| --- | --- | --- |
| Baseline data | `product`, `product_source (open_food_facts)`, `nutrient_value`, `product_ingredient` | Open Food Facts records loaded by `database/ingest.py`, or the labelled synthetic sample |
| Regulatory data | `regulatory_rule` (from `data/reference/fssai_claims.csv`), `data/reference/*.csv` | Claim conditions with regulation, clause, source URL, jurisdiction, date checked |
| Runtime data | `product`, `product_source (url)`, `price_observation` | Products analysed from a URL; prices are dated observations |
| Evaluation data | `data/verified/`, `data/verified/eval/` | Hand-labelled sets used by `notebooks/evaluation.ipynb` |
| Outputs | `analysis_result`, `product_claim`, `recommendation` | Versioned by `methodology_version`; the full report is stored as JSON |

## Request flow: `POST /api/analyze-url`

1. **Validate** (`extract/fetch.py: validate_url`): http(s) only, no credentials, ports 80/443, the host
   must resolve and every address must be public (no loopback, private, link-local, CGNAT, multicast,
   reserved). Local names (`localhost`, `.local`, `.internal`) are refused.
2. **Fetch** (`safe_get`): redirects followed by hand (max 5), each hop validated again; timeout
   (`FETCH_TIMEOUT_SECONDS`), streaming size limit (`FETCH_MAX_BYTES`), HTML only, one request per host per
   `FETCH_MIN_HOST_INTERVAL_SECONDS`, robots.txt honoured, page cached in `data/cache/`. The API also rate
   limits each client (`RATE_LIMIT_PER_MINUTE`).
3. **Extract** (`services.run_extraction`): JSON-LD / microdata, then the HTML nutrition table and labels,
   then the optional LLM fallback only when neither found nutrition or ingredients and
   `ANTHROPIC_API_KEY` is set. The fallback output is a strict Pydantic schema and every value must appear
   in the page text. Each step is logged with its outcome.
4. **Normalise** (`normalise/build.py`): per 100 g/ml, unit conversion (kJ→kcal, salt→sodium), per-serving
   scaling labelled *derived*, original printed values kept in `nutrition_original` and
   `nutrient_value.original_value`, conflicts over 2 % flagged.
5. **Match** (`services.match_open_food_facts`): best stored OFF record by brand + name similarity; recorded
   in the log as reference only, values are not merged.
6. **Store** (`database/repository.save_product`): one row per nutrient (NULL + `unknown` when missing, a
   CHECK constraint forbids anything else), ingredients in label order, price observation, source with
   extraction method and log.
7. **Analyse and score** (`services.analyse_row`): nutrition, ingredients, transparency, claims, value
   (against the stored products of the same category and basis), overall score and grade, status
   (`complete` / `partial` / `insufficient_data`). Stored in `analysis_result` with the methodology version.

## Alternatives and comparison (`recommend/alternatives.py`)

Candidates are stored records only: same category and nutrition basis, with an overall score. A candidate
is eligible when it does better on the chosen preference (balanced, nutrition, price, transparency; for
price it must also not score lower overall). Ranking uses the preference score with TF-IDF + kNN
similarity as the tie-break. Three separate picks (best match, lowest unit price, best nutrition) carry
reasons. When nothing qualifies the API says so instead of padding the list.

## Deployment

See [deployment.md](deployment.md). Secrets come only from environment variables (`.env`, never
committed). The DNS check happens before the connection, so DNS rebinding is not fully excluded; a public
deployment should also run the API behind an egress firewall that blocks private ranges.
