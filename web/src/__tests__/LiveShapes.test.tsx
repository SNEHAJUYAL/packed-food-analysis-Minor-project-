// Responses captured from the running backend on 12 Oct 2026 (synthetic and local test pages).
import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReportView } from "@/components/ReportView";
import { CompareResultView } from "@/components/CompareView";
import { MethodologyContent } from "@/components/MethodologyView";
import partial from "@/__fixtures__/live_product_partial.json";
import insufficient from "@/__fixtures__/live_product_insufficient.json";
import liveMethodology from "@/__fixtures__/live_methodology.json";
import liveCompare from "@/__fixtures__/live_compare.json";
import liveAlternatives from "@/__fixtures__/live_alternatives.json";
import type { CompareResult, Methodology, ProductAnalysis } from "@/lib/types";
import { mockFetch } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

describe("live backend shapes", () => {
  it("renders an insufficient-data URL record without a name, nutrition basis or ingredients", async () => {
    mockFetch(() => ({
      body: { ...liveAlternatives, alternatives: [], message: "The category or nutrition basis of this product is unknown, so comparable products cannot be selected." },
    }));
    render(<ReportView analysis={insufficient as unknown as ProductAnalysis} />);
    expect(screen.getByRole("heading", { level: 1, name: "Unnamed product" })).toBeInTheDocument();
    expect(screen.getByText("Overall score not computed: nutrition could not be scored. Insufficient data: the report shows what is known, but no overall grade.")).toBeInTheDocument();
    expect(screen.getByText("No ingredient list was found on this listing.")).toBeInTheDocument();
    expect(screen.getByText(/No stated nutrition basis was found/)).toBeInTheDocument();
    expect(await screen.findByText(/comparable products cannot be selected/)).toBeInTheDocument();
  });

  it("renders a partial URL record with compound ingredients and printed-only values", () => {
    mockFetch(() => ({ body: liveAlternatives }));
    render(<ReportView analysis={partial as unknown as ProductAnalysis} />);
    expect(screen.getByText("Refined Wheat Flour")).toBeInTheDocument();
    expect(screen.getByText("Salt", { selector: "th" })).toBeInTheDocument();
    expect(screen.getAllByText("per 70 g").length).toBeGreaterThan(0);
    expect(screen.getByText("No nutrition claims were matched on this listing.")).toBeInTheDocument();
  });

  it("renders a live comparison with rounded scores", () => {
    render(<CompareResultView data={liveCompare as unknown as CompareResult} />);
    expect(screen.getByText(/costs ₹25.20 per 100 g/)).toBeInTheDocument();
    expect(screen.queryByText(/11\.47/)).not.toBeInTheDocument();
  });

  it("renders the live methodology including missing-data and freshness text", () => {
    render(<MethodologyContent m={liveMethodology as unknown as Methodology} />);
    expect(screen.getByText("Missing values stay unknown and are never treated as zero.")).toBeInTheDocument();
    expect(screen.getByText(/prices are stored as dated observations/)).toBeInTheDocument();
    expect(screen.getAllByText(/Open Database License/).length).toBeGreaterThan(0);
  });
});
