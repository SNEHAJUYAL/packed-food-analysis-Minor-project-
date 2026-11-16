import Link from "next/link";
import { EvidenceBadge, GradeBadge, SyntheticBadge } from "@/components/badges";
import {
  IconArrowRight, IconChart, IconColumns, IconLeaf, IconScan, IconShield, IconSparkle, IconTag,
} from "@/components/icons";
import { LandingAnalyze } from "@/components/LandingAnalyze";
import { SampleAnalysis } from "@/components/SampleAnalysis";
import { Badge, buttonClass } from "@/components/ui";
import { EVIDENCE_LABELS, EVIDENCE_ORDER } from "@/lib/labels";

const FEATURES = [
  { icon: IconScan, title: "Multimodal product analysis", body: "Read a product page, a pack photo, an app screenshot or a saved page, and turn it into one structured record." },
  { icon: IconChart, title: "Nutrition intelligence", body: "Every nutrient normalised per 100 g or 100 ml and compared with sourced benchmarks, with traffic lights." },
  { icon: IconSparkle, title: "Ingredient transparency", body: "Ingredients in label order with their classes, INS additive codes and detected allergens, each explained." },
  { icon: IconShield, title: "Claim verification", body: "Front-of-pack claims such as “High Protein” checked against FSSAI conditions, with the facts used." },
  { icon: IconColumns, title: "Fair comparison", body: "Products from one category side by side on the same basis, including price per 100 g/ml." },
  { icon: IconLeaf, title: "Explainable alternatives", body: "Stored products ranked by the preference you choose, each with the reason it was suggested." },
];

const STEPS = [
  { title: "Provide the product", body: "Paste a product URL, upload a photo or saved page, or type the label details." },
  { title: "Extract the evidence", body: "Structured data (JSON-LD) first, then the page HTML or OCR text. robots.txt is respected." },
  { title: "Normalise", body: "Values converted to per 100 g/ml, each with an evidence label and its source." },
  { title: "Analyse & explain", body: "Five scored dimensions with their reasons, claim checks and alternatives." },
];

const LIMITATIONS = [
  "A decision-support assessment from the listing's own information, not a medical, clinical or safety judgement.",
  "Methodology v0.1 is a prototype: weights and curve parameters are design choices still to be calibrated.",
  "Listings can be incomplete or out of date. Missing values stay unknown and are never treated as zero.",
  "Comparisons and alternatives only cover products already stored, so they are not a market-wide ranking.",
];

/* Illustrative, synthetic comparison: fictional products, made-up values, labelled as such. */
const COMPARE_SAMPLE = [
  { name: "Fictional Oat Crunch", grade: "B" as const, sugar: "9 g", fibre: "8 g", price: "₹38.00" },
  { name: "Fictional Choco Loops", grade: "D" as const, sugar: "31 g", fibre: "3 g", price: "₹44.50" },
];

function SectionTitle({ eyebrow, title, body, id }: { eyebrow: string; title: string; body?: string; id?: string }) {
  return (
    <div className="max-w-2xl">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-500">{eyebrow}</p>
      <h2 id={id} className="mt-2 text-2xl font-bold text-ink sm:text-[2rem] sm:leading-tight">{title}</h2>
      {body ? <p className="mt-3 text-[15px] leading-7 text-muted">{body}</p> : null}
    </div>
  );
}

export default function HomePage() {
  return (
    <div>
      {/* Hero */}
      <section aria-labelledby="hero-title" className="relative overflow-hidden">
        <div aria-hidden="true" className="pointer-events-none absolute -right-40 -top-40 h-[520px] w-[520px] rounded-full bg-sage/60 blur-3xl" />
        <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-4 pb-16 pt-12 sm:px-6 lg:grid-cols-[1.1fr_1fr] lg:px-10 lg:pb-24 lg:pt-20">
          <div>
            <Badge tone="green" className="!px-3 !py-1">Know your food · Choose with confidence</Badge>
            <h1 id="hero-title" className="mt-5 text-4xl font-extrabold leading-[1.08] text-ink sm:text-5xl lg:text-[3.5rem]">
              Know Your Food.<br /><span className="text-forest">Make Smarter Choices.</span>
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-slate-700 sm:text-lg">
              Understand ingredients, evaluate nutrition, compare prices, and discover better packaged food alternatives
              through intelligent product analysis.
            </p>
            <div className="mt-8"><LandingAnalyze /></div>
            <p className="mt-6 text-xs text-muted">
              Evidence-labelled · robots.txt respected · not a medical score
            </p>
          </div>
          <div className="relative">
            <SampleAnalysis />
          </div>
        </div>
      </section>

      {/* Features */}
      <section aria-labelledby="features-title" className="border-y border-line bg-white">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-10 lg:py-24">
          <SectionTitle id="features-title" eyebrow="Platform" title="Food intelligence, from label to decision"
            body="One workflow that reads the product, checks the evidence and explains what it means for your choice." />
          <ul className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map(({ icon: Icon, title, body }) => (
              <li key={title} className="rounded-[var(--radius-card)] border border-line bg-ivory/50 p-6 transition hover:border-brand-300 hover:bg-white hover:shadow-[var(--shadow-card)]">
                <span aria-hidden="true" className="flex h-11 w-11 items-center justify-center rounded-xl bg-forest text-sage"><Icon className="h-5 w-5" /></span>
                <h3 className="mt-4 text-base font-semibold text-ink">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted">{body}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" aria-labelledby="how-title" className="scroll-mt-20">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-10 lg:py-24">
          <SectionTitle id="how-title" eyebrow="How it works" title="Four steps, every one of them visible" />
          <ol className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((s, i) => (
              <li key={s.title} className="relative rounded-[var(--radius-card)] border border-line bg-white p-6">
                <span className="font-display text-sm font-bold text-brand-500">0{i + 1}</span>
                <h3 className="mt-2 text-base font-semibold text-ink">{s.title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted">{s.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Nutrition + comparison previews */}
      <section aria-labelledby="preview-title" className="bg-deep text-sage">
        <div className="mx-auto grid max-w-7xl gap-12 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:px-10 lg:py-24">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#9fd3ae]">Nutrition & comparison</p>
            <h2 id="preview-title" className="mt-2 text-2xl font-bold text-white sm:text-[2rem] sm:leading-tight">
              Compare on the same basis, not the same marketing
            </h2>
            <p className="mt-4 max-w-lg text-[15px] leading-7 text-sage/80">
              Pack sizes and serving sizes differ, so every comparison is made per 100 g or 100 ml. Total pack price and
              unit price are shown separately, so the cheapest pack and the best value are never confused.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/compare" className="inline-flex items-center gap-2 rounded-xl bg-sage px-5 py-3 text-sm font-semibold text-deep transition hover:bg-white">
                Compare products <IconArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/alternatives" className="inline-flex items-center gap-2 rounded-xl border border-white/20 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10">
                Find alternatives
              </Link>
            </div>
          </div>
          <figure className="rounded-[var(--radius-card)] bg-white p-5 text-ink shadow-[var(--shadow-lift)] sm:p-6" aria-labelledby="compare-sample-caption">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold">Side by side · per 100 g</p>
              <SyntheticBadge />
            </div>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full min-w-[360px] text-left text-sm">
                <caption className="sr-only">Illustrative comparison of two fictional products</caption>
                <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
                  <tr><th scope="col" className="py-2 font-medium">Product</th><th scope="col" className="py-2 font-medium">Total sugars</th><th scope="col" className="py-2 font-medium">Fibre</th><th scope="col" className="py-2 font-medium">Price / 100 g</th></tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {COMPARE_SAMPLE.map((p) => (
                    <tr key={p.name}>
                      <th scope="row" className="py-3 font-medium"><span className="flex items-center gap-2"><GradeBadge grade={p.grade} size="sm" />{p.name}</span></th>
                      <td className="py-3">{p.sugar}</td><td className="py-3">{p.fibre}</td><td className="py-3">{p.price}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <figcaption id="compare-sample-caption" className="mt-3 text-xs text-muted">
              Illustrative sample with fictional products and made-up values. Real comparisons use stored products only.
            </figcaption>
          </figure>
        </div>
      </section>

      {/* Transparency */}
      <section aria-labelledby="evidence-title">
        <div className="mx-auto grid max-w-7xl gap-12 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:px-10 lg:py-24">
          <div>
            <SectionTitle id="evidence-title" eyebrow="Data transparency" title="Every value says where it came from"
              body="Each field carries one of five evidence labels, so you can see how much weight it deserves." />
            <dl className="mt-8 space-y-3">
              {EVIDENCE_ORDER.map((l) => (
                <div key={l} className="flex flex-col gap-1 rounded-2xl border border-line bg-white p-4 sm:flex-row sm:items-start sm:gap-4">
                  <dt className="sm:w-32 sm:shrink-0"><EvidenceBadge label={l} /></dt>
                  <dd className="text-sm text-slate-700">{EVIDENCE_LABELS[l].meaning}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div>
            <SectionTitle eyebrow="Honest limits" title="What the analysis cannot tell you" />
            <ul className="mt-8 space-y-3">
              {LIMITATIONS.map((l) => (
                <li key={l} className="flex gap-3 rounded-2xl border border-line bg-white p-4 text-sm leading-6 text-slate-700">
                  <IconTag className="mt-1 h-4 w-4 shrink-0 text-brand-500" />{l}
                </li>
              ))}
            </ul>
            <Link href="/methodology" className={`${buttonClass.ghost} mt-4 !px-0`}>
              Read the full methodology, sources and licences <IconArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* CTA band */}
      <section aria-labelledby="cta-title" className="px-4 pb-16 sm:px-6 lg:px-10 lg:pb-24">
        <div className="mx-auto flex max-w-7xl flex-col items-start gap-6 rounded-[28px] bg-forest px-6 py-10 text-white sm:px-10 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 id="cta-title" className="text-2xl font-bold">Ready to look past the label?</h2>
            <p className="mt-2 text-sm text-sage/90">Analyze a product, or explore what is already stored.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link href="/analyze" className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-forest transition hover:bg-sage">
              Analyze a product <IconArrowRight className="h-4 w-4" />
            </Link>
            <Link href="/dashboard" className="inline-flex items-center gap-2 rounded-xl border border-white/30 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10">
              Open dashboard
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
