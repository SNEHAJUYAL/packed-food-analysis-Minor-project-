import type { Metadata } from "next";
import { Suspense } from "react";
import { CompareClient } from "@/components/CompareClient";
import { LoadingState, PageHeader } from "@/components/ui";

export const metadata: Metadata = { title: "Compare products" };

export default function ComparePage() {
  return (
    <>
      <PageHeader
        eyebrow="Compare"
        title="Compare products"
        description="Stored products from one category, side by side on a per 100 g/ml basis, with the reasons behind each pick."
        crumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Compare products" }]}
      />
      <Suspense fallback={<LoadingState />}>
        <CompareClient />
      </Suspense>
    </>
  );
}
