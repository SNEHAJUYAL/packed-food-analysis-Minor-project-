# Food Decision Intelligence — web frontend

Next.js (App Router) + React + TypeScript + Tailwind CSS + Recharts frontend for the FastAPI backend
described in [`../docs/api.md`](../docs/api.md).

## Run

Requires Node 22.12+ and the backend running (default `http://localhost:8000`).

```bash
cd web
cp .env.example .env.local   # optional; defaults work for a local backend
npm install
npm run dev                  # http://localhost:3000
```

Production: `npm run build && npm run start` (set `API_BASE_URL` before `npm run build`, e.g.
`API_BASE_URL=http://api:8000 npm run build`).

## API connection

The browser always calls same-origin `/api/...`. `next.config.ts` rewrites `/api/:path*` to the
backend, so no CORS setup is needed.

| Variable | Where | Default | Purpose |
| --- | --- | --- | --- |
| `API_BASE_URL` | server (Next.js) | `http://localhost:8000` | Target of the `/api/*` rewrite. Read when `npm run dev` starts and **baked in at `npm run build`** (rewrites are compiled into the build), so set it before building for production. |
| `NEXT_PUBLIC_API_BASE_URL` | browser | empty | Leave empty to use the rewrite. If set, the browser calls this URL directly (the backend must allow CORS). Also used as the rewrite target when `API_BASE_URL` is unset. |

## Scripts

| Command | What it does |
| --- | --- |
| `npm run dev` | Development server |
| `npm run build` | Production build |
| `npm run start` | Serve the production build |
| `npm run lint` | ESLint (`eslint-config-next`, core web vitals + TypeScript) |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | Component tests (Vitest + React Testing Library + jsdom) |

## Pages

| Route | Content |
| --- | --- |
| `/` | Problem statement, how it works, URL form with extraction progress, illustrative synthetic sample, evidence labels, limitations |
| `/products` | Stored products (search, category filter, select 2–6 to compare) |
| `/products/[id]` | Product report: identity and price, score and grade, dimension chart and explanations, nutrition per 100 g/ml with traffic lights, evidence badges and printed values, ingredient explorer, claims check, evidence/data quality, alternatives, disclaimer |
| `/products/[id]/alternatives` | Alternatives on their own page |
| `/compare?ids=1,2` | Side-by-side comparison (picker when fewer than two ids) |
| `/methodology` | Weights, grade bands, thresholds and claim rules with sources, evidence labels, missing data, freshness, data sources and licensing |

## Code layout

* `src/lib/types.ts` — types mirroring `docs/api.md`; contract fields the backend may not send yet are optional.
* `src/lib/api.ts` — typed client; errors become `ApiError` carrying the API's `detail.message` and `detail.code`.
* `src/lib/labels.ts`, `src/lib/format.ts` — evidence/status wording, number/date formatting.
* `src/components/` — UI; `ReportView` renders a `ProductAnalysis`.
* `src/__fixtures__/` — test fixtures derived from a real backend report (`report_example.json`).
* `src/__tests__/` — component tests.

## Rendering rules

* Only data returned by the API is shown. Missing values are "Not found" (never 0); ingredient
  percentages appear only when the API returns `percent`; alternatives and picks are exactly what
  the API returns, and its `message` is shown when nothing fits.
* Claim statuses use neutral styling; "potential inconsistency for review" is amber, not an alarm.
* Bracketed percentage fragments that the parser returns as nameless sub-ingredients (e.g. `"62%"`)
  are not listed as separate ingredients; the parent's original text, which contains them, is shown.
