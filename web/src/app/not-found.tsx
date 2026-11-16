import Link from "next/link";
import { buttonClass } from "@/components/ui";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-md space-y-4 py-20 text-center">
      <p className="font-display text-5xl font-extrabold text-sage">404</p>
      <h1 className="text-2xl font-bold text-ink">Page not found</h1>
      <p className="text-sm text-muted">The page you asked for does not exist.</p>
      <div className="flex justify-center gap-2">
        <Link href="/dashboard" className={buttonClass.primary}>Go to the dashboard</Link>
        <Link href="/" className={buttonClass.secondary}>Go to the start page</Link>
      </div>
    </div>
  );
}
