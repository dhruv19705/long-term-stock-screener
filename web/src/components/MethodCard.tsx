import type { ReactNode } from "react";

type Props = {
  title: string;
  eyebrow?: string;
  children: ReactNode;
  className?: string;
};

export function MethodCard({ title, eyebrow, children, className = "" }: Props) {
  return (
    <article className={`rounded-2xl bg-white/90 p-6 ring-1 ring-slate-200/80 ${className}`}>
      {eyebrow && (
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">{eyebrow}</p>
      )}
      <h2 className={`font-display text-xl font-semibold text-ink ${eyebrow ? "mt-1" : ""}`}>{title}</h2>
      <div className="mt-4 space-y-3 text-sm leading-relaxed text-slate-600">{children}</div>
    </article>
  );
}

type WeightRow = { pillar: string; weight: string; metrics: string };

export function WeightTable({ rows }: { rows: WeightRow[] }) {
  return (
    <div className="mt-4 overflow-x-auto rounded-xl ring-1 ring-slate-200/80">
      <table className="w-full min-w-[480px] text-left text-sm">
        <thead className="bg-slate-50/80">
          <tr>
            <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Pillar</th>
            <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Weight</th>
            <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Key metrics</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row) => (
            <tr key={row.pillar} className="bg-white/60">
              <td className="px-4 py-3 font-medium text-ink">{row.pillar}</td>
              <td className="px-4 py-3 tabular-nums text-accent">{row.weight}</td>
              <td className="px-4 py-3 text-slate-600">{row.metrics}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
