import { useQuery } from "@tanstack/react-query";
import { fetchScreen } from "../api/client";
import type { ScreenRow } from "../types/screen";
import { RecSummaryBar, UniverseTable } from "../components/UniverseTable";

export default function UniversePage() {
  const screen = useQuery({
    queryKey: ["screen", "all"],
    queryFn: () => fetchScreen("all"),
    staleTime: 120_000,
  });

  const rows = (screen.data?.rows || []) as ScreenRow[];

  return (
    <section>
      <div className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Full universe</p>
        <h1 className="mt-1 font-display text-4xl font-bold tracking-tight text-ink">Market rankings</h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          {screen.data
            ? `${screen.data.count} stocks ranked by rating and composite score.`
            : "Loading the full screened universe…"}
        </p>
      </div>

      {rows.length > 0 && (
        <div className="mb-8">
          <RecSummaryBar rows={rows} />
        </div>
      )}

      <UniverseTable rows={rows} isLoading={screen.isLoading} showSector />
    </section>
  );
}
