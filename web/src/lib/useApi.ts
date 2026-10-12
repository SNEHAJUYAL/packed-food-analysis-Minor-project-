"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "./api";

export type ApiState<T> =
  | { kind: "loading" }
  | { kind: "error"; error: ApiError }
  | { kind: "ready"; data: T };

const LOADING = { kind: "loading" } as const;

/**
 * Run `fn` whenever `deps` change, aborting the previous call. The state is keyed by the
 * request, so a new request reads as "loading" until its own result arrives.
 */
export function useApi<T>(fn: ((signal: AbortSignal) => Promise<T>) | null, deps: unknown[]): [ApiState<T>, () => void] {
  const [nonce, setNonce] = useState(0);
  const [result, setResult] = useState<{ key: string; state: ApiState<T> } | null>(null);
  const retry = useCallback(() => setNonce((n) => n + 1), []);
  const key = `${JSON.stringify(deps)}#${nonce}`;

  useEffect(() => {
    if (!fn) return;
    const ctrl = new AbortController();
    fn(ctrl.signal)
      .then((data) => {
        if (!ctrl.signal.aborted) setResult({ key, state: { kind: "ready", data } });
      })
      .catch((e: unknown) => {
        if (ctrl.signal.aborted || (e as Error)?.name === "AbortError") return;
        const error = e instanceof ApiError ? e : new ApiError(0, "error", "Something went wrong.");
        setResult({ key, state: { kind: "error", error } });
      });
    return () => ctrl.abort();
    // `fn` is recreated each render; `key` captures everything it depends on.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return [result && result.key === key ? result.state : LOADING, retry];
}
