"use client";

import { ClaimStatusBadge } from "./badges";
import { BulletList, Card, EmptyState, ExternalLink, SectionHeading } from "./ui";
import { safeHref } from "@/lib/format";
import { CLAIM_STATUSES } from "@/lib/labels";
import type { ClaimResult, Report } from "@/lib/types";

function ClaimCard({ claim }: { claim: ClaimResult }) {
  const href = safeHref(claim.source_url);
  const missing = claim.missing_information ?? [];
  return (
    <li className="rounded-xl border border-line p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted">Claim as printed</p>
          <p className="text-base font-semibold text-ink">“{claim.matched_text || claim.claim}”</p>
        </div>
        <ClaimStatusBadge status={claim.status} />
      </div>

      <dl className="mt-3 space-y-3 text-sm">
        <div>
          <dt className="font-medium text-ink">Rule checked</dt>
          <dd className="text-slate-700">
            {claim.claim}
            {claim.rule ? <span className="mt-0.5 block text-xs text-slate-600">{claim.rule}</span> : null}
            {claim.rule_status ? (
              <span className="mt-0.5 block text-xs text-muted">Rule status: {claim.rule_status.replace(/_/g, " ")}</span>
            ) : null}
            {href ? (
              <span className="mt-1 block text-xs">
                <ExternalLink href={href}>Regulation text</ExternalLink>
              </span>
            ) : null}
          </dd>
        </div>
        {claim.facts && claim.facts.length ? (
          <div>
            <dt className="font-medium text-ink">Facts used</dt>
            <dd>
              <BulletList items={claim.facts} />
            </dd>
          </div>
        ) : null}
        {claim.reason ? (
          <div>
            <dt className="font-medium text-ink">Explanation</dt>
            <dd className="text-slate-700">{claim.reason}</dd>
          </div>
        ) : null}
        {missing.length ? (
          <div>
            <dt className="font-medium text-ink">Missing information</dt>
            <dd>
              <BulletList items={missing} />
            </dd>
          </div>
        ) : null}
      </dl>
    </li>
  );
}

export function ClaimPanel({ report }: { report: Report }) {
  const claims = report.dimensions.claims?.claims ?? [];
  const raw = report.product.claims_raw ?? [];
  return (
    <Card>
      <section aria-labelledby="claims-heading">
        <SectionHeading
          id="claims-heading"
          title="Claims check"
          subtitle="Printed nutrition claims compared with the regulatory conditions we can check from the listing. Statuses are prompts for review, not legal findings."
        />
        {claims.length === 0 ? (
          <EmptyState title="No nutrition claims were matched on this listing.">
            {raw.length ? <p>Text checked: {raw.map((r) => `“${r}”`).join(", ")}</p> : null}
          </EmptyState>
        ) : (
          <ul className="space-y-3">
            {claims.map((c, i) => (
              <ClaimCard key={`${c.claim_id ?? c.claim}-${i}`} claim={c} />
            ))}
          </ul>
        )}
        <details className="mt-4 text-sm">
          <summary className="cursor-pointer text-muted">What the four statuses mean</summary>
          <dl className="mt-2 space-y-2">
            {Object.entries(CLAIM_STATUSES).map(([k, v]) => (
              <div key={k}>
                <dt className="font-medium text-ink">{v.short}</dt>
                <dd className="text-slate-700">{v.meaning}</dd>
              </div>
            ))}
          </dl>
        </details>
      </section>
    </Card>
  );
}
