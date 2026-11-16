import type { Metadata } from "next";
import { AlternativesWorkspace } from "@/components/AlternativesWorkspace";
import { ErrorState, PageHeader } from "@/components/ui";

export const metadata: Metadata = { title: "Alternatives" };

export default async function AlternativesPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) return <ErrorState title="Product not found" message="Product ids are whole numbers." />;
  return (
    <>
      <PageHeader
        eyebrow="Alternatives"
        title="Alternatives for this product"
        description="Stored products in the same category and nutrition basis, ranked by the preference you choose, each with the reason it was suggested."
        crumbs={[
          { label: "Alternatives", href: "/alternatives" },
          { label: `Product ${id}`, href: `/products/${id}` },
          { label: "Alternatives" },
        ]}
      />
      <AlternativesWorkspace productId={Number(id)} />
    </>
  );
}
