"use client";

import { GradeBadge } from "./badges";
import { DimensionChart } from "./DimensionChart";
import { BulletList, Card, InfoTip, ScoreRing, SectionHeading } from "./ui";
import { DIMENSIONS, DIMENSION_INFO } from "@/lib/labels";
import { formatPercent, humanize } from "@/lib/format";
import type { Report } from "@/lib/types";

export function notScoredReason(report: Report): string {
  const notes = report.overall.notes?.filter(Boolean) ?? [];
  if (notes.length) return notes.join(" ");
  const missing = report.overall.missing ?? [];
  if (missing.includes("nutrition") || report.dimensions.nutrition.score === null) {
    return "No overall score is given without a nutrition score (too few nutrients were found).";
  }
  return "The analysis did not produce an overall score for this product.";
}

export function ScoreSummary({ report }: { report: Report }) {
  const { overall, dimensions } = report;
  const rows = overall.rows ?? [];
  const weightOf = (name: string) => rows.find((r) => r.name === name);
  const data = DIMENSIONS.map((d) => ({ name: d, score: dimensions[d]?.score ?? null }));

  return (
    <section aria-labelledby="score-heading" className="space-y-4">
      <Card>
        <SectionHeading
          id="score-heading"
          title="Score"
          subtitle="Consumer decision-support assessment from the listing's own information. Not a medical or clinical score."
        />
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)]">
          <div className="flex items-start gap-4">
            <GradeBadge grade={overall.grade} size="lg" />
            <div>
              {overall.score !== null && overall.score !== undefined ? (
                <>
                  <p className="font-display text-4xl font-bold text-ink">
                    {overall.score}
                    <span className="text-base font-normal text-muted"> / 100</span>
                  </p>
                  <p className="text-sm text-muted">Overall score, grade {overall.grade ?? "not assigned"}</p>
                </>
              ) : (
                <>
                  <p className="text-2xl font-semibold text-ink">Not scored</p>
                  <p className="text-sm text-muted">{notScoredReason(report)}</p>
                </>
              )}
              {overall.coverage !== null && overall.coverage !== undefined ? (
                <p className="mt-2 text-xs text-muted">
                  Weight coverage {formatPercent(overall.coverage)}
                  <InfoTip label="About weight coverage" className="ml-1 align-middle">
                    Share of the methodology weight backed by scored dimensions. Unscored dimensions are left out and the
                    remaining weights renormalised, rather than counted as zero.
                  </InfoTip>
                </p>
              ) : null}
              {overall.score !== null && overall.notes?.length ? <BulletList className="mt-2 text-xs" items={overall.notes} /> : null}
            </div>
          </div>
          <DimensionChart data={data} />
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {DIMENSIONS.map((d) => {
          const dim = dimensions[d];
          if (!dim) return null;
          const row = weightOf(d);
          return (
            <Card key={d} className="!p-5">
              <div className="flex items-start gap-4">
                <ScoreRing
                  score={dim.score}
                  size={60}
                  stroke={6}
                  label={dim.score !== null && dim.score !== undefined ? `${humanize(d)} score ${Math.round(dim.score)} out of 100` : `${humanize(d)} not scored`}
                />
                <div className="flex min-w-0 flex-1 items-start justify-between gap-3">
                <h3 className="flex items-center gap-1.5 font-semibold text-ink">
                  {humanize(d)}
                  <InfoTip label={`About the ${d} dimension`}>{DIMENSION_INFO[d]}</InfoTip>
                </h3>
                <p className="text-right text-sm">
                  {dim.score !== null && dim.score !== undefined ? (
                    <span className="font-semibold text-ink">{Math.round(dim.score)} / 100</span>
                  ) : (
                    <span className="text-muted">Not scored</span>
                  )}
                  {row ? (
                    <span className="block text-xs text-muted">
                      weight {formatPercent(row.weight)}
                      {row.effective_weight !== row.weight ? `, effective ${formatPercent(row.effective_weight)}` : ""}
                    </span>
                  ) : null}
                </p>
                </div>
              </div>
              {dim.explanation?.length ? (
                <details className="group mt-3" open>
                  <summary className="cursor-pointer text-xs font-medium text-forest">How this was calculated</summary>
                  <BulletList className="mt-2" items={dim.explanation} />
                </details>
              ) : null}
            </Card>
          );
        })}
      </div>
    </section>
  );
}
