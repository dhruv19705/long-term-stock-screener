import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchSectors } from "../api/client";
import { sectorLabel } from "../types/screen";

export default function AllSectorsDashboard() {
  const sectors = useQuery({ queryKey: ["sectors-list"], queryFn: fetchSectors });

  const total = (sectors.data?.sectors || []).reduce((n, s) => n + s.ticker_count, 0);

  return (
    <section>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Coverage</p>
          <h1 className="mt-1 font-display text-4xl font-bold tracking-tight text-ink">Sectors</h1>
          <p className="mt-2 text-slate-600">
            {total > 0 ? `${total} tickers across ${sectors.data?.sectors.length ?? 0} model buckets` : "Loading…"}
          </p>
        </div>
        <Link
          to="/universe"
          className="rounded-xl bg-accent px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-accent/90"
        >
          View all rankings →
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {(sectors.data?.sectors || []).map((s) => (
          <Link
            key={s.id}
            to={`/sectors/${s.id}`}
            className="group rounded-2xl bg-white/95 p-5 shadow-sm ring-1 ring-slate-200/60 transition hover:-translate-y-0.5 hover:shadow-md hover:ring-accent/30"
          >
            <div className="flex items-start justify-between">
              <h2 className="font-display text-lg font-semibold capitalize text-ink group-hover:text-accent">
                {sectorLabel(s.id)}
              </h2>
            </div>
            <p className="mt-1 text-sm text-slate-500">{s.display_sector}</p>
            <div className="mt-4 flex items-baseline gap-1">
              <span className="text-3xl font-bold tabular-nums text-ink">{s.ticker_count}</span>
              <span className="text-sm text-slate-500">stocks</span>
            </div>
            {s.cyclical && (
              <span className="mt-3 inline-block rounded-md bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-900 ring-1 ring-amber-200/70">
                Cyclical
              </span>
            )}
          </Link>
        ))}
      </div>
    </section>
  );
}
