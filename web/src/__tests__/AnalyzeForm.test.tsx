import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AnalyzeForm, validateUrl } from "@/components/AnalyzeForm";
import { makeAnalysis } from "@/__fixtures__";
import { mockFetch, routerPush } from "./helpers";

beforeEach(() => routerPush.mockClear());
afterEach(() => vi.unstubAllGlobals());

const categories = { categories: [{ id: "breakfast_cereals", label: "Breakfast cereals", product_count: 8 }] };

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
});
