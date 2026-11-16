import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AnalyzeForm, validateUrl } from "@/components/AnalyzeForm";
import { makeAnalysis } from "@/__fixtures__";
import { mockFetch, routerPush } from "./helpers";
import type { ProductURLCandidateResult } from "@/lib/types";

beforeEach(() => routerPush.mockClear());
afterEach(() => vi.unstubAllGlobals());

const categories = { categories: [{ id: "breakfast_cereals", label: "Breakfast cereals", product_count: 8 }] };
const candidate: ProductURLCandidateResult = {
  status: "candidate",
  submitted_url: "https://world.openfoodfacts.org/product/SYN-FIXTURE-001",
  candidate: {
    candidate_id: "urlcand_synthetic",
    status: "candidate",
    source_id: "open_food_facts",
    source_attribution: "Open Food Facts",
    license: "ODbL-1.0",
    submitted_url: "https://world.openfoodfacts.org/product/SYN-FIXTURE-001",
    final_url: "https://world.openfoodfacts.org/product/SYN-FIXTURE-001",
    extracted_at: "2026-11-16T00:00:00Z",
    normalized_product: {
      product_id: "urlcand_synthetic",
      name: { value: "Synthetic Grain Squares", label: "declared", source: "json-ld" },
      brand: { value: "Example Brand", label: "declared", source: "json-ld" },
      category: { value: "breakfast_cereals", label: "interpreted", source: "rules" },
      variant: { value: null, label: "unknown" },
      pack_size: { value: 250, label: "declared" },
      pack_unit: { value: "g", label: "declared" },
      price_inr: { value: null, label: "unknown" },
      ingredients_raw: { value: null, label: "unknown" },
      nutrition_basis: null,
      nutrition: {},
    },
    field_evidence: [{
      field_path: "name",
      original_value: "Synthetic Grain Squares",
      normalized_value: "Synthetic Grain Squares",
      validation_status: "candidate",
      provenance: {
        source_id: "open_food_facts",
        source_url: "https://world.openfoodfacts.org/product/SYN-FIXTURE-001",
        extraction_method: "json-ld",
        collected_at: "2026-11-16T00:00:00Z",
        raw_value: "Synthetic Grain Squares",
      },
    }],
    images: [],
    issues: [{ code: "missing_ingredients", field_path: "ingredients_text", message: "No ingredients were found.", severity: "warning" }],
  },
};

describe("validateUrl", () => {
  it("accepts http(s) and rejects other input", () => {
    expect(validateUrl("https://brand.example/p")).toBeNull();
    expect(validateUrl("")).toMatch(/Enter/);
    expect(validateUrl("not a url")).toMatch(/web address/);
    expect(validateUrl("ftp://x.example/a")).toMatch(/http/);
  });
});

describe("AnalyzeForm", () => {
  it("validates before calling the API", async () => {
    const spy = mockFetch((url) => (url.includes("categories") ? { body: categories } : undefined));
    render(<AnalyzeForm />);
    await userEvent.type(screen.getByLabelText("Product page URL"), "javascript:alert(1)");
    await userEvent.click(screen.getByRole("button", { name: "Analyse" }));
    expect(screen.getByText("Only http and https addresses can be analysed.")).toBeInTheDocument();
    expect(spy.mock.calls.some(([u]) => String(u).includes("analyze-url"))).toBe(false);
  });

  it("shows progress steps and redirects to the product report", async () => {
    let body: string | undefined;
    mockFetch((url, init) => {
      if (url.includes("categories")) return { body: categories };
      if (url.endsWith("/api/analyze-url")) {
        body = init?.body as string;
        return { body: makeAnalysis() };
      }
      return undefined;
    });
    render(<AnalyzeForm />);
    await screen.findByRole("option", { name: "Breakfast cereals" });
    await userEvent.type(screen.getByLabelText("Product page URL"), "https://brand.example/cereal");
    await userEvent.click(screen.getByRole("button", { name: "Analyse" }));
    expect(await screen.findByRole("list", { name: "Analysis progress" })).toBeInTheDocument();
    expect(screen.getByText("Reading structured data")).toBeInTheDocument();
    await vi.waitFor(() => expect(routerPush).toHaveBeenCalledWith("/products/12"));
    expect(JSON.parse(body!)).toEqual({ url: "https://brand.example/cereal", category: null, refresh: false });
  });

  it("shows the API error message (e.g. blocked destination)", async () => {
    mockFetch((url) =>
      url.includes("categories")
        ? { body: categories }
        : { status: 400, body: { detail: { code: "blocked_destination", message: "That address points to a private or local network and cannot be fetched." } } },
    );
    render(<AnalyzeForm />);
    await userEvent.type(screen.getByLabelText("Product page URL"), "http://127.0.0.1/admin");
    await userEvent.click(screen.getByRole("button", { name: "Analyse" }));
    expect(await screen.findByText("That address points to a private or local network and cannot be fetched.")).toBeInTheDocument();
    expect(screen.getByText(/stopped/)).toBeInTheDocument();
    expect(routerPush).not.toHaveBeenCalled();
  });

  it("previews an unverified candidate without saving or navigating", async () => {
    const spy = mockFetch((url) => {
      if (url.includes("categories")) return { body: categories };
      if (url.endsWith("/api/product-candidates/from-url")) return { body: candidate };
      return undefined;
    });
    render(<AnalyzeForm />);
    await userEvent.type(screen.getByLabelText("Product page URL"), "https://world.openfoodfacts.org/product/SYN-FIXTURE-001");
    await userEvent.click(screen.getByRole("button", { name: "Preview candidate (not saved)" }));
    expect(await screen.findByText("UNVERIFIED")).toBeInTheDocument();
    expect(screen.getByText("Synthetic Grain Squares")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ingredients" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Nutrition" })).toBeInTheDocument();
    expect(screen.getByText(/Not found on this page/)).toBeInTheDocument();
    await userEvent.click(screen.getByText("Source and field provenance"));
    expect(await screen.findByText(/Original: "Synthetic Grain Squares"/)).toBeInTheDocument();
    expect(spy.mock.calls.some(([url]) => String(url).endsWith("/api/product-candidates/from-url"))).toBe(true);
    expect(spy.mock.calls.some(([url]) => String(url).endsWith("/api/analyze-url"))).toBe(false);
    expect(routerPush).not.toHaveBeenCalled();
  });

  it("explains when candidate extraction is blocked by source policy", async () => {
    mockFetch((url) => url.includes("categories")
      ? { body: categories }
      : { status: 403, body: { status: "blocked", error_code: "unsupported_source", message: "Source is unauthorized." } });
    render(<AnalyzeForm />);
    await userEvent.type(screen.getByLabelText("Product page URL"), "https://retailer.example/product/1");
    await userEvent.click(screen.getByRole("button", { name: "Preview candidate (not saved)" }));
    expect(await screen.findByText(/This retailer is not currently supported for automated product extraction/)).toBeInTheDocument();
    expect(routerPush).not.toHaveBeenCalled();
  });

  it("shows robots denial as an access restriction and offers offline fallback", async () => {
    mockFetch((url) => url.includes("categories")
      ? { body: categories }
      : { status: 403, body: { detail: { code: "robots_disallowed", message: "robots test" } } });
    render(<AnalyzeForm />);
    await userEvent.type(screen.getByLabelText("Product page URL"), "https://world.openfoodfacts.org/product/123");
    await userEvent.click(screen.getByRole("button", { name: "Analyse" }));
    expect(await screen.findByText(/This source does not permit automated access to this page/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Upload saved product page" })).toHaveAttribute("href", "#saved-page-upload");
    expect(screen.getByRole("link", { name: "Upload product packaging images" })).toHaveAttribute("href", "#packaging-image-upload");
    expect(screen.getByRole("link", { name: "Enter product details manually" })).toHaveAttribute("href", "#manual-entry-form");
    expect(screen.queryByText(/retailer is not currently supported/i)).not.toBeInTheDocument();
  });
});
