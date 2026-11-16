"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { validateUrl } from "./AnalyzeForm";
import { IconArrowRight, IconLink } from "./icons";
import { buttonClass } from "./ui";

/** Hero URL box: validates, then hands the URL to the real analysis workflow on /analyze. */
export function LandingAnalyze() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const problem = validateUrl(url);
    setError(problem);
    if (problem) return;
    router.push(`/analyze?url=${encodeURIComponent(url.trim())}&run=1`);
  }

  return (
    <form onSubmit={onSubmit} noValidate className="w-full max-w-2xl">
      <label htmlFor="hero-url" className="sr-only">Product page URL</label>
      <div className="flex flex-col gap-2 rounded-2xl border border-line bg-white p-2 shadow-[var(--shadow-lift)] sm:flex-row">
        <div className="relative min-w-0 flex-1">
          <IconLink className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
          <input
            id="hero-url"
            type="url"
            inputMode="url"
            autoComplete="url"
            placeholder="Paste a product page URL"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? "hero-url-error" : undefined}
            className="w-full rounded-xl border-0 bg-transparent py-3.5 pl-12 pr-3 text-base text-ink placeholder:text-slate-400 focus:outline-none focus:ring-0"
          />
        </div>
        <button type="submit" className={`${buttonClass.primary} sm:px-6`}>
          Analyze Product <IconArrowRight className="h-4 w-4" />
        </button>
      </div>
      {error ? <p id="hero-url-error" role="alert" className="mt-2 text-sm font-medium text-[#8f3530]">{error}</p> : null}
      <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
        <Link href="/products" className={`${buttonClass.secondary}`}>Explore Products</Link>
        <Link href="/analyze#packaging-image-upload" className="font-medium text-forest underline-offset-4 hover:underline">
          or upload a pack photo
        </Link>
      </div>
    </form>
  );
}
