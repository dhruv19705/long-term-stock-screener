import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { ScreenRow } from "../types/screen";
import { REC_ORDER, formatTicker, recRank, sectorLabel } from "../types/screen";
import { RecommendationBadge } from "./RecommendationBadge";
import { ValuationBadge } from "./ValuationBadge";

type Props = {
  rows: ScreenRow[];
  isLoading?: boolean;
  sectorFilter?: string;
  showSector?: boolean;
};

const thBase = "py-3.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500";
const tdBase = "py-3.5 align-middle";

export function UniverseTable({ rows, isLoading, sectorFilter, showSector = true }: Props) {
  const [search, setSearch] = useState("");
  const [recFilter, setRecFilter] = useState<string>("all");
  const [sector, setSector] = useState<string>(sectorFilter || "all");

  const sectors = useMemo(() => {
    const set = new Set(rows.map((r) => r.sector_focus));
    return Array.from(set).sort();
  }, [rows]);

  const filtered = useMemo(() => {
    const q = search.trim().toUpperCase();
    return rows
      .filter((r) => {
        if (recFilter !== "all" && r.recommendation !== recFilter) return false;
        const activeSector = sectorFilter || sector;
        if (activeSector !== "all" && r.sector_focus !== activeSector) return false;
        if (!q) return true;
        return r.stock.toUpperCase().includes(q) || formatTicker(r.stock).toUpperCase().includes(q);
      })
      .sort((a, b) => {
        const dr = recRank(b.recommendation) - recRank(a.recommendation);
        if (dr !== 0) return dr;
        return b.composite_score - a.composite_score;
      });
  }, [rows, search, recFilter, sector, sectorFilter]);

  const recCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const r of REC_ORDER) counts[r] = 0;
    for (const row of rows) {
      if (row.recommendation in counts) counts[row.recommendation] += 1;
    }
    return counts;
  }, [rows]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {REC_ORDER.map((rec) => (
          <button
            key={rec}
            type="button"
            onClick={() => setRecFilter(recFilter === rec ? "all" : rec)}
            className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${
              recFilter === rec
                ? "bg-ink text-white shadow-sm"
                : "bg-white/90 text-slate-600 ring-1 ring-slate-200/80 hover:ring-slate-300"
            }`}
          >
            {rec}
            <span className="ml-1.5 opacity-70">{recCounts[rec] ?? 0}</span>
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="relative min-w-[200px] flex-1">
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search ticker…"
            className="w-full rounded-xl border-0 bg-white/90 py-2.5 pl-10 pr-4 text-sm shadow-sm ring-1 ring-slate-200/80 placeholder:text-slate-400 focus:ring-2 focus:ring-accent/40"
          />
          <svg className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z" />
          </svg>
        </div>
        {!sectorFilter && (
          <select
            value={sector}
            onChange={(e) => setSector(e.target.value)}
            className="rounded-xl border-0 bg-white/90 px-4 py-2.5 text-sm shadow-sm ring-1 ring-slate-200/80 focus:ring-2 focus:ring-accent/40"
          >
            <option value="all">All sectors</option>
            {sectors.map((s) => (
              <option key={s} value={s}>
                {sectorLabel(s)}
              </option>
            ))}
          </select>
        )}
        <p className="flex items-center text-sm text-slate-500">
          Showing <strong className="mx-1 text-ink">{filtered.length}</strong> of {rows.length}
        </p>
      </div>

      <div className="overflow-hidden rounded-2xl bg-white/95 shadow-sm ring-1 ring-slate-200/60">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] table-fixed text-left text-sm">
            <colgroup>
              <col className="w-14" />
              <col className={showSector ? "w-[22%]" : "w-[32%]"} />
              {showSector && <col className="w-[14%]" />}
              <col className="w-[120px]" />
              <col className="w-20" />
              <col className="w-[100px]" />
              <col className="w-16" />
            </colgroup>
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/80">
                <th className={`${thBase} pl-6 pr-2 text-left`}>#</th>
                <th className={`${thBase} px-5 text-left`}>Stock</th>
                {showSector && <th className={`${thBase} px-5 text-left`}>Sector</th>}
                <th className={`${thBase} px-5 text-left`}>Rating</th>
                <th className={`${thBase} px-5 text-right`}>Score</th>
                <th className={`${thBase} px-5 text-left`}>Valuation</th>
                <th className={`${thBase} pl-5 pr-6 text-right`}>Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((row, idx) => (
                <tr key={row.stock} className="group transition hover:bg-slate-50/80">
                  <td className={`${tdBase} pl-6 pr-2 tabular-nums text-slate-400`}>{idx + 1}</td>
                  <td className={`${tdBase} px-5`}>
                    <Link
                      to={`/stock/${encodeURIComponent(row.stock)}`}
                      className="font-semibold text-ink group-hover:text-accent"
                    >
                      {formatTicker(row.stock)}
                    </Link>
                  </td>
                  {showSector && (
                    <td className={`${tdBase} px-5 text-slate-600`}>{sectorLabel(row.sector_focus)}</td>
                  )}
                  <td className={`${tdBase} px-5`}>
                    <div className="flex flex-col gap-0.5">
                      <RecommendationBadge value={row.recommendation} />
                      {row.calibration_applied && row.raw_recommendation && row.raw_recommendation !== row.recommendation && (
                        <span className="text-[10px] text-slate-400" title={`Was ${row.raw_recommendation}`}>
                          adj.
                        </span>
                      )}
                    </div>
                  </td>
                  <td className={`${tdBase} px-5 text-right font-semibold tabular-nums text-ink`}>
                    {row.composite_score.toFixed(1)}
                  </td>
                  <td className={`${tdBase} px-5`}>
                    <ValuationBadge value={row.valuation} />
                  </td>
                  <td className={`${tdBase} pl-5 pr-6 text-right tabular-nums text-slate-600`}>
                    {row.stock_risk_score != null ? row.stock_risk_score.toFixed(0) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {isLoading && (
          <div className="border-t border-slate-100 px-6 py-8 text-center text-sm text-slate-500">
            Loading market data… first run may take a minute.
          </div>
        )}
        {!isLoading && filtered.length === 0 && (
          <div className="border-t border-slate-100 px-6 py-8 text-center text-sm text-slate-500">
            No stocks match your filters.
          </div>
        )}
      </div>
    </div>
  );
}

export function RecSummaryBar({ rows }: { rows: ScreenRow[] }) {
  const total = rows.length;
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const r of REC_ORDER) c[r] = 0;
    for (const row of rows) {
      if (row.recommendation in c) c[row.recommendation] += 1;
    }
    return c;
  }, [rows]);

  const colors: Record<string, string> = {
    "STRONG BUY": "bg-emerald-500",
    BUY: "bg-teal-500",
    HOLD: "bg-slate-400",
    AVOID: "bg-amber-500",
    SELL: "bg-rose-500",
  };

  return (
    <div className="rounded-2xl bg-white/95 p-5 shadow-sm ring-1 ring-slate-200/60">
      <div className="mb-3 flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-ink">Rating distribution</h3>
        <span className="text-xs text-slate-500">{total} stocks</span>
      </div>
      <div className="flex h-2 overflow-hidden rounded-full bg-slate-100">
        {REC_ORDER.map((rec) => {
          const pct = total ? (counts[rec] / total) * 100 : 0;
          if (pct === 0) return null;
          return (
            <div
              key={rec}
              className={`${colors[rec]} transition-all`}
              style={{ width: `${pct}%` }}
              title={`${rec}: ${counts[rec]}`}
            />
          );
        })}
      </div>
      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5">
        {REC_ORDER.map((rec) => (
          <div key={rec} className="flex items-center gap-1.5 text-xs text-slate-600">
            <span className={`h-2 w-2 rounded-full ${colors[rec]}`} />
            {rec} <span className="font-semibold text-ink">{counts[rec]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
