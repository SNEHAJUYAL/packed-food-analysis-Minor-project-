import type {
  AlternativesResult,
  AnalyzeUploadRequest,
  AnalyzeUrlRequest,
  ApiErrorBody,
  Category,
  CompareRequest,
  CompareResult,
  Health,
  Methodology,
  ManualAnalyzeRequest,
  Preference,
  ProductAnalysis,
  ProductList,
  PriceEntryRequest,
  PriceSummary,
  ProductURLCandidateResult,
  SearchResult,
  AskAnswer,
} from "./types";

/**
 * Base URL for browser requests. Empty (the default) means same-origin `/api/...`, which the
 * Next.js rewrite in next.config.ts proxies to the FastAPI backend. Set NEXT_PUBLIC_API_BASE_URL
 * only to call the backend directly (it must then allow CORS).
 */
export function apiBase(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  return raw.replace(/\/+$/, "");
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

const FALLBACK_MESSAGES: Record<number, string> = {
  400: "The request could not be processed.",
  403: "Access to this page is not permitted.",
  404: "Not found.",
  413: "The page is too large to analyse.",
  415: "This file or page type is not supported.",
  422: "Please check the input and try again.",
  429: "Too many requests. Please wait a minute and try again.",
  502: "The page could not be fetched.",
  503: "The service is temporarily unavailable.",
  504: "The page took too long to respond.",
};

export const BACKEND_DOWN =
  "The analysis service (API) is not running. Start it in a second terminal with ./run.sh api, then try again.";

/** Turn any error body into an ApiError, keeping the API's plain-language `message`. */
export function parseApiError(status: number, body: unknown): ApiError {
  const root = body as { error_code?: unknown; message?: unknown } | null;
  if (root && typeof root === "object" && typeof root.error_code === "string" &&
      typeof root.message === "string" && root.message) {
    return new ApiError(status, root.error_code, root.message);
  }
  const detail = (body as ApiErrorBody | null)?.detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const d = detail as { code?: unknown; message?: unknown };
    if (typeof d.message === "string" && d.message) {
      return new ApiError(status, typeof d.code === "string" ? d.code : "error", d.message);
    }
  }
  if (typeof detail === "string" && detail) return new ApiError(status, "error", detail);
  if (Array.isArray(detail)) {
    // FastAPI's default validation errors.
    const first = detail[0] as { msg?: string } | undefined;
    return new ApiError(status, "validation_error", first?.msg ?? FALLBACK_MESSAGES[422]);
  }
  return new ApiError(status, "error", FALLBACK_MESSAGES[status] ?? `Request failed (HTTP ${status}).`);
}

async function request<T>(path: string, init?: RequestInit & { signal?: AbortSignal }): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${apiBase()}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        // FormData sets its own multipart Content-Type with the boundary.
        ...(init?.body && !(init.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
      cache: "no-store",
    });
  } catch (err) {
    if ((err as Error)?.name === "AbortError") throw err;
    throw new ApiError(0, "network_error", BACKEND_DOWN);
  }
  let body: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }
  if (!res.ok) {
    // A 5xx with no JSON body comes from the Next.js proxy, not the API: the backend is not running
    // or not reachable at API_BASE_URL.
    if (res.status >= 500 && (body === null || typeof body !== "object")) {
      throw new ApiError(res.status, "backend_unreachable", BACKEND_DOWN);
    }
    throw parseApiError(res.status, body);
  }
  return body as T;
}

const q = (params: Record<string, string | number | undefined | null>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null && v !== "") s.set(k, String(v));
  const out = s.toString();
  return out ? `?${out}` : "";
};

export const api = {
  health: (signal?: AbortSignal) => request<Health>("/api/health", { signal }),
  analyzeUrl: (body: AnalyzeUrlRequest, signal?: AbortSignal) =>
    request<ProductAnalysis>("/api/analyze-url", { method: "POST", body: JSON.stringify(body), signal }),
  /** Source-policy-gated candidate extraction. This endpoint never saves or scores the product. */
  candidateFromUrl: (url: string, signal?: AbortSignal) =>
    request<ProductURLCandidateResult>("/api/product-candidates/from-url", {
      method: "POST", body: JSON.stringify({ url }), signal,
    }),
  analyzeManual: (body: ManualAnalyzeRequest, signal?: AbortSignal) =>
    request<ProductAnalysis>("/api/analyze-manual", { method: "POST", body: JSON.stringify(body), signal }),
  /** A pack photo, app screenshot or saved product page; nothing is fetched by the server. */
  analyzeUpload: (body: AnalyzeUploadRequest, signal?: AbortSignal) => {
    const form = new FormData();
    form.append("file", body.file);
    if (body.page_url) form.append("page_url", body.page_url);
    if (body.site) form.append("site", body.site);
    if (body.category) form.append("category", body.category);
    if (body.name) form.append("name", body.name);
    if (body.corrections?.brand) form.append("brand", body.corrections.brand);
    if (body.corrections?.variant) form.append("variant", body.corrections.variant);
    if (body.corrections?.pack_size_text) form.append("pack_size_text", body.corrections.pack_size_text);
    if (body.corrections?.ingredients_text) form.append("ingredients_text", body.corrections.ingredients_text);
    if (body.corrections?.nutrition_basis) form.append("nutrition_basis", body.corrections.nutrition_basis);
    if (body.corrections?.nutrition_text) form.append("nutrition_text", body.corrections.nutrition_text);
    return request<ProductAnalysis>("/api/analyze-upload", { method: "POST", body: form, signal });
  },
  listProducts: (params: { category?: string; q?: string; limit?: number } = {}, signal?: AbortSignal) =>
    request<ProductList>(`/api/products${q(params)}`, { signal }),
  getProduct: (id: number | string, signal?: AbortSignal) =>
    request<ProductAnalysis>(`/api/products/${encodeURIComponent(String(id))}`, { signal }),
  compare: (body: CompareRequest, signal?: AbortSignal) =>
    request<CompareResult>("/api/products/compare", { method: "POST", body: JSON.stringify(body), signal }),
  alternatives: (id: number | string, preference: Preference, limit = 5, signal?: AbortSignal) =>
    request<AlternativesResult>(
      `/api/products/${encodeURIComponent(String(id))}/alternatives${q({ preference, limit })}`,
      { signal },
    ),
  categories: (signal?: AbortSignal) => request<{ categories: Category[] }>("/api/reference/categories", { signal }),
  methodology: (signal?: AbortSignal) => request<Methodology>("/api/reference/methodology", { signal }),
  /** Type a product name, get a direct answer: grade, quality, comparison, alternatives, prices. */
  ask: (text: string, signal?: AbortSignal) =>
    request<AskAnswer>("/api/ask", { method: "POST", body: JSON.stringify({ q: text }), signal }),
  /** Stored products plus Open Food Facts results that have not been analysed yet. */
  search: (text: string, signal?: AbortSignal) =>
    request<SearchResult>(`/api/search${q({ q: text, limit: 20 })}`, { signal }),
  /** Bring one Open Food Facts product in (by its Open Food Facts code) and score it. */
  importOff: (code: string, signal?: AbortSignal) =>
    request<ProductAnalysis>("/api/products/import-off", { method: "POST", body: JSON.stringify({ barcode: code }), signal }),
  prices: (id: number | string, signal?: AbortSignal) =>
    request<PriceSummary>(`/api/products/${encodeURIComponent(String(id))}/prices`, { signal }),
  addPrice: (id: number | string, body: PriceEntryRequest, signal?: AbortSignal) =>
    request<PriceSummary>(`/api/products/${encodeURIComponent(String(id))}/prices`, {
      method: "POST", body: JSON.stringify(body), signal,
    }),
};

export type Api = typeof api;
