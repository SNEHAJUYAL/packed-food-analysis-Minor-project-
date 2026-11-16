"use client";

import { useEffect, useState } from "react";
import { IconAlert } from "./icons";
import { ApiError, BACKEND_DOWN, api } from "@/lib/api";

const DB_DOWN =
  "The API is running but cannot reach the database. Check that PostgreSQL is running and DATABASE_URL in .env is " +
  "right, then run ./run.sh migrate and ./run.sh seed.";

/** Says plainly when the API or its database is down, instead of every page failing with a bare error. */
export function ServiceStatus() {
  const [problem, setProblem] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    api
      .health(ctrl.signal)
      .then((h) => setProblem(h.database === "ok" ? null : DB_DOWN))
      .catch((e: unknown) => {
        if (ctrl.signal.aborted) return;
        const code = e instanceof ApiError ? e.code : "network_error";
        if (code === "backend_unreachable" || code === "network_error") setProblem(BACKEND_DOWN);
      });
    return () => ctrl.abort();
  }, []);

  if (!problem) return null;
  return (
    <div role="alert" className="flex gap-3 rounded-2xl border border-[#f1d2a8] bg-[#fdf6ec] p-4 text-sm text-[#5c3a10]">
      <IconAlert className="mt-0.5 h-5 w-5 shrink-0 text-[#b87422]" />
      <div>
        <p className="font-semibold text-[#4a2e0b]">The app cannot analyse anything right now</p>
        <p className="mt-1">{problem}</p>
      </div>
    </div>
  );
}
