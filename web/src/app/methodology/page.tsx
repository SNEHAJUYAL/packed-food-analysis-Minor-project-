import type { Metadata } from "next";
import { MethodologyView } from "@/components/MethodologyView";

export const metadata: Metadata = { title: "Methodology" };

export default function MethodologyPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-ink sm:text-3xl">Methodology</h1>
        <p className="mt-1 text-sm text-muted">
          How scores are calculated, which sources the benchmarks come from, and what the analysis cannot tell you.
        </p>
      </div>
      <MethodologyView />
    </div>
  );
}
