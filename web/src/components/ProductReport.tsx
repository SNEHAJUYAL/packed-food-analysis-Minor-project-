"use client";

import Link from "next/link";
import { ReportView } from "./ReportView";
import { ErrorState, LoadingState } from "./ui";
import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";

export function ProductReport({ id }: { id: string }) {
  const valid = /^\d+$/.test(id);
  const [state, retry] = useApi(valid ? (signal) => api.getProduct(id, signal) : null, [id]);

  if (!valid) {
    return <ErrorState title="Product not found" message="Product ids are whole numbers." action={<Link className="underline" href="/products">Browse stored products</Link>} />;
  }
  if (state.kind === "loading") return <LoadingState label="Loading product report…" />;
  if (state.kind === "error") {
    const notFound = state.error.status === 404;
    return (
      <ErrorState
        title={notFound ? "Product not found" : "Could not load this report"}
        message={state.error.message}
        code={state.error.code}
        action={
          <div className="flex gap-4">
            {!notFound ? (
              <button type="button" onClick={retry} className="underline">
                Try again
              </button>
            ) : null}
            <Link className="underline" href="/products">Browse stored products</Link>
          </div>
        }
      />
    );
  }
  return <ReportView analysis={state.data} />;
}
