"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState, type KeyboardEvent } from "react";
import { AnalyzeForm } from "./AnalyzeForm";
import { IconCheck, IconLink, IconPencil, IconSearch, IconShield, IconUpload } from "./icons";
import { ProductSearch } from "./ProductSearch";
import { ServiceStatus } from "./ServiceStatus";
import { UploadForm } from "./UploadForm";
import { Note } from "./ui";

type Tab = "search" | "url" | "upload" | "manual";

const TABS: { id: Tab; label: string; hint: string; icon: typeof IconLink }[] = [
  { id: "search", label: "Search by name", hint: "Any product, by name or brand", icon: IconSearch },
  { id: "url", label: "Product URL", hint: "Paste a product page link", icon: IconLink },
  { id: "upload", label: "Packaging image or saved page", hint: "Photo, screenshot or .html", icon: IconUpload },
  { id: "manual", label: "Manual entry", hint: "Type the label details", icon: IconPencil },
];

/** Anchors used by the URL error state's fallback links map to the tab that holds them. */
const HASH_TAB: Record<string, Tab> = {
  "#saved-page-upload": "upload",
  "#packaging-image-upload": "upload",
  "#upload": "upload",
  "#manual-entry-form": "manual",
  "#manual": "manual",
  "#url": "url",
  "#search": "search",
};

const AFTER = [
  "Product identity, pack and price with evidence labels",
  "Nutrition per 100 g/ml with traffic lights",
  "Ingredient classes, INS additives and allergens",
  "Claim checks against FSSAI conditions",
  "Minerals and vitamins where the source declares them",
  "Prices across shops, price history and the cheapest place to buy",
  "Five explained scores, and healthier alternatives from stored products",
];

export function AnalyzeWorkspace() {
  const params = useSearchParams();
  const initialUrl = params?.get("url") ?? "";
  const autoSubmit = params?.get("run") === "1" && Boolean(initialUrl);
  const initialQuery = params?.get("q") ?? "";
  const [tab, setTab] = useState<Tab>(initialUrl ? "url" : "search");

  useEffect(() => {
    const sync = () => {
      const t = HASH_TAB[window.location.hash];
      if (t) {
        setTab(t);
        // Bring the requested form into view once the tab has rendered.
        requestAnimationFrame(() => document.querySelector(window.location.hash)?.scrollIntoView({ block: "start", behavior: "smooth" }));
      }
    };
    sync();
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);

  function onKey(e: KeyboardEvent<HTMLDivElement>) {
    const i = TABS.findIndex((t) => t.id === tab);
    let next = i;
    if (e.key === "ArrowRight") next = (i + 1) % TABS.length;
    else if (e.key === "ArrowLeft") next = (i - 1 + TABS.length) % TABS.length;
    else return;
    e.preventDefault();
    setTab(TABS[next].id);
    document.getElementById(`tab-${TABS[next].id}`)?.focus();
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="min-w-0 space-y-5">
        <ServiceStatus />
        <div role="tablist" aria-label="How to provide the product" onKeyDown={onKey} className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {TABS.map(({ id, label, hint, icon: Icon }) => {
            const on = tab === id;
            return (
              <button
                key={id}
                id={`tab-${id}`}
                type="button"
                role="tab"
                aria-selected={on}
                aria-controls={`panel-${id}`}
                tabIndex={on ? 0 : -1}
                onClick={() => setTab(id)}
                className={`flex items-center gap-3 rounded-2xl border p-3.5 text-left transition ${
                  on ? "border-forest bg-white shadow-[var(--shadow-card)] ring-1 ring-forest" : "border-line bg-white/60 hover:border-brand-300 hover:bg-white"
                }`}
              >
                <span aria-hidden="true" className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${on ? "bg-forest text-sage" : "bg-brand-50 text-forest"}`}>
                  <Icon className="h-5 w-5" />
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-semibold text-ink">{label}</span>
                  <span className="block text-xs text-muted">{hint}</span>
                </span>
              </button>
            );
          })}
        </div>

        <div
          id={`panel-${tab}`}
          role="tabpanel"
          aria-labelledby={`tab-${tab}`}
          className="animate-fade-up rounded-[var(--radius-card)] border border-line bg-white p-5 shadow-[var(--shadow-card)] sm:p-7"
        >
          {tab === "search" ? <ProductSearch initialQuery={initialQuery} /> : null}
          {tab === "url" ? <AnalyzeForm initialUrl={initialUrl} autoSubmit={autoSubmit} /> : null}
          {tab === "upload" ? <UploadForm mode="upload" /> : null}
          {tab === "manual" ? <UploadForm mode="manual" /> : null}
        </div>
        <Note>Search finds products already analysed and products on Open Food Facts. Paste a link, upload a pack photo or type the label for anything else.</Note>
      </div>

      <aside className="space-y-4">
        <section className="rounded-[var(--radius-card)] bg-deep p-5 text-sage">
          <h2 className="text-sm font-semibold text-white">What you get</h2>
          <ul className="mt-3 space-y-2.5 text-sm">
            {AFTER.map((a) => (
              <li key={a} className="flex gap-2.5"><IconCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#9fd3ae]" />{a}</li>
            ))}
          </ul>
        </section>
        <section className="rounded-[var(--radius-card)] border border-line bg-white p-5">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-ink"><IconShield className="h-4 w-4 text-forest" />Evidence, not guesses</h2>
          <p className="mt-2 text-xs leading-5 text-muted">
            Every value is labelled declared, derived, interpreted, verified or unknown. Missing values stay unknown; they are
            never filled in as zero. Uploads and manual entries are marked as user-supplied and unverified.
          </p>
        </section>
      </aside>
    </div>
  );
}
