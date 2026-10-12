"use client";

import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { humanize } from "@/lib/format";

export interface DimensionDatum {
  name: string;
  score: number | null;
}

/** Horizontal bars, 0–100. Unscored dimensions are listed as "not scored", never drawn as zero. */
export function DimensionChart({ data, height = 220 }: { data: DimensionDatum[]; height?: number }) {
  const scored = data.filter((d) => d.score !== null && d.score !== undefined);
  const unscored = data.filter((d) => d.score === null || d.score === undefined);
  return (
    <figure aria-label="Dimension scores chart" className="w-full">
      {scored.length > 0 ? (
        <div style={{ height }} className="w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={scored.map((d) => ({ ...d, score: Math.round(d.score as number), label: humanize(d.name) }))} layout="vertical" margin={{ top: 4, right: 36, bottom: 4, left: 8 }}>
              <CartesianGrid horizontal={false} stroke="#e3e7ec" />
              <XAxis type="number" domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={{ fontSize: 12, fill: "#5b6676" }} />
              <YAxis type="category" dataKey="label" width={96} tick={{ fontSize: 12, fill: "#1f2a37" }} />
              <Tooltip
                cursor={{ fill: "#eef7f5" }}
                formatter={(v) => [`${v} / 100`, "Score"]}
                contentStyle={{ borderRadius: 8, borderColor: "#e3e7ec", fontSize: 12 }}
              />
              <Bar dataKey="score" radius={[0, 6, 6, 0]} isAnimationActive={false} barSize={18}>
                {scored.map((d) => (
                  <Cell key={d.name} fill="#2f8f7f" />
                ))}
                <LabelList dataKey="score" position="right" style={{ fontSize: 12, fill: "#1f2a37" }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : null}
      {unscored.length > 0 ? (
        <figcaption className="mt-2 text-xs text-muted">
          Not scored: {unscored.map((d) => humanize(d.name)).join(", ")}.
        </figcaption>
      ) : null}
    </figure>
  );
}
