"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ErrorState, Spinner } from "./ui";
import { ApiError, api } from "@/lib/api";
import { validateUrl } from "./AnalyzeForm";

const IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"];
const MAX_IMAGE_BYTES = 8 * 1024 * 1024;
const MAX_PAGE_BYTES = 5 * 1024 * 1024;
const SITES = [
  { id: "", label: "Not from a shop / not sure" },
  { id: "blinkit.com", label: "Blinkit" },
  { id: "zeptonow.com", label: "Zepto" },
  { id: "swiggy.com", label: "Swiggy Instamart" },
  { id: "bigbasket.com", label: "BigBasket" },
];

export function checkFile(file: File | null): string | null {
  if (!file) return "Choose a photo, a screenshot or a saved product page.";
  const name = file.name.toLowerCase();
  const isPage = name.endsWith(".html") || name.endsWith(".htm") || file.type === "text/html";
  const isImage = IMAGE_TYPES.includes(file.type) || /\.(jpe?g|png|webp|gif)$/.test(name);
  if (!isPage && !isImage) return "Use a JPEG, PNG, WebP or GIF image, or a page saved as .html.";
  if (isImage && file.size > MAX_IMAGE_BYTES) return "Images must be 8 MB or smaller.";
  if (isPage && file.size > MAX_PAGE_BYTES) return "Saved pages must be 5 MB or smaller.";
  if (file.size === 0) return "That file is empty.";
  return null;
}

export function UploadForm() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [site, setSite] = useState("");
  const [pageUrl, setPageUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [inputError, setInputError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<ApiError | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const problem = checkFile(file) ?? (pageUrl.trim() ? validateUrl(pageUrl) : null);
    setInputError(problem);
    setApiError(null);
    if (problem || !file) return;
    setBusy(true);
    try {
      const result = await api.analyzeUpload({ file, site: site || null, page_url: pageUrl.trim() || null });
      router.push(`/products/${result.product_id}`);
    } catch (err) {
      setBusy(false);
      setApiError(err instanceof ApiError ? err : new ApiError(0, "error", "The file could not be analysed."));
    }
  }

  return (
    <div className="space-y-3">
      <form onSubmit={onSubmit} noValidate className="space-y-3 rounded-2xl border border-line bg-white p-4" aria-describedby="upload-help">
        <p className="text-sm font-medium text-ink">Or upload a pack photo, a screenshot, or a saved product page</p>
        <label className="block text-sm">
          <span className="sr-only">Photo, screenshot or saved page</span>
          <input
            type="file"
            aria-label="Photo, screenshot or saved page"
            accept="image/jpeg,image/png,image/webp,image/gif,.html,.htm,text/html"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            disabled={busy}
            className="block w-full text-sm text-slate-700 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-2 file:text-brand-700"
          />
        </label>
        <div className="flex flex-col gap-2 text-sm sm:flex-row sm:items-center sm:gap-4">
          <label className="flex items-center gap-2">
            <span className="text-slate-700">Shop</span>
            <select value={site} onChange={(e) => setSite(e.target.value)} disabled={busy} className="rounded-lg border border-line bg-white px-2 py-1.5">
              {SITES.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
          <input
            type="url"
            inputMode="url"
            aria-label="Product link (optional)"
            placeholder="Product link (optional)"
            value={pageUrl}
            onChange={(e) => setPageUrl(e.target.value)}
            disabled={busy}
            className="min-w-0 flex-1 rounded-lg border border-line bg-white px-3 py-1.5 placeholder:text-slate-400"
          />
          <button
            type="submit"
            disabled={busy}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 font-medium text-white hover:bg-brand-700 disabled:opacity-70"
          >
            {busy ? <Spinner className="border-white border-t-transparent" /> : null}
            {busy ? "Reading…" : "Upload and analyse"}
          </button>
        </div>
        {inputError ? <p className="text-sm text-amber-800">{inputError}</p> : null}
        <p id="upload-help" className="text-xs text-muted">
          Photos are read by an AI model and only values that appear in its transcript of the label are kept; check them
          against the pack. A page saved from the browser (Ctrl+S or ⌘S) is read as saved, with nothing fetched. Choosing
          the shop lets alternatives come from products analysed from the same shop.
        </p>
      </form>
      {apiError ? <ErrorState title="The file could not be analysed" message={apiError.message} code={apiError.code} /> : null}
    </div>
  );
}
