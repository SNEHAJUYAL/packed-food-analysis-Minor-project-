import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="border-t border-line bg-white">
      <div className="mx-auto grid max-w-6xl gap-4 px-4 py-8 text-sm text-muted sm:px-6 md:grid-cols-[2fr_1fr]">
        <div className="space-y-2">
          <p className="font-medium text-ink">Food Decision Intelligence</p>
          <p>
            Consumer decision-support assessment, not a medical or clinical score. Product data from listings and
            Open Food Facts (ODbL); see the <Link className="underline" href="/methodology">methodology</Link> for sources.
          </p>
          <p>
            Minor project, MSIT (GGSIPU), New Delhi. Idea by Sneha Juyal; team Sneha Juyal, Radhika, Shinjini; guides Dr.
            Sudesh Pahal and Dr. Neeru Rathee.
          </p>
        </div>
        <nav aria-label="Footer" className="md:justify-self-end">
          <ul className="space-y-1">
            <li><Link className="hover:underline" href="/">Analyse a product</Link></li>
            <li><Link className="hover:underline" href="/products">Stored products</Link></li>
            <li><Link className="hover:underline" href="/compare">Compare</Link></li>
            <li><Link className="hover:underline" href="/methodology">Methodology and limitations</Link></li>
          </ul>
        </nav>
      </div>
    </footer>
  );
}
