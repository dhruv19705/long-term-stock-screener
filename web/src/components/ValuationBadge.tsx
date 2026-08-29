const tones: Record<string, string> = {
  Under: "bg-emerald-50 text-emerald-800 ring-emerald-200/70",
  Fair: "bg-slate-50 text-slate-700 ring-slate-200/70",
  Over: "bg-orange-50 text-orange-900 ring-orange-200/70",
  Unknown: "bg-slate-50 text-slate-500 ring-slate-200/70",
};

export function ValuationBadge({ value }: { value: string }) {
  const v = value || "Unknown";
  return (
    <span className={`inline-flex rounded-md px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${tones[v] || tones.Unknown}`}>
      {v}
    </span>
  );
}
