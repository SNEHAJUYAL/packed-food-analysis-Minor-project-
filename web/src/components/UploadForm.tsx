"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type DragEvent, type FormEvent } from "react";
import { IconClose, IconFile, IconImage, IconPencil, IconUpload } from "./icons";
import { ErrorState, Spinner, buttonClass, inputClass } from "./ui";
import { ApiError, api } from "@/lib/api";
import { validateUrl } from "./AnalyzeForm";
import type { Category } from "@/lib/types";

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

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

const isImageFile = (f: File) => IMAGE_TYPES.includes(f.type) || /\.(jpe?g|png|webp|gif)$/i.test(f.name);

/**
 * Offline evidence: a saved page or packaging image (`mode="upload"`), typed label details
 * (`mode="manual"`), or both (default).
 */
export function UploadForm({ mode = "all" }: { mode?: "all" | "upload" | "manual" }) {
  const router = useRouter();
  const [file, setFileState] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const previewRef = useRef<string | null>(null);

  function setFile(next: File | null) {
    if (previewRef.current && typeof URL.revokeObjectURL === "function") URL.revokeObjectURL(previewRef.current);
    const url = next && isImageFile(next) && typeof URL.createObjectURL === "function" ? URL.createObjectURL(next) : null;
    previewRef.current = url;
    setPreview(url);
    setFileState(next);
    setInputError(next ? checkFile(next) : null);
  }

  useEffect(() => () => {
    if (previewRef.current && typeof URL.revokeObjectURL === "function") URL.revokeObjectURL(previewRef.current);
  }, []);

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer?.files?.[0];
    if (dropped) setFile(dropped);
  }
  const [site, setSite] = useState("");
  const [pageUrl, setPageUrl] = useState("");
  const [name, setName] = useState("");
  const [brand, setBrand] = useState("");
  const [variant, setVariant] = useState("");
  const [packSize, setPackSize] = useState("");
  const [ingredients, setIngredients] = useState("");
  const [nutritionBasis, setNutritionBasis] = useState<"per_100g" | "per_100ml" | "">("");
  const [nutritionText, setNutritionText] = useState("");
  const [manualName, setManualName] = useState("");
  const [manualBrand, setManualBrand] = useState("");
  const [manualVariant, setManualVariant] = useState("");
  const [manualPackSize, setManualPackSize] = useState("");
  const [manualPackUnit, setManualPackUnit] = useState<"g" | "ml">("g");
  const [manualIngredients, setManualIngredients] = useState("");
  const [manualNutritionBasis, setManualNutritionBasis] = useState<"per_100g" | "per_100ml" | "">("");
  const [manualNutritionText, setManualNutritionText] = useState("");
  const [manualPrice, setManualPrice] = useState("");
  const [category, setCategory] = useState("");
  const [categories, setCategories] = useState<Category[]>([]);

  useEffect(() => {
    const ctrl = new AbortController();
    api
      .categories(ctrl.signal)
      .then((r) => setCategories(r.categories ?? []))
      .catch(() => setCategories([]));
    return () => ctrl.abort();
  }, []);
  const [busy, setBusy] = useState(false);
  const [inputError, setInputError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<ApiError | null>(null);
  const [manualBusy, setManualBusy] = useState(false);
  const [manualError, setManualError] = useState<ApiError | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const problem = checkFile(file) ?? (pageUrl.trim() ? validateUrl(pageUrl) : null);
    setInputError(problem);
    setApiError(null);
    if (problem || !file) return;
    setBusy(true);
    try {
      const result = await api.analyzeUpload({
        file,
        site: site || null,
        page_url: pageUrl.trim() || null,
        name: name.trim() || null,
        category: category || null,
        corrections: {
          brand: brand.trim() || null,
          variant: variant.trim() || null,
          pack_size_text: packSize.trim() || null,
          ingredients_text: ingredients.trim() || null,
          nutrition_basis: nutritionBasis || null,
          nutrition_text: nutritionText.trim() || null,
        },
      });
      router.push(`/products/${result.product_id}`);
    } catch (err) {
      setBusy(false);
      setApiError(err instanceof ApiError ? err : new ApiError(0, "error", "The file could not be analysed."));
    }
  }

  function parseNutrition(text: string): Record<string, string> {
    const aliases: Record<string, string> = {
      "total carbohydrates": "carbohydrate", carbohydrates: "carbohydrate", sugars: "total_sugars",
      "total sugars": "total_sugars", "added sugars": "added_sugars", fat: "total_fat",
      "total fat": "total_fat", "saturated fat": "saturated_fat", "trans fat": "trans_fat",
      fiber: "fibre",
    };
    const result: Record<string, string> = {};
    for (const line of text.split(/\r?\n/)) {
      const match = line.match(/^\s*([^:=]+)\s*[:=]\s*(.+?)\s*$/);
      if (!match) continue;
      const rawName = match[1].trim().toLowerCase();
      const key = aliases[rawName] ?? rawName.replaceAll(" ", "_");
      result[key] = match[2].trim();
    }
    return result;
  }

  async function onManualSubmit(e: FormEvent) {
    e.preventDefault();
    setManualError(null);
    if (!manualName.trim()) {
      setManualError(new ApiError(422, "validation_error", "Enter the product name."));
      return;
    }
    const nutrition = parseNutrition(manualNutritionText);
    if (Object.keys(nutrition).length && !manualNutritionBasis) {
      setManualError(new ApiError(422, "validation_error", "Choose the nutrition basis before entering nutrient values."));
      return;
    }
    const size = manualPackSize.trim() ? Number(manualPackSize) : null;
    if (size !== null && (!Number.isFinite(size) || size <= 0)) {
      setManualError(new ApiError(422, "validation_error", "Pack size must be a positive number."));
      return;
    }
    const price = manualPrice.trim() ? Number(manualPrice) : null;
    if (price !== null && (!Number.isFinite(price) || price <= 0)) {
      setManualError(new ApiError(422, "validation_error", "Selling price must be a positive INR amount."));
      return;
    }
    setManualBusy(true);
    try {
      const result = await api.analyzeManual({
        name: manualName.trim(), brand: manualBrand.trim() || null, category: category || null,
        variant: manualVariant.trim() || null, pack_size: size, pack_unit: size === null ? null : manualPackUnit,
        ingredients_text: manualIngredients.trim() || null,
        nutrition_basis: manualNutritionBasis || null, nutrition, price_inr: price,
      });
      router.push(`/products/${result.product_id}`);
    } catch (err) {
      setManualBusy(false);
      setManualError(err instanceof ApiError ? err : new ApiError(0, "error", "The manual entry could not be analysed."));
    }
  }

  const field = "mt-1.5 " + inputClass;
  const lbl = "block text-xs font-medium text-slate-700";

  const uploadForm = (
    <form onSubmit={onSubmit} noValidate className="space-y-5" aria-describedby="upload-help">
      <div>
        <p className="text-base font-semibold text-ink">Upload a saved product page or packaging images</p>
        <p className="mt-1 text-xs leading-5 text-muted">
          <span id="saved-page-upload">Saved HTML pages (.html/.htm) are parsed locally; scripts are not run and remote images are not fetched.</span>{" "}
          <span id="packaging-image-upload">Images can show the front, back, ingredients or nutrition panel.</span>
        </p>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); if (!busy) setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={busy ? undefined : onDrop}
        className={`relative rounded-[var(--radius-card)] border-2 border-dashed p-6 text-center transition sm:p-8 ${
          dragging ? "border-brand-500 bg-brand-50" : file ? "border-brand-300 bg-white" : "border-slate-300 bg-slate-50/60 hover:border-brand-300"
        }`}
      >
        <input
          id="upload-file"
          type="file"
          aria-label="Saved product page or packaging image"
          accept="image/jpeg,image/png,image/webp,image/gif,.html,.htm,text/html"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          disabled={busy}
          className="sr-only"
        />
        {file ? (
          <div className="flex flex-col items-center gap-3 sm:flex-row sm:text-left">
            {preview ? (
              // eslint-disable-next-line @next/next/no-img-element -- local object URL preview, never a remote image
              <img src={preview} alt="Preview of the selected image" className="h-24 w-24 shrink-0 rounded-xl border border-line object-cover" />
            ) : (
              <span aria-hidden="true" className="flex h-16 w-16 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-forest">
                {isImageFile(file) ? <IconImage className="h-7 w-7" /> : <IconFile className="h-7 w-7" />}
              </span>
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-ink">{file.name}</p>
              <p className="text-xs text-muted">{isImageFile(file) ? "Image" : "Saved web page"} · {formatBytes(file.size)}</p>
            </div>
            <div className="flex gap-2">
              <label htmlFor="upload-file" className={`${buttonClass.secondary} cursor-pointer !py-2`}>Replace</label>
              <button type="button" onClick={() => setFile(null)} disabled={busy} className={`${buttonClass.ghost} !py-2`} aria-label="Remove selected file">
                <IconClose className="h-4 w-4" /> Remove
              </button>
            </div>
          </div>
        ) : (
          <label htmlFor="upload-file" className="flex cursor-pointer flex-col items-center gap-3">
            <span aria-hidden="true" className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-forest shadow-[var(--shadow-card)]">
              <IconUpload className="h-6 w-6" />
            </span>
            <span className="text-sm font-semibold text-ink">Drag a file here, or <span className="text-forest underline underline-offset-2">browse</span></span>
            <span className="text-xs text-muted">JPEG, PNG, WebP or GIF up to 8 MB · saved .html page up to 5 MB</span>
          </label>
        )}
      </div>
      {inputError ? <p role="alert" className="text-sm font-medium text-[#8f3530]">{inputError}</p> : null}

      <div className="grid gap-4 sm:grid-cols-2">
        <label className={lbl}>
          Shop
          <select value={site} onChange={(e) => setSite(e.target.value)} disabled={busy} className={field}>
            {SITES.map((s) => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
        </label>
        <label className={lbl}>
          Product link <span className="font-normal text-muted">(optional)</span>
          <input type="url" inputMode="url" aria-label="Product link (optional)" placeholder="https://…" value={pageUrl}
            onChange={(e) => setPageUrl(e.target.value)} disabled={busy} className={field} />
        </label>
        <label className={lbl}>
          Product name <span className="font-normal text-muted">(optional)</span>
          <input type="text" aria-label="Product name (optional)" placeholder="If the image does not show it" value={name}
            onChange={(e) => setName(e.target.value)} disabled={busy} maxLength={200} className={field} />
        </label>
        {categories.length ? (
          <label className={lbl}>
            Category
            <select value={category} onChange={(e) => setCategory(e.target.value)} disabled={busy} className={field}>
              <option value="">Detect automatically</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.label}</option>
              ))}
            </select>
          </label>
        ) : null}
      </div>

      <details className="group rounded-xl border border-line bg-white p-4">
        <summary className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-ink">
          <IconPencil className="h-4 w-4 text-forest" /> Correct or add details before analysis
        </summary>
        <p className="mt-2 text-xs text-muted">Your entries take precedence over extracted values. The original OCR transcript remains in the report for review.</p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className={lbl}>Brand<input aria-label="Corrected brand" value={brand} onChange={(e) => setBrand(e.target.value)} disabled={busy} className={field} /></label>
          <label className={lbl}>Variant or flavour<input aria-label="Corrected variant" value={variant} onChange={(e) => setVariant(e.target.value)} disabled={busy} className={field} /></label>
          <label className={lbl}>Pack size and unit<input aria-label="Corrected pack size" placeholder="200 g or 2 x 100 g" value={packSize} onChange={(e) => setPackSize(e.target.value)} disabled={busy} className={field} /></label>
          <label className={lbl}>Nutrition basis<select aria-label="Corrected nutrition basis" value={nutritionBasis} onChange={(e) => setNutritionBasis(e.target.value as "per_100g" | "per_100ml" | "")} disabled={busy} className={field}><option value="">Not stated</option><option value="per_100g">Per 100 g</option><option value="per_100ml">Per 100 ml</option></select></label>
          <label className={`${lbl} sm:col-span-2`}>Ingredients<textarea aria-label="Corrected ingredients" value={ingredients} onChange={(e) => setIngredients(e.target.value)} disabled={busy} rows={3} className={field} /></label>
          <label className={`${lbl} sm:col-span-2`}>Nutrition values<textarea aria-label="Corrected nutrition values" placeholder={'One per line, e.g. energy: 450 kcal\nprotein: 8 g\nsodium: 320 mg'} value={nutritionText} onChange={(e) => setNutritionText(e.target.value)} disabled={busy} rows={4} className={`${field} font-mono`} /></label>
        </div>
      </details>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p id="upload-help" className="max-w-xl text-xs leading-5 text-muted">
          Photos use OCR (or Claude when configured) and can be misread. Photograph the ingredients and
          nutrition panel flat and sharp, and check the read text in the report against the pack. A page saved from the browser (Ctrl+S or ⌘S) is read as saved, with nothing fetched. Choosing
          the shop lets alternatives come from products analysed from the same shop.
        </p>
        <button type="submit" disabled={busy} className={`${buttonClass.primary} shrink-0`}>
          {busy ? <Spinner className="border-white border-t-transparent" /> : <IconUpload className="h-4 w-4" />}
          {busy ? "Reading…" : "Upload and analyse"}
        </button>
      </div>
      {busy ? (
        <div role="status" aria-live="polite" className="animate-fade-up rounded-xl bg-brand-50 p-3 text-sm text-forest">
          <p className="font-medium">Uploading and reading the file…</p>
          <p className="mt-0.5 text-xs text-slate-700">Photos are read with OCR, which can take several seconds. The report opens when it is ready.</p>
          <span className="mt-2 block h-1 overflow-hidden rounded-full bg-white"><span className="skeleton block h-full w-full" /></span>
        </div>
      ) : null}
      {apiError ? <ErrorState title="The file could not be analysed" message={apiError.message} code={apiError.code} /> : null}
    </form>
  );

  const manualForm = (
    <form id="manual-entry-form" onSubmit={onManualSubmit} noValidate className="space-y-5">
      <div>
        <h3 className="text-base font-semibold text-ink">Enter product details manually</h3>
        <p className="mt-1 text-xs text-muted">These details are saved as user-entered, unverified information. Leave anything unknown blank.</p>
      </div>
      <fieldset className="grid gap-4 sm:grid-cols-2">
        <legend className="sr-only">Product identity</legend>
        <label className={lbl}>Product name <span className="text-[#8f3530]">*</span><input required aria-label="Manual product name" value={manualName} onChange={(e) => setManualName(e.target.value)} disabled={manualBusy} className={field} /></label>
        <label className={lbl}>Brand<input aria-label="Manual brand" value={manualBrand} onChange={(e) => setManualBrand(e.target.value)} disabled={manualBusy} className={field} /></label>
        <label className={lbl}>Variant or flavour<input aria-label="Manual variant" value={manualVariant} onChange={(e) => setManualVariant(e.target.value)} disabled={manualBusy} className={field} /></label>
        {categories.length ? <label className={lbl}>Category<select aria-label="Manual category" value={category} onChange={(e) => setCategory(e.target.value)} disabled={manualBusy} className={field}><option value="">Unknown</option>{categories.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label> : null}
        <div className="flex gap-2">
          <label className={`${lbl} min-w-0 flex-1`}>Pack size<input type="number" min="0.001" step="any" aria-label="Manual pack size" value={manualPackSize} onChange={(e) => setManualPackSize(e.target.value)} disabled={manualBusy} className={field} /></label>
          <label className={lbl}>Unit<select aria-label="Manual pack unit" value={manualPackUnit} onChange={(e) => setManualPackUnit(e.target.value as "g" | "ml")} disabled={manualBusy} className={field}><option value="g">g</option><option value="ml">ml</option></select></label>
        </div>
        <label className={lbl}>Selling price (INR)<input type="number" min="0.01" step="0.01" aria-label="Manual selling price INR" value={manualPrice} onChange={(e) => setManualPrice(e.target.value)} disabled={manualBusy} className={field} /></label>
      </fieldset>
      <fieldset className="grid gap-4 sm:grid-cols-2">
        <legend className="sr-only">Label details</legend>
        <label className={`${lbl} sm:col-span-2`}>Ingredients<textarea aria-label="Manual ingredients" placeholder="Copy the ingredient list from the pack, in order" value={manualIngredients} onChange={(e) => setManualIngredients(e.target.value)} disabled={manualBusy} rows={3} className={field} /></label>
        <label className={lbl}>Nutrition basis<select aria-label="Manual nutrition basis" value={manualNutritionBasis} onChange={(e) => setManualNutritionBasis(e.target.value as "per_100g" | "per_100ml" | "")} disabled={manualBusy} className={field}><option value="">Not stated</option><option value="per_100g">Per 100 g</option><option value="per_100ml">Per 100 ml</option></select></label>
        <label className={`${lbl} sm:col-span-2`}>Nutrition values<textarea aria-label="Manual nutrition values" placeholder={'One per line, e.g. energy: 450 kcal\nprotein: 8 g\nsodium: 320 mg'} value={manualNutritionText} onChange={(e) => setManualNutritionText(e.target.value)} disabled={manualBusy} rows={5} className={`${field} font-mono`} /></label>
      </fieldset>
      <div className="flex justify-end">
        <button type="submit" disabled={manualBusy} className={buttonClass.primary}>
          {manualBusy ? <Spinner className="border-white border-t-transparent" /> : null}{manualBusy ? "Analysing…" : "Save and analyse manual details"}
        </button>
      </div>
      {manualError ? <ErrorState title="Manual entry could not be analysed" message={manualError.message} code={manualError.code} /> : null}
    </form>
  );

  if (mode === "upload") return uploadForm;
  if (mode === "manual") return manualForm;
  return (
    <section id="offline-upload" className="space-y-6" aria-labelledby="offline-upload-heading">
      <div>
        <h2 id="offline-upload-heading" className="text-lg font-semibold text-ink">Continue without automatic page access</h2>
        <p className="mt-1 text-sm text-muted">Upload a saved page, packaging images, or enter the label details yourself. Uploaded evidence is user-supplied and not independently verified.</p>
      </div>
      <div className="rounded-[var(--radius-card)] border border-line bg-white p-5 shadow-[var(--shadow-card)]">{uploadForm}</div>
      <div className="rounded-[var(--radius-card)] border border-line bg-white p-5 shadow-[var(--shadow-card)]">{manualForm}</div>
    </section>
  );
}
