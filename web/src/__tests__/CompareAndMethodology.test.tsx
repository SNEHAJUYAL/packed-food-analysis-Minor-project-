import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { CompareResultView, CompareView } from "@/components/CompareView";
import { MethodologyContent } from "@/components/MethodologyView";
import { ProductsBrowser } from "@/components/ProductsBrowser";
import { compareResult, methodology, productList } from "@/__fixtures__";
import { mockFetch } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

describe("CompareResultView", () => {
  it("shows picks with reasons, a per-100 table and ingredient differences", () => {
    render(<CompareResultView data={compareResult} />);
    expect(screen.getByText("Lowest price per 100")).toBeInTheDocument();
    expect(screen.getByText("₹39.50 vs ₹48.00 per 100 g.")).toBeInTheDocument();
    const table = screen.getByRole("table", { name: "Product comparison table" });
    const sugars = within(table).getByRole("rowheader", { name: "Added sugars" }).closest("tr")!;
    expect(within(sugars).getByText("Not found")).toBeInTheDocument();
    expect(within(sugars).getByText("0 g")).toBeInTheDocument();
    expect(within(table).getByText("90%")).toBeInTheDocument();
    expect(screen.getByText("Only in Choco Crunch Whole Grain Cereal - High Protein")).toBeInTheDocument();
    expect(screen.getByText("Rationale")).toBeInTheDocument();
  });

  it("shows the picker when fewer than two ids are given", async () => {
    mockFetch((url) => (url.includes("categories") ? { body: { categories: [] } } : { body: productList }));
    render(<CompareView ids={[]} />);
    expect(screen.getByRole("button", { name: /Compare/ })).toBeDisabled();
    expect(await screen.findByText("Plain Oat Flakes")).toBeInTheDocument();
  });

  it("shows the API message when products cannot be compared", async () => {
    mockFetch(() => ({ status: 422, body: { detail: { code: "validation_error", message: "Products must share one category." } } }));
    render(<CompareView ids={[1, 2]} />);
    expect(await screen.findByText("Products must share one category.")).toBeInTheDocument();
  });
});

describe("MethodologyContent", () => {
  it("renders weights, grade bands, thresholds with sources and claim rules with clauses", () => {
    render(<MethodologyContent m={methodology} />);
    expect(screen.getByText("40%")).toBeInTheDocument();
    expect(screen.getByText("85 and above")).toBeInTheDocument();
    expect(screen.getByText("70 to 84")).toBeInTheDocument();
    expect(screen.getByText(/FSSAI Schedule I Sl. 4/)).toBeInTheDocument();
    expect(screen.getByText("Schedule I, Sl. No. 10 (Sugars: Low), reg. 5(3)")).toBeInTheDocument();
    expect(screen.getAllByText(/ODbL/).length).toBeGreaterThan(0);
    for (const l of ["Declared", "Derived", "Interpreted", "Verified", "Unknown"]) {
      expect(screen.getAllByText(l).length).toBeGreaterThan(0);
    }
    // Claim statuses fall back to built-in meanings when the API sends none.
    expect(screen.getAllByText("Potential inconsistency for review").length).toBeGreaterThan(0);
  });
});

describe("ProductsBrowser", () => {
  it("lists stored products with status and synthetic labels", async () => {
    mockFetch((url) => (url.includes("categories") ? { body: { categories: [] } } : { body: productList }));
    render(<ProductsBrowser />);
    expect(await screen.findByText("Honey Loops")).toBeInTheDocument();
    expect(screen.getByText("Showing 3 of 3")).toBeInTheDocument();
    expect(screen.getAllByText("Synthetic demo record").length).toBe(2);
    expect(screen.getByText("Insufficient data")).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    mockFetch((url) => (url.includes("categories") ? { body: { categories: [] } } : { body: { products: [], total: 0 } }));
    render(<ProductsBrowser />);
    expect(await screen.findByText("No stored products match.")).toBeInTheDocument();
  });
});
