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
    await userEvent.upload(screen.getByLabelText("Photo, screenshot or saved page"), png());
    await userEvent.selectOptions(screen.getByRole("combobox"), "blinkit.com");
    await userEvent.click(screen.getByRole("button", { name: "Upload and analyse" }));
    await waitFor(() => expect(routerPush).toHaveBeenCalled());
    expect(sent).toBeInstanceOf(FormData);
    expect(sent?.get("site")).toBe("blinkit.com");
    expect((sent?.get("file") as File).name).toBe("okra.png");
    expect(headers?.["Content-Type"]).toBeUndefined();
  });

  it("shows the API's message when photos cannot be read", async () => {
    mockFetch(() => ({ status: 503, body: { detail: { code: "vision_not_configured", message: "Reading photos needs an Anthropic API key (ANTHROPIC_API_KEY in .env). Saved product pages work without one." } } }));
    render(<UploadForm />);
    await userEvent.upload(screen.getByLabelText("Photo, screenshot or saved page"), png());
    await userEvent.click(screen.getByRole("button", { name: "Upload and analyse" }));
    expect(await screen.findByText(/needs an Anthropic API key/)).toBeInTheDocument();
    expect(routerPush).not.toHaveBeenCalled();
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

  it("adds the upload hint when a shop refuses the fetch", async () => {
    const { errorHint } = await import("@/components/AnalyzeForm");
    expect(errorHint("fetch_failed")).toMatch(/Save the product page/);
    expect(errorHint("blocked_destination")).toBeNull();
  });
});
