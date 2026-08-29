const styles: Record<string, { pill: string; dot: string }> = {
  "STRONG BUY": { pill: "bg-emerald-50 text-emerald-800 ring-emerald-200/80", dot: "bg-emerald-500" },
  BUY: { pill: "bg-teal-50 text-teal-800 ring-teal-200/80", dot: "bg-teal-500" },
  HOLD: { pill: "bg-slate-100 text-slate-700 ring-slate-200/80", dot: "bg-slate-400" },
  AVOID: { pill: "bg-amber-50 text-amber-900 ring-amber-200/80", dot: "bg-amber-500" },
  SELL: { pill: "bg-rose-50 text-rose-800 ring-rose-200/80", dot: "bg-rose-500" },
};

export function RecommendationBadge({ value, size = "sm" }: { value: string; size?: "sm" | "md" }) {
  const s = styles[value] || styles.HOLD;
  const sizeClass = size === "md" ? "px-3 py-1 text-xs" : "px-2.5 py-0.5 text-[11px]";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold uppercase tracking-wide ring-1 ring-inset ${sizeClass} ${s.pill}`}
    >
      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${s.dot}`} />
      {value}
    </span>
  );
}
