import type { Metadata } from "next";
import { Suspense } from "react";
import { CompareClient } from "@/components/CompareClient";
import { LoadingState } from "@/components/ui";

export const metadata: Metadata = { title: "Compare" };

export default function ComparePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-ink sm:text-3xl">Compare products</h1>
        <p className="mt-1 text-sm text-muted">
          Stored products from one category, side by side on a per 100 g/ml basis, with the reasons behind each pick.
        </p>
      </div>
      <Suspense fallback={<LoadingState />}>
        <CompareClient />
      </Suspense>
    </div>
  );
}
