"use client";

import { Badge, InfoTip } from "./ui";
import {
  ANALYSIS_STATUS,
  EVIDENCE_LABELS,
  EVIDENCE_TONE,
  INGREDIENT_STATUS,
  LIGHT_LABEL,
  claimStatusInfo,
  evidenceMeaning,
} from "@/lib/labels";
import type { AnalysisStatus, EvidenceLabel, Grade } from "@/lib/types";

export function EvidenceBadge({ label, source, note }: { label: string | null | undefined; source?: string | null; note?: string | null }) {
  const l = (label ?? "unknown") as EvidenceLabel;
  const title = EVIDENCE_LABELS[l]?.title ?? l;
  const tone = EVIDENCE_TONE[l] ?? "slate";
  return (
    <span className="inline-flex items-center gap-1">
      <Badge tone={tone}>
        <span className="sr-only">Evidence: </span>
        {title}
      </Badge>
      <InfoTip label={`What "${title}" means`}>
        <span className="block font-medium">{title}</span>
        <span className="block">{evidenceMeaning(l)}</span>
        {source ? <span className="mt-1 block text-slate-300">Source: {source}</span> : null}
        {note ? <span className="mt-1 block text-slate-300">Note: {note}</span> : null}
      </InfoTip>
    </span>
  );
}

export function ClaimStatusBadge({ status }: { status: string }) {
  const info = claimStatusInfo(status);
  return (
    <span className="inline-flex items-center gap-1">
      <Badge tone={info.tone}>{info.short}</Badge>
      <InfoTip label={`About the status "${info.short}"`}>{info.meaning}</InfoTip>
    </span>
  );
}

export function AnalysisStatusBadge({ status }: { status: AnalysisStatus | string }) {
  const info = ANALYSIS_STATUS[status as AnalysisStatus] ?? { title: status, meaning: "", tone: "slate" as const };
  return (
    <span className="inline-flex items-center gap-1">
      <Badge tone={info.tone}>{info.title}</Badge>
      {info.meaning ? <InfoTip label={`About "${info.title}"`}>{info.meaning}</InfoTip> : null}
    </span>
  );
}

export function SyntheticBadge() {
  return (
    <span className="inline-flex items-center gap-1">
      <Badge tone="violet">Synthetic demo record</Badge>
      <InfoTip label="About synthetic demo records">
        This record was created for demonstration. It does not describe a real product on sale.
      </InfoTip>
    </span>
  );
}

const GRADE_CLASSES: Record<Grade, string> = {
  A: "bg-teal-700 text-white",
  B: "bg-teal-500 text-white",
  C: "bg-sky-500 text-white",
  D: "bg-amber-400 text-amber-950",
  E: "bg-orange-300 text-orange-950",
};

export function GradeBadge({ grade, size = "md" }: { grade: Grade | null | undefined; size?: "sm" | "md" | "lg" }) {
  const dims = size === "lg" ? "h-14 w-14 text-2xl" : size === "sm" ? "h-6 w-6 text-xs" : "h-9 w-9 text-base";
  if (!grade) {
    return (
      <span className={`inline-flex items-center justify-center rounded-xl bg-slate-200 font-semibold text-slate-600 ${dims}`} aria-label="No grade">
        –
      </span>
    );
  }
  return (
    <span
      className={`inline-flex items-center justify-center rounded-xl font-bold ${GRADE_CLASSES[grade]} ${dims}`}
      aria-label={`Grade ${grade}`}
    >
      {grade}
    </span>
  );
}

const LIGHT_DOT: Record<string, string> = {
  green: "bg-emerald-500",
  yellow: "bg-amber-400",
  red: "bg-rose-400",
};

export function TrafficLight({ light }: { light: string | null | undefined }) {
  if (!light) return <span className="text-xs text-slate-400">No benchmark</span>;
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-slate-700">
      <span aria-hidden="true" className={`h-2.5 w-2.5 rounded-full ${LIGHT_DOT[light] ?? "bg-slate-300"}`} />
      {LIGHT_LABEL[light] ?? light}
    </span>
  );
}

export function UncertaintyIndicator({ status }: { status: string }) {
  const info = INGREDIENT_STATUS[status] ?? { title: status, meaning: "", uncertain: true };
  if (!info.uncertain) {
    return <Badge tone="teal">{info.title}</Badge>;
  }
  return (
    <span className="inline-flex items-center gap-1">
      <Badge tone="amber">
        <span aria-hidden="true">≈</span> {info.title}
      </Badge>
      <InfoTip label={`About "${info.title}"`}>{info.meaning}</InfoTip>
    </span>
  );
}
