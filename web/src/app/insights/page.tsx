import type { Metadata } from "next";
import { InsightsView } from "@/components/InsightsView";

export const metadata: Metadata = { title: "Insights & analytics" };

export default function InsightsPage() {
  return <InsightsView />;
}
