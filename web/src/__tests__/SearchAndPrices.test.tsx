import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProductSearch } from "@/components/ProductSearch";
import { PricePanel } from "@/components/PricePanel";
import { NutrientExtras } from "@/components/NutrientExtras";
import type { PriceSummary, ProductAnalysis } from "@/lib/types";
import { mockFetch, routerPush } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

const PRICES: PriceSummary = {
  product_id: 7, basis: "100 g", is_synthetic: false,
  observations: [
    { id: 1, retailer: "zepto", retailer_label: "Zepto", price_inr: 45, pack_size: 80, pack_unit: "g", price_per_100: 56.25,
      observed_at: "2026-10-07T12:00:00+00:00", source: "Zepto (Delhi), invoice-backed purchase", source_url: null,
      evidence: "invoice", evidence_text: "Paid price on a purchase invoice", is_mrp: false, outlier: false },
    { id: 2, retailer: "zepto", retailer_label: "Zepto", price_inr: 35, pack_size: 80, pack_unit: "g", price_per_100: 43.75,
      observed_at: "2026-11-01T12:00:00+00:00", source: "Zepto (Delhi), invoice-backed purchase", source_url: null,
      evidence: "invoice", evidence_text: "Paid price on a purchase invoice", is_mrp: false, outlier: false },
    { id: 3, retailer: "swiggy instamart", retailer_label: "Swiggy Instamart", price_inr: 38, pack_size: 80, pack_unit: "g",
      price_per_100: 47.5, observed_at: "2026-11-16T12:00:00+00:00", source: "Swiggy Instamart (Delhi), workbook observation, unverified",
      source_url: null, evidence: "unverified", evidence_text: "From a research workbook", is_mrp: false, outlier: false },
  ],
  retailers: [
    { retailer: "zepto", retailer_label: "Zepto", observations: 2, evidence: "invoice", outlier: false, latest_price_inr: 35,
      latest_price_per_100: 43.75, latest_observed_at: "2026-11-01T12:00:00+00:00", pack_size: 80, pack_unit: "g",
      lowest_price_per_100: 43.75, highest_price_per_100: 56.25, change_inr: -10, change_percent: -22.2, trend: "down", source_url: null },
    { retailer: "swiggy instamart", retailer_label: "Swiggy Instamart", observations: 1, evidence: "unverified", outlier: false,
      latest_price_inr: 38, latest_price_per_100: 47.5, latest_observed_at: "2026-11-16T12:00:00+00:00", pack_size: 80, pack_unit: "g",
      lowest_price_per_100: 47.5, highest_price_per_100: 47.5, change_inr: null, change_percent: null, trend: null, source_url: null },
  ],
  cheapest: "Zepto",
  spread: { cheapest: "Zepto", dearest: "Swiggy Instamart", difference_per_100: 3.75, difference_percent: 8.6 },
  vs_category: null, mrp: { price_inr: 50, observed_at: "2026-11-01T12:00:00+00:00", evidence_text: "MRP printed on a purchase invoice" },
  notes: ["Every price is a dated observation with its source."],
  retailer_options: { zepto: "Zepto", blinkit: "Blinkit" },
};

describe("product search", () => {
  it("shows stored and Open Food Facts results and imports one on request", async () => {
    const fetchSpy = mockFetch((url, init) => {
      if (url.includes("/api/search")) {
        return { body: { query: "ragi", notes: [], attribution: "Open Food Facts (ODbL).",
          stored: [{ product_id: 3, name: "Ragi Squares", brand: "Eatrite", category: "breakfast_cereals", overall: 82, grade: "B",
                     status: "partial", price_per_100: null, is_synthetic: false }],
          online: [{ barcode: "8900000000017", name: "Ragi Chips", brand: "Crax", quantity: "80 g", nutriscore_grade: "c",
                     image_url: null, product_id: null, stored: false, source_url: "https://world.openfoodfacts.org/product/1" }] } };
      }
      if (url.includes("/api/products/import-off") && init?.method === "POST") return { body: { product_id: 99 } };
      return undefined;
    });
    render(<ProductSearch />);
    await userEvent.type(screen.getByLabelText("Product name or brand"), "ragi");
    await userEvent.click(screen.getByRole("button", { name: "Search" }));
    expect(await screen.findByText(/Ragi Squares/)).toBeInTheDocument();
    expect(screen.getByText("Ragi Chips")).toBeInTheDocument();
    expect(screen.queryByText("8900000000017")).not.toBeInTheDocument(); // no barcode shown
    await userEvent.click(screen.getByRole("button", { name: "Analyse" }));
    expect(fetchSpy.mock.calls.some(([u]) => String(u).includes("/api/products/import-off"))).toBe(true);
    await vi.waitFor(() => expect(routerPush).toHaveBeenCalledWith("/products/99"));
  });
});

describe("price panel", () => {
  it("shows the cheapest shop, the price change and evidence labels", async () => {
    mockFetch((url) => (url.includes("/prices") ? { body: PRICES } : undefined));
    render(<PricePanel productId={7} />);
    expect(await screen.findByText("Prices across shops")).toBeInTheDocument();
    expect(screen.getAllByText("Zepto").length).toBeGreaterThan(0);
    expect(screen.getByText(/Swiggy Instamart costs 8.6% more than Zepto/)).toBeInTheDocument();
    expect(screen.getByText("Invoice-backed")).toBeInTheDocument();
    expect(screen.getByText("Unverified")).toBeInTheDocument();
    expect(screen.getByText(/▼/)).toBeInTheDocument();
    expect(screen.getByText("Add a price you saw")).toBeInTheDocument();
  });
});

describe("minerals and vitamins", () => {
  it("lists declared micronutrients and says when there are none", () => {
    const base = { report: { product: { nutrition_basis: "per_100g" } } } as unknown as ProductAnalysis;
    const { rerender } = render(<NutrientExtras analysis={{ ...base, extras: { micronutrients: {
      calcium: { label: "Calcium", value: 120, unit: "mg", group: "mineral", source: "Open Food Facts" } } } }} />);
    expect(screen.getByText("Calcium")).toBeInTheDocument();
    expect(screen.getByText("120 mg")).toBeInTheDocument();
    rerender(<NutrientExtras analysis={{ ...base, extras: { micronutrients: {} } }} />);
    expect(screen.getByText(/does not declare any minerals or vitamins/)).toBeInTheDocument();
  });
});
