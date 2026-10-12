import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-md space-y-3 py-16 text-center">
      <h1 className="text-2xl font-semibold text-ink">Page not found</h1>
      <p className="text-sm text-muted">The page you asked for does not exist.</p>
      <p className="text-sm">
        <Link href="/" className="text-brand-700 underline">Go to the start page</Link>
      </p>
    </div>
  );
}
