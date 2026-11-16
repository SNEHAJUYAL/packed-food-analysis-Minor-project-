import type { Metadata } from "next";
import Link from "next/link";
import { ProductsBrowser } from "@/components/ProductsBrowser";
import { PageHeader, buttonClass } from "@/components/ui";

export const metadata: Metadata = { title: "Product explorer" };

export default function ProductsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Explore"
        title="Product explorer"
        description="Every product analysed so far. Synthetic demo records are labelled. Select two to six from one category to compare."
        crumbs={[{ label: "Dashboard", href: "/dashboard" }, { label: "Product explorer" }]}
        actions={<Link href="/analyze" className={buttonClass.primary}>Analyze a product</Link>}
      />
      <ProductsBrowser />
    </>
  );
}
