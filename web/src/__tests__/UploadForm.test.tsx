import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UploadForm, checkFile } from "@/components/UploadForm";
import { AlternativesPanel } from "@/components/AlternativesPanel";
import { alternatives, makeAnalysis } from "@/__fixtures__";
import { mockFetch, routerPush } from "./helpers";

beforeEach(() => routerPush.mockClear());
afterEach(() => vi.unstubAllGlobals());

const png = () => new File([new Uint8Array([137, 80, 78, 71])], "okra.png", { type: "image/png" });

describe("checkFile", () => {
  it("accepts images and saved pages, rejects others", () => {
    expect(checkFile(png())).toBeNull();
    expect(checkFile(new File(["<html>"], "page.html", { type: "text/html" }))).toBeNull();
    expect(checkFile(null)).toMatch(/Choose/);
    expect(checkFile(new File(["%PDF"], "label.pdf", { type: "application/pdf" }))).toMatch(/JPEG/);
    expect(checkFile(new File([new Uint8Array(9 * 1024 * 1024)], "big.jpg", { type: "image/jpeg" }))).toMatch(/8 MB/);
  });
});

describe("UploadForm", () => {
  it("sends the file and shop as multipart and opens the report", async () => {
    let sent: FormData | undefined;
    let headers: Record<string, string> | undefined;
    mockFetch((url, init) => {
      if (url.endsWith("/api/analyze-upload")) {
        sent = init?.body as FormData;
        headers = init?.headers as Record<string, string>;
        return { body: makeAnalysis() };
      }
      return undefined;
    });
    render(<UploadForm />);
    await userEvent.upload(screen.getByLabelText("Saved product page or packaging image"), png());
    await userEvent.selectOptions(screen.getByLabelText("Shop"), "blinkit.com");
    await userEvent.type(screen.getByLabelText("Product name (optional)"), "Troovy Moong Dal Chips");
    await userEvent.click(screen.getByRole("button", { name: "Upload and analyse" }));
    await waitFor(() => expect(routerPush).toHaveBeenCalled());
    expect(sent).toBeInstanceOf(FormData);
    expect(sent?.get("site")).toBe("blinkit.com");
    expect(sent?.get("name")).toBe("Troovy Moong Dal Chips");
    expect((sent?.get("file") as File).name).toBe("okra.png");
    expect(headers?.["Content-Type"]).toBeUndefined();
  });

  it("shows the API's message when photos cannot be read", async () => {
    mockFetch(() => ({ status: 503, body: { detail: { code: "photo_reader_missing", message: "Reading photos needs the free Tesseract OCR program (on a Mac: brew install tesseract, then restart the API)." } } }));
    render(<UploadForm />);
    await userEvent.upload(screen.getByLabelText("Saved product page or packaging image"), png());
    await userEvent.click(screen.getByRole("button", { name: "Upload and analyse" }));
    expect(await screen.findByText(/brew install tesseract/)).toBeInTheDocument();
    expect(routerPush).not.toHaveBeenCalled();
  });

  it("submits manual product details as explicitly unverified input", async () => {
    let request: Record<string, unknown> | undefined;
    mockFetch((url, init) => {
      if (url.includes("categories")) return { body: { categories: [] } };
      if (url.endsWith("/api/analyze-manual")) {
        request = JSON.parse(init?.body as string) as Record<string, unknown>;
        return { body: makeAnalysis({ product_id: 21 }) };
      }
      return undefined;
    });
    render(<UploadForm />);
    await userEvent.type(screen.getByLabelText("Manual product name"), "Synthetic Manual Cereal");
    await userEvent.type(screen.getByLabelText("Manual brand"), "Example Foods");
    await userEvent.type(screen.getByLabelText("Manual pack size"), "300");
    await userEvent.type(screen.getByLabelText("Manual ingredients"), "Oats, sugar");
    await userEvent.selectOptions(screen.getByLabelText("Manual nutrition basis"), "per_100g");
    await userEvent.type(screen.getByLabelText("Manual nutrition values"), "energy: 400 kcal{enter}protein: 10 g");
    await userEvent.click(screen.getByRole("button", { name: "Save and analyse manual details" }));
    await waitFor(() => expect(routerPush).toHaveBeenCalledWith("/products/21"));
    expect(request).toMatchObject({
      name: "Synthetic Manual Cereal", brand: "Example Foods", pack_size: 300, pack_unit: "g",
      ingredients_text: "Oats, sugar", nutrition_basis: "per_100g",
      nutrition: { energy: "400 kcal", protein: "10 g" },
    });
  });
});

describe("AlternativesPanel scope", () => {
  it("says which shop the alternatives come from", async () => {
    mockFetch(() => ({ body: { ...alternatives, site: "blinkit.com", scope: "same_site" } }));
    render(<AlternativesPanel productId={1} />);
    expect(await screen.findByText(/from blinkit\.com considered/)).toBeInTheDocument();
  });
});

describe("service problems", () => {
  it("explains a bare proxy 500 as the API not running", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("Internal Server Error", { status: 500 })));
    const { ServiceStatus } = await import("@/components/ServiceStatus");
    render(<ServiceStatus />);
    expect(await screen.findByText(/API\) is not running/)).toBeInTheDocument();
  });

  it("explains a database outage", async () => {
    mockFetch(() => ({ body: { status: "degraded", database: "unavailable", methodology_version: "0.1.0", product_count: null } }));
    const { ServiceStatus } = await import("@/components/ServiceStatus");
    render(<ServiceStatus />);
    expect(await screen.findByText(/cannot reach the database/)).toBeInTheDocument();
  });

  it("shows the distinct robots restriction explanation without retailer wording", async () => {
    const { errorHint } = await import("@/components/AnalyzeForm");
    expect(errorHint("robots_disallowed")).toMatch(/respect its access restrictions/);
    expect(errorHint("robots_disallowed")).not.toMatch(/retailer/i);
    expect(errorHint("unsupported_source")).toMatch(/retailer is not currently supported/i);
    expect(errorHint("source_fetch_failed")).toMatch(/could not be retrieved/i);
    expect(errorHint("product_extraction_failed")).toMatch(/information could not be extracted/i);
    expect(errorHint("blocked_destination")).toBeNull();
  });
});
