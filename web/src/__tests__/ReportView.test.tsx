import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { ReportView } from "@/components/ReportView";
import { alternatives, makeAnalysis, makePartialAnalysis, makeUnscoredAnalysis } from "@/__fixtures__";
import { mockFetch } from "./helpers";

beforeEach(() => {
  mockFetch((url) => (url.includes("/alternatives") ? { body: alternatives } : undefined));
});
afterEach(() => vi.unstubAllGlobals());

describe("ReportView (current backend output)", () => {
  it("shows identity, synthetic badge, price per 100 g and source link", () => {
    render(<ReportView analysis={makeAnalysis()} />);
    expect(screen.getByRole("heading", { level: 1, name: "Choco Crunch Whole Grain Cereal - High Protein" })).toBeInTheDocument();
    expect(screen.getAllByText("Synthetic demo record").length).toBeGreaterThan(0);
    expect(screen.getByText("₹48.00")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /brand\.example/ })).toHaveAttribute("href", "https://brand.example/cereal");
    expect(screen.getByText("12 Oct 2026, 09:02 UTC")).toBeInTheDocument();
  });

  it("shows overall score, grade and dimension explanations", () => {
    render(<ReportView analysis={makeAnalysis()} />);
    expect(screen.getAllByLabelText("Grade C").length).toBeGreaterThan(0);
    expect(screen.getByText("Overall score, grade C")).toBeInTheDocument();
    expect(screen.getByText("Whole grain is the first ingredient: +10.")).toBeInTheDocument();
    expect(screen.getByText("No comparison set yet, so value for money is not scored.")).toBeInTheDocument();
  });

  it("renders missing nutrients as not found, never zero, with evidence badges", () => {
    render(<ReportView analysis={makeAnalysis()} />);
    const table = screen.getByRole("table", { name: /Nutrition per 100 g/ });
    const added = within(table).getByRole("rowheader", { name: /Added sugars/ }).closest("tr")!;
    expect(within(added).getByText("Not found")).toBeInTheDocument();
    expect(within(added).getAllByText("Unknown").length).toBeGreaterThan(0);
    const sugars = within(table).getByRole("rowheader", { name: /Total sugars/ }).closest("tr")!;
    expect(within(sugars).getByText("28 g")).toBeInTheDocument();
    expect(within(sugars).getByText("Red")).toBeInTheDocument();
    expect(within(sugars).getAllByText("Declared").length).toBeGreaterThan(0);
  });

  it("uses neutral claim language and shows the regulation and facts", () => {
    const { container } = render(<ReportView analysis={makeAnalysis()} />);
    expect(screen.getByText("“High Protein”")).toBeInTheDocument();
    expect(screen.getAllByText("Potential inconsistency for review").length).toBeGreaterThan(0);
    expect(screen.getByText(/1.71 g per 100 kcal/)).toBeInTheDocument();
    expect(screen.getByText(/FSS \(Advertising and Claims\) Regulations, 2018/)).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/violat|illegal|fraud|dangerous/i);
  });

  it("does not invent ingredient percentages when the API gives none", () => {
    render(<ReportView analysis={makeAnalysis()} />);
    const list = screen.getByRole("list", { name: "Ingredients in label order" });
    expect(within(list).queryByText(/declared\)/)).not.toBeInTheDocument();
    // Parser annotations like "62%" are not listed as separate ingredients.
    expect(within(list).queryByText("62%")).not.toBeInTheDocument();
    expect(within(list).getByText("Whole Grain Wheat (62%)")).toBeInTheDocument();
  });

  it("shows the disclaimer", () => {
    render(<ReportView analysis={makeAnalysis()} />);
    expect(screen.getByText(/not a medical or clinical score\. Methodology v0\.1\.0/)).toBeInTheDocument();
  });
});

describe("ReportView (contract fields, partial data)", () => {
  it("shows the partial-data banner, conflicts and missing price", () => {
    render(<ReportView analysis={makePartialAnalysis()} />);
    expect(screen.getAllByText("Partial data").length).toBeGreaterThan(0);
    expect(screen.getAllByText("total_sugars: json-ld says 28, html-table says 30").length).toBe(1);
    expect(screen.getByText("Not available (needs price and pack size)")).toBeInTheDocument();
    expect(screen.queryByText("Synthetic demo record")).not.toBeInTheDocument();
  });

  it("shows original printed values", () => {
    render(<ReportView analysis={makePartialAnalysis()} />);
    expect(screen.getByRole("columnheader", { name: "As printed" })).toBeInTheDocument();
    expect(screen.getByText("8.4 g")).toBeInTheDocument();
    expect(screen.getByText("per 30 g serving")).toBeInTheDocument();
  });

  it("shows declared percent, functional category and uncertainty indicators", () => {
    render(<ReportView analysis={makePartialAnalysis()} />);
    expect(screen.getByText("(62% declared)")).toBeInTheDocument();
    expect(screen.getByText("Cereal")).toBeInTheDocument();
    expect(screen.getByText("Whole grain cereal declared as the first ingredient.")).toBeInTheDocument();
    expect(screen.getByText(/Fuzzy match/)).toBeInTheDocument();
    expect(screen.getByText(/^\s*Uncertain$/)).toBeInTheDocument();
  });

  it("shows claim missing information and a regulation link", () => {
    render(<ReportView analysis={makePartialAnalysis()} />);
    expect(screen.getByText("serving size")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Regulation text/ })).toHaveAttribute("href", expect.stringContaining("fssai.gov.in"));
    expect(screen.getAllByText("Consistent with available evidence").length).toBeGreaterThan(0);
  });
});

describe("ReportView (not scored)", () => {
  it("says not scored with a reason instead of a grade", () => {
    render(<ReportView analysis={makeUnscoredAnalysis()} showAlternatives={false} />);
    expect(screen.getByText("Not scored", { selector: "p" })).toBeInTheDocument();
    expect(screen.getByText(/No overall score is given without a nutrition score/)).toBeInTheDocument();
    expect(screen.getAllByText("Insufficient data").length).toBeGreaterThan(0);
  });
});
