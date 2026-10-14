import { ClaimStatusBadge, EvidenceBadge, GradeBadge, TrafficLight } from "./badges";
import { Badge } from "./ui";

// A fixed, synthetic example (the pipeline run on a made-up "Example Foods" page).
// It is static, labelled as illustrative, and never presented as a real product.
const SAMPLE = {
  name: "Choco Crunch Whole Grain Cereal",
  brand: "Example Foods (fictional)",
  overall: 69,
  grade: "C" as const,
  dimensions: [
    { name: "Nutrition", score: 61 as number | null },
    { name: "Ingredients", score: 95 as number | null },
    { name: "Transparency", score: 90 as number | null },
    { name: "Claims", score: 0 as number | null },
    { name: "Value", score: null as number | null },
  ],
  nutrients: [
    { name: "Total sugars", value: "28 g", light: "red", label: "declared" },
    { name: "Saturated fat", value: "5 g", light: "yellow", label: "declared" },
    { name: "Fibre", value: "4 g", light: "green", label: "declared" },
    { name: "Added sugars", value: null, light: null, label: "unknown" },
  ],
  claim: {
    text: "High Protein",
    status: "potential inconsistency for review",
    reason: "7 g protein per 100 g is below the FSSAI condition of 10.8 g per 100 g (or 5.4 g per 100 kcal). The per-serving route was not checked.",
  },
};

export function SampleAnalysis() {
  return (
    <figure className="rounded-2xl border border-line bg-white p-4 shadow-sm sm:p-6" aria-labelledby="sample-caption">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Badge tone="violet">Illustrative sample (synthetic data)</Badge>
        <span className="text-xs text-muted">Methodology v0.1.0</span>
      </div>
      <div className="mt-4 flex items-start gap-4">
        <GradeBadge grade={SAMPLE.grade} size="lg" />
        <div>
          <p className="font-semibold text-ink">{SAMPLE.name}</p>
          <p className="text-sm text-muted">{SAMPLE.brand}</p>
          <p className="mt-1 text-sm text-slate-700">
            Overall <span className="font-semibold">{SAMPLE.overall}</span> / 100
          </p>
        </div>
      </div>
      <ul className="mt-4 space-y-1.5" aria-label="Sample dimension scores">
        {SAMPLE.dimensions.map((d) => (
          <li key={d.name} className="grid grid-cols-[96px_1fr_64px] items-center gap-2 text-sm">
            <span className="text-slate-700">{d.name}</span>
            <span className="h-2 rounded-full bg-slate-100">
              {d.score !== null ? <span className="block h-2 rounded-full bg-brand-500" style={{ width: `${Math.max(d.score, 1)}%` }} /> : null}
            </span>
            <span className="text-right tabular-nums text-slate-700">{d.score ?? "not scored"}</span>
          </li>
        ))}
      </ul>
      <table className="mt-4 w-full text-left text-sm">
        <caption className="sr-only">Sample nutrients per 100 g</caption>
        <tbody className="divide-y divide-line">
          {SAMPLE.nutrients.map((n) => (
            <tr key={n.name}>
              <th scope="row" className="py-1.5 font-normal text-slate-700">{n.name}</th>
              <td className="py-1.5 tabular-nums">{n.value ?? <span className="text-muted">Not found</span>}</td>
              <td className="py-1.5"><TrafficLight light={n.light} /></td>
              <td className="py-1.5"><EvidenceBadge label={n.label} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-4 rounded-xl bg-slate-50 p-3 text-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="font-medium text-ink">“{SAMPLE.claim.text}”</span>
          <ClaimStatusBadge status={SAMPLE.claim.status} />
        </div>
        <p className="mt-1 text-slate-700">{SAMPLE.claim.reason}</p>
      </div>
      <figcaption id="sample-caption" className="mt-3 text-xs text-muted">
        Illustrative sample (synthetic data): a made-up product page run through the pipeline. Value is not scored because
        no comparison set existed.
      </figcaption>
    </figure>
  );
}
