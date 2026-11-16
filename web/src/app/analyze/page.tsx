import type { Metadata } from "next";
import { Suspense } from "react";
import { AnalyzeWorkspace } from "@/components/AnalyzeWorkspace";
import { LoadingState, PageHeader } from "@/components/ui";

export const metadata: Metadata = { title: "Analyze a product" };

export default function AnalyzePage() {
  return (
    <>
      <PageHeader
        eyebrow="Analyze"
        title="Analyze a packaged food product"
        description="Give us a product page, a pack photo or the label details. We extract the evidence, normalise it per 100 g/ml, and explain every score."
        crumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Analyze product" }]}
      />
      <Suspense fallback={<LoadingState lines={2} />}>
        <AnalyzeWorkspace />
      </Suspense>
    </>
  );
}
