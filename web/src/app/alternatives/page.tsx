import type { Metadata } from "next";
import { ProductPicker } from "@/components/ProductPicker";
import { PageHeader } from "@/components/ui";

export const metadata: Metadata = { title: "Alternatives" };

export default function AlternativesHubPage() {
  return (
    <>
      <PageHeader
        eyebrow="Alternatives"
        title="Find better alternatives"
        description="Choose a stored product to see comparable products ranked by nutrition, unit price, transparency or a balanced score. Suggestions come only from products already stored, and say why each was chosen."
        crumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Alternatives" }]}
      />
      <ProductPicker hrefTemplate="/products/{id}/alternatives" actionLabel="See alternatives" />
    </>
  );
}
