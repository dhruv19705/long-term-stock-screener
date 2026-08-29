export function FitScoreBar({ score, label = "Profile Fit" }: { score: number; label?: string }) {
  const color = score >= 80 ? "bg-good" : score >= 60 ? "bg-accent" : score >= 40 ? "bg-warn" : "bg-danger";
  return (
    <div className="w-full">
      <div className="mb-1 flex justify-between text-xs text-slate-600">
        <span>{label || "Fit"}</span>
        <span className="font-semibold text-ink">{score.toFixed(0)}</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full ${color}`} style={{ width: `${Math.min(100, Math.max(0, score))}%` }} />
      </div>
    </div>
  );
}
