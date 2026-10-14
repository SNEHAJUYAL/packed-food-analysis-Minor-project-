import type {
  AlternativesResult,
  AnalyzeUrlRequest,
  ApiErrorBody,
  Category,
  CompareRequest,
  CompareResult,
  Health,
  Methodology,
  Preference,
  ProductAnalysis,
  ProductList,
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
  415: "This page type is not supported.",
  422: "Please check the input and try again.",
  429: "Too many requests. Please wait a minute and try again.",
  502: "The page could not be fetched.",
  503: "The service is temporarily unavailable.",
  504: "The page took too long to respond.",
};

/** Turn any error body into an ApiError, keeping the API's plain-language `message`. */
export function parseApiError(status: number, body: unknown): ApiError {
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
      headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}), ...init?.headers },
      cache: "no-store",
    });
  } catch (err) {
    if ((err as Error)?.name === "AbortError") throw err;
    throw new ApiError(0, "network_error", "Could not reach the analysis service. Is the backend running?");
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
  if (!res.ok) throw parseApiError(res.status, body);
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
};

export type Api = typeof api;
