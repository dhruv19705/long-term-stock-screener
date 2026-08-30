import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { fetchScreen, fetchSectorSummary } from "../api/client";
import type { ScreenRow } from "../types/screen";
import { RecSummaryBar, UniverseTable } from "../components/UniverseTable";
import { sectorLabel } from "../types/screen";

export default function SectorDashboard() {
  const { sector = "banking" } = useParams<{ sector: string }>();
  const title = sectorLabel(sector);

  const screen = useQuery({
    queryKey: ["screen", sector],
    queryFn: () => fetchScreen(sector),
    staleTime: 120_000,
  });
  const summary = useQuery({
    queryKey: ["summary", sector],
    queryFn: () => fetchSectorSummary(sector),
    staleTime: 120_000,
  });

  const rows = (screen.data?.rows || []) as ScreenRow[];

  return (
    <section>
      <div className="mb-2">
        <Link to="/sectors" className="text-sm text-accent hover:underline">
          ← All sectors
        </Link>
      </div>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Sector view</p>
          <h1 className="mt-1 font-display text-4xl font-bold tracking-tight text-ink">{title}</h1>
          <p className="mt-2 text-slate-600">
            {summary.data
              ? `${summary.data.count} names · avg score ${Number(summary.data.avg_composite || 0).toFixed(1)}`
              : "Loading sector screen…"}
          </p>
        </div>
        <Link
          to="/universe"
          className="rounded-xl bg-white/90 px-4 py-2 text-sm font-medium text-slate-700 ring-1 ring-slate-200/80 hover:ring-accent/40"
        >
          View full universe
        </Link>
      </div>

      {rows.length > 0 && (
        <div className="mb-8">
          <RecSummaryBar rows={rows} />
        </div>
      )}

      <UniverseTable rows={rows} isLoading={screen.isLoading} sectorFilter={sector} showSector={false} />
    </section>
  );
}
