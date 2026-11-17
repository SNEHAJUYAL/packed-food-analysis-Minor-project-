"use client";

import Link from "next/link";
import { GradeBadge, SyntheticBadge } from "./badges";
import { IconArrowRight, IconCheck, IconAlert, IconSparkle } from "./icons";
import { Badge, Card, ScoreRing, buttonClass } from "./ui";
import { formatInr } from "@/lib/format";
import type { AskAnswer } from "@/lib/types";

/** The direct answer to a typed product name: grade, quality, ranking, alternatives and prices. */
export function AnswerCard({ answer }: { answer: AskAnswer }) {
  if (answer.kind === "not_found") {
    return (
      <Card>
        <p className="text-sm font-semibold text-ink">{answer.verdict}</p>
        <p className="mt-1 text-xs text-muted">{answer.basis}</p>
        {answer.next_steps?.length ? (
          <ul className="mt-3 flex flex-wrap gap-2 text-sm">
            <li><a className={buttonClass.secondary} href="#url">Paste the product link</a></li>
            <li><a className={buttonClass.secondary} href="#upload">Upload a pack photo</a></li>
            <li><a className={buttonClass.secondary} href="#manual">Enter the label by hand</a></li>
          </ul>
        ) : null}
      </Card>
    );
  }

  if (answer.kind === "ai_estimate" && answer.estimate) {
    const e = answer.estimate;
    return (
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone="amber"><IconSparkle className="h-3.5 w-3.5" /> AI-generated estimate{e.provider ? ` · ${e.provider}` : ""}</Badge>
          <Badge tone="slate">Confidence: {e.confidence}</Badge>
        </div>
        <h3 className="mt-3 text-lg font-semibold text-ink">{e.product}</h3>
        <p className="mt-2 text-sm text-slate-700">{e.quality_summary}</p>
        {e.watch_out_for.length ? (
          <ul className="mt-3 list-disc pl-5 text-sm text-slate-700">{e.watch_out_for.map((w) => <li key={w}>{w}</li>)}</ul>
        ) : null}
        {e.healthier_alternatives.length ? (
          <p className="mt-3 text-sm"><span className="font-medium text-ink">Healthier options to look for:</span> {e.healthier_alternatives.join(", ")}</p>
        ) : null}
        {e.web_sources?.length ? (
          <div className="mt-3 text-xs text-muted">
            <p className="font-medium text-ink">Google Search sources</p>
            <ul className="mt-1 list-disc pl-5">
              {e.web_sources.slice(0, 5).map((source) => (
                <li key={source.url}><a href={source.url} target="_blank" rel="noreferrer" className="underline">{source.title}</a></li>
              ))}
            </ul>
          </div>
        ) : null}
        <p className="mt-3 rounded-xl bg-[#fdf6ec] p-3 text-xs text-[#5c3a10]">{answer.basis}</p>
      </Card>
    );
  }

  const prices = answer.prices;
  return (
    <Card>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
        <ScoreRing score={answer.score ?? null} size={84} caption="score"
                   label={answer.score != null ? `Score ${answer.score} out of 100` : "Score not computed"} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            {answer.grade ? <GradeBadge grade={answer.grade} size="sm" /> : <Badge tone="slate">No grade</Badge>}
            {answer.is_synthetic ? <SyntheticBadge /> : null}
            <Badge tone="green">From the evidence</Badge>
            {answer.found_via === "open_food_facts" ? <Badge tone="teal">Just added from Open Food Facts</Badge> : null}
          </div>
          <h3 className="mt-2 text-lg font-semibold text-ink">{answer.name}</h3>
          <p className="mt-1 text-sm text-slate-700">{answer.verdict}</p>
        </div>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <h4 className="text-sm font-semibold text-forest">What is good</h4>
          {answer.good?.length ? (
            <ul className="mt-2 space-y-1.5 text-sm">
              {answer.good.map((g) => <li key={g} className="flex gap-2"><IconCheck className="mt-0.5 h-4 w-4 shrink-0 text-forest" />{g}</li>)}
            </ul>
          ) : <p className="mt-2 text-sm text-muted">Nothing stands out as good from the known values.</p>}
        </div>
        <div>
          <h4 className="text-sm font-semibold text-[#a3361f]">What to watch</h4>
          {answer.watch?.length ? (
            <ul className="mt-2 space-y-1.5 text-sm">
              {answer.watch.map((w) => <li key={w} className="flex gap-2"><IconAlert className="mt-0.5 h-4 w-4 shrink-0 text-[#b87422]" />{w}</li>)}
            </ul>
          ) : <p className="mt-2 text-sm text-muted">No warning signs in the known values.</p>}
        </div>
      </div>

      {answer.alternatives?.length ? (
        <div className="mt-4">
          <h4 className="text-sm font-semibold text-ink">Healthier alternatives</h4>
          <ul className="mt-2 divide-y divide-line rounded-xl border border-line">
            {answer.alternatives.slice(0, 3).map((a) => (
              <li key={a.product_id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                <Link href={`/products/${a.product_id}`} className="min-w-0 truncate font-medium text-ink hover:underline">{a.name}</Link>
                {a.grade ? <GradeBadge grade={a.grade} size="sm" /> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : answer.alternatives_message ? <p className="mt-4 text-sm text-muted">{answer.alternatives_message}</p> : null}

      {prices?.retailers?.length ? (
        <div className="mt-4">
          <h4 className="text-sm font-semibold text-ink">Prices recorded</h4>
          <ul className="mt-2 flex flex-wrap gap-2 text-sm">
            {prices.retailers.map((r) => (
              <li key={r.retailer} className="rounded-xl bg-slate-50 px-3 py-1.5">
                {r.retailer}: <strong>{formatInr(r.price_inr)}</strong>
                {r.evidence === "unverified" ? <span className="text-xs text-muted"> (unverified)</span> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {answer.ai_estimate ? (
        <div className="mt-4 rounded-xl border border-[#f1d2a8] bg-[#fdf6ec] p-3 text-sm">
          <p className="flex flex-wrap items-center gap-2 font-semibold text-[#5c3a10]">
            <IconSparkle className="h-4 w-4" /> AI-generated estimate{answer.ai_estimate.provider ? ` (${answer.ai_estimate.provider})` : ""}, not from this product&apos;s label
          </p>
          <p className="mt-1 text-slate-700">{answer.ai_estimate.quality_summary}</p>
          {answer.ai_estimate.watch_out_for.length ? <p className="mt-1 text-slate-700"><span className="font-medium">Watch out for:</span> {answer.ai_estimate.watch_out_for.join("; ")}</p> : null}
          {answer.ai_estimate.healthier_alternatives.length ? <p className="mt-1 text-slate-700"><span className="font-medium">Healthier options:</span> {answer.ai_estimate.healthier_alternatives.join(", ")}</p> : null}
          {answer.ai_estimate.web_sources?.length ? (
            <p className="mt-1 text-xs text-muted">
              Sources: {answer.ai_estimate.web_sources.slice(0, 3).map((source) => (
                <a key={source.url} href={source.url} target="_blank" rel="noreferrer" className="mr-2 underline">{source.title}</a>
              ))}
            </p>
          ) : null}
          <p className="mt-1 text-xs text-muted">Unverified and not scored. Upload a pack photo to get a real grade.</p>
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-3">
        <p className="text-xs text-muted">{answer.basis}</p>
        {answer.product_id ? (
          <Link href={`/products/${answer.product_id}`} className={buttonClass.secondary}>
            Full report <IconArrowRight className="h-4 w-4" />
          </Link>
        ) : null}
      </div>
    </Card>
  );
}
