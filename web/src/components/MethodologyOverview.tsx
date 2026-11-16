import {
  IconBook, IconChart, IconColumns, IconDatabase, IconLeaf, IconScan, IconShield, IconSparkle, IconTag,
} from "./icons";

/**
 * Plain-language overview of the pipeline as implemented (src/extract, src/normalise, src/analyse,
 * src/score, src/recommend). Deterministic rules are described as rules, not machine learning.
 */
const STAGES = [
  {
    icon: IconDatabase,
    title: "Data acquisition",
    body: "A product page you submit is fetched once with SSRF checks, a size limit and per-site pacing, only where robots.txt allows. Uploads (pack photo, screenshot, saved .html page) and manual entries fetch nothing. The reference catalogue is an Open Food Facts India subset (ODbL) plus labelled synthetic demo records.",
  },
  {
    icon: IconScan,
    title: "Extraction and OCR",
    body: "Structured data (schema.org JSON-LD) is read first, then the page HTML (nutrition tables, ingredient blocks). Photos are read offline with Tesseract OCR and parsed with fixed rules; an optional Claude vision fallback only keeps values that appear in its transcript of the label. Photo-reading accuracy on real camera photos has not been measured.",
  },
  {
    icon: IconTag,
    title: "Product identity matching",
    body: "A new product is compared with stored Open Food Facts records by brand and name (fuzzy token-set similarity, cutoff 85). A match is shown for reference only; its values are never merged into the record. Flavours and pack sizes are not merged.",
  },
  {
    icon: IconChart,
    title: "Nutrition normalisation",
    body: "Every nutrient is converted to per 100 g or per 100 ml. Per-serving values are scaled using the declared serving size, and sodium is derived from salt where only salt is printed. Each value keeps an evidence label; missing stays unknown, never zero.",
  },
  {
    icon: IconSparkle,
    title: "Ingredient classification",
    body: "The ingredient list is split in label order (including compound ingredients) and matched to a curated dictionary of terms, classes and INS additive codes, with fuzzy matching flagged as uncertain. Allergens are detected from the text. Classes describe processing and disclosure, not harm.",
  },
  {
    icon: IconShield,
    title: "Marketing claim evaluation",
    body: "Printed claims such as “High Protein” or “Low Sugar” are checked against FSSAI (Advertising and Claims) conditions stored in data/reference with their clause. Results are prompts for review, not legal findings; claims needing missing data are marked “cannot be verified”.",
  },
  {
    icon: IconColumns,
    title: "Scoring",
    body: "Five dimensions (nutrition, ingredients, transparency, claims, value for money) are scored 0–100 by deterministic formulas from config/scoring.json and combined with fixed weights into an overall score and grade A–E. Unscored dimensions are left out and the weights renormalised; no overall score is given without a nutrition score.",
  },
  {
    icon: IconLeaf,
    title: "Recommendation logic",
    body: "Alternatives are stored products in the same category and nutrition basis that beat the product on your chosen preference. Ties are broken by TF-IDF text similarity (cosine) over name, brand, category and ingredients. Each suggestion carries a rationale.",
  },
  {
    icon: IconBook,
    title: "Model methodology",
    body: "No independently trained, product-specific machine-learning model is used. The pretrained components are the Tesseract OCR engine and, if configured, the Claude vision model. TF-IDF similarity is fitted on the stored products at request time. Everything else is rule-based and reproducible.",
  },
];

export function MethodologyOverview() {
  return (
    <section aria-label="Pipeline overview" className="space-y-6">
      <ol className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {STAGES.map(({ icon: Icon, title, body }, i) => (
          <li key={title} className="rounded-[var(--radius-card)] border border-line bg-white p-5 shadow-[var(--shadow-card)]">
            <div className="flex items-center gap-3">
              <span aria-hidden="true" className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-forest"><Icon className="h-5 w-5" /></span>
              <span className="font-display text-xs font-bold text-brand-500">0{i + 1}</span>
            </div>
            <h2 className="mt-3 text-base font-semibold text-ink">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-muted">{body}</p>
          </li>
        ))}
      </ol>
      <div className="rounded-[var(--radius-card)] bg-deep p-6 text-sage">
        <h2 className="text-base font-semibold text-white">Informational, not medical</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-sage/85">
          Product scores are decision-support indicators built from the listing&apos;s own information. They are not medical,
          clinical or safety assessments, the thresholds are prototype values still to be calibrated, and they are not
          endorsed by FSSAI or any other authority.
        </p>
      </div>
    </section>
  );
}
