import Link from "next/link";
import { AnalyzeForm } from "@/components/AnalyzeForm";
import { EvidenceBadge } from "@/components/badges";
import { SampleAnalysis } from "@/components/SampleAnalysis";
import { ServiceStatus } from "@/components/ServiceStatus";
import { UploadForm } from "@/components/UploadForm";
import { EVIDENCE_LABELS, EVIDENCE_ORDER } from "@/lib/labels";

const STEPS = [
  { title: "Product URL or photo", body: "You paste a product page, or upload a pack photo, a screenshot or a saved page." },
  { title: "Extraction", body: "Structured data (JSON-LD) first, then the page HTML. robots.txt is respected." },
  { title: "Normalised record", body: "Values converted to per 100 g/ml, each with an evidence label and source." },
  { title: "Analysis", body: "Nutrients against sourced benchmarks, ingredient list, disclosure and printed claims." },
  { title: "Explainable score", body: "Five dimensions with their reasons, combined into a 0–100 score and A–E grade." },
  { title: "Alternatives", body: "Stored products in the same category, from the same shop when it is known, ranked by the preference you choose." },
];

const LIMITATIONS = [
  "A decision-support assessment from the listing's own information, not a medical, clinical or safety judgement.",
  "Methodology v0.1 is a prototype: weights and curve parameters are design choices still to be calibrated.",
  "Some benchmarks are placeholders (for example, red bounds from the UK scheme until an Indian cut-off is final); energy has no sourced benchmark yet.",
  "Listings can be incomplete or out of date. Missing values stay unknown and are never treated as zero.",
  "Claim statuses are prompts for review, not legal findings. Some routes (such as per-serving conditions) may not be checked.",
  "Comparisons and alternatives only cover products already stored, so they are not a market-wide ranking.",
];

export default function HomePage() {
  return (
    <div className="space-y-14 sm:space-y-20">
      <section className="grid items-start gap-8 lg:grid-cols-[1.1fr_1fr]" aria-labelledby="hero-title">
        <div className="space-y-5">
          <p className="text-sm font-medium tracking-wide text-brand-700">Understand. Evaluate. Compare. Decide.</p>
          <h1 id="hero-title" className="text-3xl font-semibold leading-tight text-ink sm:text-4xl">
            See what a packaged food listing actually tells you.
          </h1>
          <p className="text-base text-slate-700">
            Product pages mix nutrition tables, ingredient lists, marketing claims and prices in different units and
            formats. Comparing two products fairly takes time, and it is hard to tell which numbers were printed, which were
            calculated and which are missing. Food Decision Intelligence reads a product page, normalises it to a common basis,
            and explains every score with the evidence behind it.
          </p>
          <ServiceStatus />
          <AnalyzeForm />
          <UploadForm />
          <p className="text-sm text-muted">
            Or <Link href="/products" className="text-brand-700 underline">browse products already analysed</Link> and{" "}
            <Link href="/compare" className="text-brand-700 underline">compare them</Link>.
          </p>
        </div>
        <SampleAnalysis />
      </section>

      <section aria-labelledby="how-title">
        <h2 id="how-title" className="text-xl font-semibold text-ink sm:text-2xl">How it works</h2>
        <ol className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {STEPS.map((s, i) => (
            <li key={s.title} className="rounded-2xl border border-line bg-white p-4">
              <p className="flex items-center gap-2 font-medium text-ink">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-50 text-xs font-semibold text-brand-700">{i + 1}</span>
                {s.title}
                {i < STEPS.length - 1 ? <span aria-hidden="true" className="ml-auto text-slate-300">→</span> : null}
              </p>
              <p className="mt-2 text-sm text-slate-700">{s.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="evidence-title" className="grid gap-8 lg:grid-cols-2">
        <div>
          <h2 id="evidence-title" className="text-xl font-semibold text-ink sm:text-2xl">Evidence standards</h2>
          <p className="mt-2 text-sm text-slate-700">
            Every value carries one of five labels, so you can see how much weight it deserves.
          </p>
          <dl className="mt-4 space-y-3">
            {EVIDENCE_ORDER.map((l) => (
              <div key={l} className="flex flex-col gap-1 rounded-xl border border-line bg-white p-3 sm:flex-row sm:items-start sm:gap-4">
                <dt className="sm:w-32 sm:shrink-0"><EvidenceBadge label={l} /></dt>
                <dd className="text-sm text-slate-700">{EVIDENCE_LABELS[l].meaning}</dd>
              </div>
            ))}
          </dl>
        </div>
        <div>
          <h2 className="text-xl font-semibold text-ink sm:text-2xl">Limitations</h2>
          <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-slate-700">
            {LIMITATIONS.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
          <p className="mt-4 text-sm">
            <Link href="/methodology" className="text-brand-700 underline">Read the full methodology, sources and licences</Link>
          </p>
        </div>
      </section>
    </div>
  );
}
