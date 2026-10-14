import type { Metadata } from "next";
import { ProductReport } from "@/components/ProductReport";

export const metadata: Metadata = { title: "Product report" };

export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ProductReport id={id} />;
}
