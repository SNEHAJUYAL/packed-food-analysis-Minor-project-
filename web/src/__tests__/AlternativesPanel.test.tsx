import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AlternativesPanel } from "@/components/AlternativesPanel";
import { alternatives, noAlternatives } from "@/__fixtures__";
import { mockFetch } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

describe("AlternativesPanel", () => {
  it("lists ranked alternatives with rationale, attributes and picks", async () => {
    mockFetch(() => ({ body: alternatives }));
    render(<AlternativesPanel productId={12} />);
    expect(await screen.findByText(/Scores 78 against 69/)).toBeInTheDocument();
    expect(screen.getByText("whole grain first")).toBeInTheDocument();
    expect(screen.getByText("Best match for this preference")).toBeInTheDocument();
    expect(screen.getByText("Highest balanced score among eligible products.")).toBeInTheDocument();
    expect(screen.getByText("No pick")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Compare side by side" })).toHaveAttribute("href", "/compare?ids=12,3");
  });

  it("re-queries with the chosen preference and shows the API message when nothing fits", async () => {
    const spy = mockFetch((url) => ({ body: url.includes("preference=nutrition") ? noAlternatives : alternatives }));
    render(<AlternativesPanel productId={12} />);
    await screen.findByText(/Scores 78 against 69/);
    await userEvent.click(screen.getByRole("radio", { name: "Nutrition" }));
    expect(await screen.findByText("No stored product in this category scores higher on nutrition.")).toBeInTheDocument();
    expect(spy.mock.calls.some(([u]) => String(u).includes("preference=nutrition"))).toBe(true);
    expect(screen.queryByText(/Scores 78 against 69/)).not.toBeInTheDocument();
  });

  it("shows the API error message", async () => {
    mockFetch(() => ({ status: 503, body: { detail: { code: "database_unavailable", message: "The product database is not reachable right now." } } }));
    render(<AlternativesPanel productId={12} />);
    expect(await screen.findByText("The product database is not reachable right now.")).toBeInTheDocument();
  });
});
