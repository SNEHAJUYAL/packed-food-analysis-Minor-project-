"use client";

import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { humanize } from "@/lib/format";
import { scoreColor } from "./ui";

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
              <CartesianGrid horizontal={false} stroke="#eef1ea" />
              <XAxis type="number" domain={[0, 100]} ticks={[0, 25, 50, 75, 100]} tick={{ fontSize: 12, fill: "#5f6961" }} />
              <YAxis type="category" dataKey="label" width={96} tick={{ fontSize: 12, fill: "#202b25" }} />
              <Tooltip
                cursor={{ fill: "#eaf0e8" }}
                formatter={(v) => [`${v} / 100`, "Score"]}
                contentStyle={{ borderRadius: 12, borderColor: "#e5e8e1", fontSize: 12 }}
              />
              <Bar dataKey="score" radius={[0, 4, 4, 0]} isAnimationActive={false} barSize={16}>
                {scored.map((d) => (
                  <Cell key={d.name} fill={scoreColor(d.score)} />
                ))}
                <LabelList dataKey="score" position="right" style={{ fontSize: 12, fill: "#202b25" }} />
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
