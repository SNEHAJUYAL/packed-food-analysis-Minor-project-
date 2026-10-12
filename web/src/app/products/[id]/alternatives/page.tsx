import type { Metadata } from "next";
import Link from "next/link";
import { AlternativesPanel } from "@/components/AlternativesPanel";
import { ErrorState } from "@/components/ui";

export const metadata: Metadata = { title: "Alternatives" };

export default async function AlternativesPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) return <ErrorState title="Product not found" message="Product ids are whole numbers." />;
  return (
    <div className="space-y-4">
      <p className="text-sm">
        <Link href={`/products/${id}`} className="text-brand-700 hover:underline">← Back to the product report</Link>
      </p>
      <h1 className="text-2xl font-semibold text-ink">Alternatives for product {id}</h1>
      <AlternativesPanel productId={Number(id)} />
    </div>
  );
}
