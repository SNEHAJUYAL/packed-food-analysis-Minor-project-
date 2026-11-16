"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { IconCheck, IconLink } from "./icons";
import { ErrorState, Spinner, buttonClass } from "./ui";
import { ApiError, api } from "@/lib/api";
import { ANALYSIS_STEPS } from "@/lib/labels";
import type { Category, Product, ProductURLCandidateResult } from "@/lib/types";

type Phase = "idle" | "running" | "done" | "error";

// Which progress step an API error belongs to; the steps advance on a timer, so the step shown
// when an error arrives is not necessarily where it happened.
const ERROR_STEP: Record<string, number> = {
  invalid_url: 0, blocked_destination: 0, unsupported_source: 0, validation_error: 0,
  robots_disallowed: 1, source_fetch_failed: 1, product_extraction_failed: 2,
  fetch_failed: 1, timeout: 1, too_large: 1, unsupported_content: 1,
};
const SERVICE_DOWN = new Set(["backend_unreachable", "network_error", "database_unavailable", "internal_error"]);
const SOURCE_MESSAGES: Record<string, string> = {
  unsupported_source: "This retailer is not currently supported for automated product extraction. You can upload a saved product page or packaging screenshots instead.",
  robots_disallowed: "This source does not permit automated access to this page. We respect its access restrictions. You can upload a saved copy of the product page or product screenshots.",
  source_fetch_failed: "The product page could not be retrieved. Please upload a saved page or product screenshots.",
  product_extraction_failed: "The page was retrieved, but the required product information could not be extracted. Upload packaging images or enter the product details manually.",
};

export function errorHint(code: string): string | null {
  return SOURCE_MESSAGES[code] ?? null;
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
    <ol aria-label="Analysis progress" className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {ANALYSIS_STEPS.map((step, i) => {
        const done = phase === "done" || i < active;
        const current = i === active && phase === "running";
        const stopped = i === active && phase === "error";
        return (
          <li key={step} className={`flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition ${current ? "bg-brand-50" : stopped ? "bg-[#fdf6ec]" : ""}`} aria-current={current ? "step" : undefined}>
            <span
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                done ? "bg-forest text-white" : current ? "bg-white ring-2 ring-brand-500" : stopped ? "bg-warn text-[#3d2508]" : "bg-slate-100 text-slate-400"
              }`}
            >
              {done ? <IconCheck className="h-3.5 w-3.5" /> : current ? <Spinner className="h-3 w-3" /> : stopped ? "!" : i + 1}
            </span>
            <span className={done || current ? "font-medium text-ink" : stopped ? "font-medium text-[#7a4a12]" : "text-muted"}>
              {step}
              {stopped ? " — stopped" : ""}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function knownNutrition(product: Product) {
  return Object.entries(product.nutrition ?? {}).filter(([, item]) => item?.value !== null && item?.value !== undefined);
}

function candidateMissing(product: Product, issues: ProductURLCandidateResult["issues"] = []): string[] {
  const missing: string[] = [];
  if (!product.name?.value) missing.push("Product name");
  if (!product.brand?.value) missing.push("Brand");
  if (!product.category?.value) missing.push("Category");
  if (!product.variant?.value) missing.push("Variant or flavour");
  if (!product.pack_size?.value || !product.pack_unit?.value) missing.push("Pack size");
  if (!product.ingredients_raw?.value) missing.push("Ingredients");
  if (!knownNutrition(product).length) missing.push("Nutrition");
  const labels: Record<string, string> = {
    description: "Description", serving_size_text: "Serving size", allergens_text: "Allergens",
    claims_text: "Marketing claims", gtin: "Barcode", price: "Selling price", mrp: "MRP",
    availability: "Availability", currency: "Currency", image_url: "Product image",
  };
  for (const issue of issues ?? []) {
    if (issue.code === "missing_extracted_field" && labels[issue.field_path]) missing.push(labels[issue.field_path]);
  }
  return [...new Set(missing)];
}

function messageFor(error: ApiError): string {
  if (SOURCE_MESSAGES[error.code]) return SOURCE_MESSAGES[error.code];
  if (error.code === "invalid_url") return "Enter a valid HTTP or HTTPS product URL.";
  return error.message;
}

function OfflineFallbackLinks() {
  return (
    <div className="mt-3 flex flex-wrap gap-2 text-sm">
      <a className={`${buttonClass.secondary} !py-2`} href="#saved-page-upload">Upload saved product page</a>
      <a className={`${buttonClass.secondary} !py-2`} href="#packaging-image-upload">Upload product packaging images</a>
      <a className={`${buttonClass.secondary} !py-2`} href="#manual-entry-form">Enter product details manually</a>
    </div>
  );
}

function CandidatePreview({ result }: { result: ProductURLCandidateResult }) {
  const candidate = result.candidate;
  if (!candidate) return null;
  const product = candidate.normalized_product;
  const nutrition = knownNutrition(product);
  const missing = candidateMissing(product, candidate.issues);
  const conflicts = [...(candidate.issues ?? []), ...(result.issues ?? [])].filter((issue) =>
    issue.code.includes("conflict") || issue.severity === "error",
  );
  const hasAnyProductDetail = Boolean(product.name?.value || product.brand?.value ||
    product.ingredients_raw?.value || nutrition.length || candidate.images.length);
  const servingRaw = candidate.field_evidence.find((field) => field.field_path === "serving_size_text")?.original_value;
  const servingSize = typeof servingRaw === "string" || typeof servingRaw === "number" ? String(servingRaw) : null;
  const overview: { label: string; value: string | null | undefined }[] = [
    { label: "Product", value: product.name?.value },
    { label: "Brand", value: product.brand?.value },
    { label: "Category", value: product.category?.value },
    { label: "Variant", value: product.variant?.value },
    { label: "Pack size", value: product.pack_size?.value && product.pack_unit?.value
      ? `${product.pack_size.value} ${product.pack_unit.value}` : null },
    { label: "Serving size", value: servingSize },
  ];

  return (
    <section className="animate-fade-up rounded-[var(--radius-card)] border border-[#f1d2a8] bg-[#fdf8f0] p-4 sm:p-5" aria-labelledby="candidate-title" aria-live="polite">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-amber-800">Candidate preview · not saved</p>
          <h3 id="candidate-title" className="mt-1 text-lg font-semibold text-ink">Unverified product information</h3>
        </div>
        <span className="rounded-full border border-amber-400 bg-white px-3 py-1 text-xs font-semibold text-amber-900">UNVERIFIED</span>
      </div>

      {!hasAnyProductDetail ? (
        <p className="mt-4 rounded-xl bg-white/80 p-3 text-sm text-amber-950">
          The page was reachable, but no product details could be extracted. Try a supported product page or upload a saved page or package image.
        </p>
      ) : (
        <>
          <dl className="mt-4 grid gap-x-6 gap-y-3 rounded-xl bg-white/80 p-4 sm:grid-cols-2">
            {overview.map(({ label, value }) => (
              <div key={label}>
                <dt className="text-xs font-medium text-muted">{label}</dt>
                <dd className="mt-0.5 break-words text-sm text-ink">{value || <span className="text-slate-400">Not found</span>}</dd>
              </div>
            ))}
          </dl>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <section className="rounded-xl bg-white/80 p-4" aria-labelledby="candidate-ingredients">
              <h4 id="candidate-ingredients" className="text-sm font-semibold text-ink">Ingredients</h4>
              {product.ingredients_raw?.value
                ? <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-ink">{product.ingredients_raw.value}</p>
                : <p className="mt-2 text-sm text-muted">No ingredient information was found.</p>}
            </section>
            <section className="rounded-xl bg-white/80 p-4" aria-labelledby="candidate-nutrition">
              <h4 id="candidate-nutrition" className="text-sm font-semibold text-ink">Nutrition{product.nutrition_basis ? ` · ${product.nutrition_basis.replaceAll("_", " ")}` : ""}</h4>
              {nutrition.length ? (
                <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
                  {nutrition.map(([name, item]) => (
                    <div key={name} className="contents">
                      <dt className="text-muted">{name.replaceAll("_", " ")}</dt>
                      <dd className="text-right text-ink">{item.value} <span className="text-xs text-muted">{item.label}</span></dd>
                    </div>
                  ))}
                </dl>
              ) : <p className="mt-2 text-sm text-muted">No nutrition values were found.</p>}
            </section>
          </div>

          {candidate.images.length ? (
            <section className="mt-4 rounded-xl bg-white/80 p-4" aria-labelledby="candidate-images">
              <h4 id="candidate-images" className="text-sm font-semibold text-ink">Image references</h4>
              <p className="mt-1 text-xs text-muted">URLs only. Image availability, contents and product match have not been verified.</p>
              <ul className="mt-2 space-y-2 text-sm">
                {candidate.images.map((image) => (
                  <li key={image.image_url} className="break-all">
                    <a href={image.image_url} target="_blank" rel="noreferrer" className="text-brand-700 underline decoration-brand-300 underline-offset-2">{image.image_url}</a>
                    <span className="ml-2 text-xs text-muted">{image.source} · {image.validation_status.replaceAll("_", " ")}</span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </>
      )}

      {missing.length ? (
        <div className="mt-4 rounded-xl border border-amber-200 bg-white/80 p-3">
          <h4 className="text-sm font-semibold text-amber-950">Not found on this page</h4>
          <p className="mt-1 text-sm text-amber-900">{missing.join(" · ")}</p>
        </div>
      ) : null}
      {conflicts.length ? (
        <div className="mt-3 rounded-xl border border-red-200 bg-red-50 p-3" role="status">
          <h4 className="text-sm font-semibold text-red-900">Conflicting or invalid details need review</h4>
          <ul className="mt-1 list-disc pl-5 text-sm text-red-900">
            {conflicts.map((issue, index) => <li key={`${issue.code}-${issue.field_path}-${index}`}>{issue.field_path}: {issue.message}</li>)}
          </ul>
        </div>
      ) : null}

      <details className="mt-4 rounded-xl border border-amber-200 bg-white/80 p-3">
        <summary className="cursor-pointer text-sm font-medium text-ink">Source and field provenance</summary>
        <dl className="mt-3 grid gap-3 text-xs sm:grid-cols-2">
          <div><dt className="font-semibold text-muted">Source</dt><dd className="mt-0.5 break-all text-ink">{candidate.source_attribution || candidate.source_id}</dd></div>
          <div><dt className="font-semibold text-muted">Page</dt><dd className="mt-0.5 break-all"><a className="text-brand-700 underline" href={candidate.final_url} target="_blank" rel="noreferrer">{candidate.final_url}</a></dd></div>
          <div><dt className="font-semibold text-muted">Extracted</dt><dd className="mt-0.5 text-ink">{new Date(candidate.extracted_at).toLocaleString()}</dd></div>
          <div><dt className="font-semibold text-muted">License / attribution</dt><dd className="mt-0.5 text-ink">{candidate.license || "Not stated"}</dd></div>
        </dl>
        {candidate.field_evidence.length ? <ul className="mt-3 max-h-56 space-y-2 overflow-auto border-t border-line pt-3">
          {candidate.field_evidence.map((field, index) => (
            <li key={`${field.field_path}-${index}`} className="break-words text-xs text-ink">
              <strong>{field.field_path}</strong> · {field.validation_status} · {field.provenance.extraction_method}
              <div className="mt-0.5 text-muted">Original: {JSON.stringify(field.original_value)}{field.normalized_value !== null && field.normalized_value !== undefined ? ` · Normalized: ${JSON.stringify(field.normalized_value)}` : ""}</div>
              <div className="text-muted">{field.provenance.source_url} · {field.provenance.collected_at}</div>
            </li>
          ))}
        </ul> : <p className="mt-3 border-t border-line pt-3 text-xs text-muted">No source fields were extracted.</p>}
      </details>
    </section>
  );
}

export function AnalyzeForm({
  stepIntervalMs = 1800,
  initialUrl = "",
  autoSubmit = false,
}: {
  stepIntervalMs?: number;
  /** Prefills the field (e.g. from the landing page). */
  initialUrl?: string;
  /** Start straight away with `initialUrl`: used only after the person pressed Analyse on the landing page. */
  autoSubmit?: boolean;
}) {
  const router = useRouter();
  const [url, setUrl] = useState(initialUrl);
  const [category, setCategory] = useState("");
  const [refresh, setRefresh] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [active, setActive] = useState(0);
  const [inputError, setInputError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<ApiError | null>(null);
  const [candidate, setCandidate] = useState<ProductURLCandidateResult | null>(null);
  const [candidateError, setCandidateError] = useState<ApiError | null>(null);
  const [candidateBusy, setCandidateBusy] = useState(false);
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
    await run(url);
  }

  async function run(target: string) {
    const problem = validateUrl(target);
    setInputError(problem);
    setApiError(null);
    if (problem) return;
    setPhase("running");
    setActive(0);
    // The API answers in one response, so the steps advance on a timer while we wait and the
    // last step only completes when the result arrives.
    timer.current = setInterval(() => setActive((a) => Math.min(a + 1, ANALYSIS_STEPS.length - 1)), stepIntervalMs);
    try {
      const result = await api.analyzeUrl({ url: target.trim(), category: category || null, refresh });
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

  // Landing-page hand-off: start once after mount. The timer is cleared on unmount, so React's
  // development double-mount does not send two requests.
  useEffect(() => {
    if (!autoSubmit || !initialUrl) return;
    const t = setTimeout(() => void run(initialUrl), 0);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onCandidatePreview() {
    const problem = validateUrl(url);
    setInputError(problem);
    setCandidate(null);
    setCandidateError(null);
    if (problem) return;
    setCandidateBusy(true);
    try {
      setCandidate(await api.candidateFromUrl(url.trim()));
    } catch (err) {
      const e = err instanceof ApiError ? err : new ApiError(0, "error", "The candidate preview could not be completed.");
      setCandidateError(e);
    } finally {
      setCandidateBusy(false);
    }
  }

  const busy = phase === "running" || phase === "done";

  return (
    <div className="space-y-4">
      <form onSubmit={onSubmit} noValidate className="space-y-3" aria-describedby="url-help">
        <label htmlFor="product-url" className="block text-sm font-semibold text-ink">
          Product page URL
        </label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative min-w-0 flex-1">
          <IconLink className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
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
            className="w-full rounded-xl border border-line bg-white py-3.5 pl-12 pr-4 text-base text-ink placeholder:text-slate-400 transition focus:border-brand-500 focus:outline-none focus:ring-4 focus:ring-brand-100 disabled:bg-slate-50"
          />
          </div>
          <button
            type="submit"
            disabled={busy}
            className={`${buttonClass.primary} sm:min-w-[140px]`}
          >
            {busy ? <Spinner className="border-white border-t-transparent" /> : null}
            {busy ? "Analysing…" : "Analyse"}
          </button>
        </div>
        {inputError ? (
          <p id="url-error" className="text-sm font-medium text-[#8f3530]">
            {inputError}
          </p>
        ) : null}
        <p id="url-help" className="text-xs leading-5 text-muted">
          The page is fetched once, on your request, only where the site&apos;s robots.txt allows it. Many shop apps block
          automated access; if that happens, upload a saved page or a pack photo instead.
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onCandidatePreview}
            disabled={candidateBusy || busy}
            className={buttonClass.secondary}
          >
            {candidateBusy ? <Spinner className="h-4 w-4" /> : null}
            {candidateBusy ? "Previewing…" : "Preview candidate (not saved)"}
          </button>
          <span className="self-center text-xs text-muted">Analyze saves and scores a product. Preview only extracts an unverified candidate.</span>
        </div>
        <div className="flex flex-col gap-3 text-sm sm:flex-row sm:items-center sm:gap-6">
          {categories.length ? (
            <label className="flex items-center gap-2">
              <span className="text-slate-700">Category</span>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                disabled={busy}
                className="rounded-xl border border-line bg-white px-3 py-2 text-sm"
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
        <div className="animate-fade-up rounded-[var(--radius-card)] border border-line bg-white p-4 shadow-[var(--shadow-card)]" aria-live="polite">
          <ProgressSteps active={active} phase={phase} />
          {phase === "done" ? <p className="mt-3 text-sm text-muted">Done. Opening the report…</p> : null}
        </div>
      ) : null}
      {apiError ? (
        <ErrorState
          title={apiError.code === "unsupported_source" ? "This retailer is not supported for automatic access" :
            apiError.code === "robots_disallowed" ? "This page cannot be fetched automatically" :
            apiError.code === "source_fetch_failed" ? "The product page could not be retrieved" :
            apiError.code === "product_extraction_failed" ? "Product details were not found" :
            SERVICE_DOWN.has(apiError.code) ? "The analysis service is not available" : "The page could not be analysed"}
          message={messageFor(apiError)}
          code={apiError.code}
          action={SOURCE_MESSAGES[apiError.code] ? <OfflineFallbackLinks /> : undefined}
        />
      ) : null}
      {candidateError ? <ErrorState title="Candidate preview unavailable" message={messageFor(candidateError)} code={candidateError.code}
        action={SOURCE_MESSAGES[candidateError.code] ? <OfflineFallbackLinks /> : undefined} /> : null}
      {candidate ? <CandidatePreview result={candidate} /> : null}
    </div>
  );
}
