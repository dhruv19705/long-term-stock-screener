const tones = {
  good: "border-emerald-200/80 bg-emerald-50/80 text-emerald-900",
  warn: "border-amber-200/80 bg-amber-50/80 text-amber-950",
  neutral: "border-slate-200/80 bg-white/80 text-slate-700",
  accent: "border-sky-200/80 bg-sky-50/80 text-sky-900",
};

export function AxisBadge({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: keyof typeof tones;
}) {
  return (
    <span className={`inline-flex flex-col rounded-lg border px-2.5 py-1.5 text-left ${tones[tone]}`}>
      <span className="text-[10px] font-medium uppercase tracking-wider opacity-60">{label}</span>
      <span className="text-sm font-semibold leading-tight">{value}</span>
    </span>
  );
}
