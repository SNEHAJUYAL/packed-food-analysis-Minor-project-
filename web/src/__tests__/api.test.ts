import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, parseApiError } from "@/lib/api";
import { mockFetch } from "./helpers";

afterEach(() => vi.unstubAllGlobals());

describe("parseApiError", () => {
  it("keeps the API's plain-language message and code", () => {
    const e = parseApiError(400, { detail: { code: "blocked_destination", message: "That address points to a private network." } });
    expect(e).toBeInstanceOf(ApiError);
    expect(e.code).toBe("blocked_destination");
    expect(e.message).toBe("That address points to a private network.");
  });

  it("handles string details, FastAPI validation arrays and empty bodies", () => {
    expect(parseApiError(404, { detail: "Product not found" }).message).toBe("Product not found");
    expect(parseApiError(422, { detail: [{ msg: "field required" }] }).message).toBe("field required");
    expect(parseApiError(504, null).message).toMatch(/too long/);
  });
});

describe("api client", () => {
  it("calls same-origin /api paths and passes query parameters", async () => {
    const spy = mockFetch(() => ({ body: { alternatives: [] } }));
    await api.alternatives(12, "price");
    expect(spy.mock.calls[0][0]).toBe("/api/products/12/alternatives?preference=price&limit=5");
  });

  it("throws ApiError with the backend message on failure", async () => {
    mockFetch(() => ({ status: 403, body: { detail: { code: "robots_disallowed", message: "The site's robots.txt does not allow this page to be fetched." } } }));
    await expect(api.analyzeUrl({ url: "https://x.example/p" })).rejects.toMatchObject({
      code: "robots_disallowed",
      status: 403,
      message: "The site's robots.txt does not allow this page to be fetched.",
    });
  });

  it("reports a network failure in plain language", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("fetch failed"); }));
    await expect(api.health()).rejects.toMatchObject({ code: "network_error" });
  });
});
