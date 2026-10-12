import { vi } from "vitest";

export type Handler = (url: string, init?: RequestInit) => { status?: number; body: unknown } | undefined;

/** Replace global fetch with a router over request URLs; records calls. */
export function mockFetch(handler: Handler) {
  const spy = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
    const res = handler(url, init) ?? { status: 404, body: { detail: { code: "not_found", message: "Not found." } } };
    return new Response(JSON.stringify(res.body), {
      status: res.status ?? 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", spy);
  return spy;
}

export { routerPush } from "./navigationMock";
