import type { Metadata } from "next";
import { MethodologyOverview } from "@/components/MethodologyOverview";
import { MethodologyView } from "@/components/MethodologyView";
import { PageHeader } from "@/components/ui";

export const metadata: Metadata = { title: "Methodology" };

export default function MethodologyPage() {
  return (
    <>
      <PageHeader
        eyebrow="Methodology"
        title="How the analysis works"
        description="How products are acquired, normalised and scored, which sources the benchmarks come from, and what the analysis cannot tell you. Scores are informational decision-support indicators, not medical assessments."
        crumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Methodology" }]}
      />
      <MethodologyOverview />
      <h2 className="mb-4 mt-12 text-xl font-bold text-ink">Live scoring configuration</h2>
      <MethodologyView />
    </>
  );
}
