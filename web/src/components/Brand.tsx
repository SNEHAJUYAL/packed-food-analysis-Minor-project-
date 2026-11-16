import { IconLeaf } from "./icons";

export function BrandMark({ compact = false, inverted = false }: { compact?: boolean; inverted?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <span
        aria-hidden="true"
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${inverted ? "bg-sage text-deep" : "bg-forest text-sage"}`}
      >
        <IconLeaf className="h-5 w-5" />
      </span>
      {compact ? null : (
        <span className="leading-tight">
          <span className={`block font-display text-[15px] font-bold ${inverted ? "text-white" : "text-ink"}`}>Food Intelligence</span>
          <span className={`block text-[11px] ${inverted ? "text-sage/80" : "text-muted"}`}>Know your food</span>
        </span>
      )}
    </span>
  );
}
