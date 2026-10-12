import type { Metadata } from "next";
import { ProductsBrowser } from "@/components/ProductsBrowser";

export const metadata: Metadata = { title: "Stored products" };

export default function ProductsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-ink sm:text-3xl">Stored products</h1>
        <p className="mt-1 text-sm text-muted">
          Every product analysed so far. Synthetic demo records are labelled. Select two to six from one category to compare.
        </p>
      </div>
      <ProductsBrowser />
    </div>
  );
}
