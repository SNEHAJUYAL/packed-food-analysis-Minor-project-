import Link from "next/link";
import { BrandMark } from "./Brand";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { href: "/analyze", label: "Analyze a product" },
      { href: "/products", label: "Product explorer" },
      { href: "/compare", label: "Compare products" },
      { href: "/alternatives", label: "Alternatives" },
    ],
  },
  {
    title: "Data",
    links: [
      { href: "/dashboard", label: "Dashboard" },
      { href: "/insights", label: "Insights & analytics" },
      { href: "/methodology", label: "Methodology and limitations" },
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="bg-deep text-sage/80">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1.6fr_1fr_1fr] lg:px-10">
        <div className="space-y-4 text-sm">
          <BrandMark inverted />
          <p className="max-w-md leading-6">
            Consumer decision-support assessment, not a medical or clinical score. Product data comes from pages you submit,
            your uploads, and Open Food Facts (ODbL).
          </p>
          <p className="max-w-md text-xs leading-5 text-sage/60">
            Minor project, MSIT (GGSIPU), New Delhi. Idea by Sneha Juyal; team Sneha Juyal, Radhika, Shinjini; guides Dr.
            Sudesh Pahal and Dr. Neeru Rathee.
          </p>
        </div>
        {COLUMNS.map((c) => (
          <nav key={c.title} aria-label={c.title}>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-white">{c.title}</p>
            <ul className="mt-4 space-y-2.5 text-sm">
              {c.links.map((l) => (
                <li key={l.href}><Link className="transition hover:text-white" href={l.href}>{l.label}</Link></li>
              ))}
            </ul>
          </nav>
        ))}
      </div>
    </footer>
  );
}
