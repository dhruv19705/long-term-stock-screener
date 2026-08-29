import type { QuestionAnswer } from "../api/client";

const signalColor: Record<string, string> = {
  good: "border-l-good bg-emerald-50/70",
  warn: "border-l-warn bg-amber-50/70",
  bad: "border-l-danger bg-rose-50/70",
  unknown: "border-l-slate-400 bg-slate-50",
};

export function AnalystQuestionCard({ q }: { q: QuestionAnswer }) {
  return (
    <article
      className={`rounded-lg border border-slate-200/80 border-l-4 p-4 shadow-sm ${
        signalColor[q.signal] || signalColor.unknown
      }`}
    >
      <div className="mb-2 flex items-start justify-between gap-3">
        <h3 className="font-display text-lg font-semibold text-ink">{q.question}</h3>
        <span className="shrink-0 text-xs uppercase tracking-wider text-slate-500">{q.signal}</span>
      </div>
      <p className="mb-2 text-sm text-slate-600">{q.answer}</p>
      <div className="flex flex-wrap gap-2 text-xs text-slate-500">
        <span className="rounded bg-white/80 px-2 py-0.5">{q.dimension}</span>
        {Object.entries(q.metrics || {})
          .slice(0, 4)
          .map(([k, v]) => (
            <span key={k} className="rounded bg-white/80 px-2 py-0.5">
              {k}: {typeof v === "number" ? v.toFixed(2) : String(v)}
            </span>
          ))}
      </div>
    </article>
  );
}
