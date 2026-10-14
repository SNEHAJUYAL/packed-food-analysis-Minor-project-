"use client";

import { useSearchParams } from "next/navigation";
import { CompareView } from "./CompareView";
import { parseIds } from "@/lib/format";

export function CompareClient() {
  const params = useSearchParams();
  const ids = parseIds(params?.get("ids"));
  return <CompareView key={ids.join(",")} ids={ids} />;
}
