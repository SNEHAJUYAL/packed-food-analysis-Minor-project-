"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { ErrorState, Spinner } from "./ui";
import { ApiError, api } from "@/lib/api";
import { ANALYSIS_STEPS } from "@/lib/labels";
import type { Category } from "@/lib/types";

type Phase = "idle" | "running" | "done" | "error";

// Which progress step an API error belongs to; the steps advance on a timer, so the step shown
// when an error arrives is not necessarily where it happened.
const ERROR_STEP: Record<string, number> = {
  invalid_url: 0, blocked_destination: 0, validation_error: 0,
  robots_disallowed: 1, fetch_failed: 1, timeout: 1, too_large: 1, unsupported_content: 1,
};
const SERVICE_DOWN = new Set(["backend_unreachable", "network_error", "database_unavailable", "internal_error"]);
const SHOP_HINT =
  "Shopping apps such as Blinkit, Zepto and Swiggy Instamart often refuse automated requests. Save the product page " +
  "in your browser (⌘S or Ctrl+S) or take a screenshot, and upload it below instead.";

export function errorHint(code: string): string | null {
  return ERROR_STEP[code] === 1 ? SHOP_HINT : null;
}

export function validateUrl(raw: string): string | null {
  const v = raw.trim();
  if (!v) return "Enter the address of a product page.";
  let u: URL;
  try {
    u = new URL(v);
  } catch {
    return "That does not look like a web address. It should start with https://";
  }
  if (u.protocol !== "http:" && u.protocol !== "https:") return "Only http and https addresses can be analysed.";
  return null;
}

export function ProgressSteps({ active, phase }: { active: number; phase: Phase }) {
  return (
    <ol aria-label="Analysis progress" className="space-y-2">
      {ANALYSIS_STEPS.map((step, i) => {
        const done = phase === "done" || i < active;
        const current = i === active && phase === "running";
        const stopped = i === active && phase === "error";
        return (
          <li key={step} className="flex items-center gap-3 text-sm" aria-current={current ? "step" : undefined}>
            <span
              className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs ${
                done ? "bg-brand-600 text-white" : current ? "bg-brand-50 ring-1 ring-brand-500" : stopped ? "bg-amber-100 text-amber-900" : "bg-slate-100 text-slate-400"
              }`}
            >
              {done ? "✓" : current ? <Spinner className="h-3 w-3" /> : stopped ? "!" : i + 1}
            </span>
            <span className={done || current ? "text-ink" : stopped ? "text-amber-900" : "text-muted"}>
              {step}
              {stopped ? " — stopped" : ""}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

export function AnalyzeForm({ stepIntervalMs = 1800 }: { stepIntervalMs?: number }) {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [category, setCategory] = useState("");
  const [refresh, setRefresh] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [active, setActive] = useState(0);
  const [inputError, setInputError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<ApiError | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    api
      .categories(ctrl.signal)
      .then((r) => setCategories(r.categories ?? []))
      .catch(() => setCategories([]));
    return () => {
      ctrl.abort();
      if (timer.current) clearInterval(timer.current);
    };
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const problem = validateUrl(url);
    setInputError(problem);
    setApiError(null);
    if (problem) return;
    setPhase("running");
    setActive(0);
    // The API answers in one response, so the steps advance on a timer while we wait and the
    // last step only completes when the result arrives.
    timer.current = setInterval(() => setActive((a) => Math.min(a + 1, ANALYSIS_STEPS.length - 1)), stepIntervalMs);
    try {
      const result = await api.analyzeUrl({ url: url.trim(), category: category || null, refresh });
      if (timer.current) clearInterval(timer.current);
      setActive(ANALYSIS_STEPS.length);
      setPhase("done");
      router.push(`/products/${result.product_id}`);
    } catch (err) {
      if (timer.current) clearInterval(timer.current);
      const e = err instanceof ApiError ? err : new ApiError(0, "error", "The analysis could not be completed.");
      setPhase(SERVICE_DOWN.has(e.code) ? "idle" : "error");
      if (e.code in ERROR_STEP) setActive(ERROR_STEP[e.code]);
      setApiError(e);
    }
  }

  const busy = phase === "running" || phase === "done";

  return (
    <div className="space-y-4">
      <form onSubmit={onSubmit} noValidate className="space-y-3" aria-describedby="url-help">
        <label htmlFor="product-url" className="block text-sm font-medium text-ink">
          Product page URL
        </label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            id="product-url"
            name="url"
            type="url"
            inputMode="url"
            autoComplete="url"
            placeholder="https://brand.example/product"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={busy}
            aria-invalid={inputError ? true : undefined}
            aria-errormessage={inputError ? "url-error" : undefined}
            className="min-w-0 flex-1 rounded-xl border border-line bg-white px-4 py-3 text-base text-ink placeholder:text-slate-400 focus:border-brand-500 disabled:bg-slate-50"
          />
          <button
            type="submit"
            disabled={busy}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand-600 px-5 py-3 font-medium text-white hover:bg-brand-700 disabled:opacity-70"
          >
            {busy ? <Spinner className="border-white border-t-transparent" /> : null}
            {busy ? "Analysing…" : "Analyse"}
          </button>
        </div>
        {inputError ? (
          <p id="url-error" className="text-sm text-amber-800">
            {inputError}
          </p>
        ) : null}
        <p id="url-help" className="text-xs text-muted">
          Paste a brand or retailer product page. The page is fetched only if its robots.txt allows it.
        </p>
        <div className="flex flex-col gap-3 text-sm sm:flex-row sm:items-center sm:gap-6">
          {categories.length ? (
            <label className="flex items-center gap-2">
              <span className="text-slate-700">Category</span>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                disabled={busy}
                className="rounded-lg border border-line bg-white px-2 py-1.5"
              >
                <option value="">Detect automatically</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <label className="flex items-center gap-2 text-slate-700">
            <input type="checkbox" checked={refresh} onChange={(e) => setRefresh(e.target.checked)} disabled={busy} className="h-4 w-4 accent-brand-600" />
            Fetch again (ignore cached copy)
          </label>
        </div>
      </form>

      {phase !== "idle" ? (
        <div className="rounded-2xl border border-line bg-white p-4" aria-live="polite">
          <ProgressSteps active={active} phase={phase} />
          {phase === "done" ? <p className="mt-3 text-sm text-muted">Done. Opening the report…</p> : null}
        </div>
      ) : null}
      {apiError ? (
        <ErrorState
          title={SERVICE_DOWN.has(apiError.code) ? "The analysis service is not available" : "The page could not be analysed"}
          message={[apiError.message, errorHint(apiError.code)].filter(Boolean).join(" ")}
          code={apiError.code}
        />
      ) : null}
    </div>
  );
}
