import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchRecommendations } from "../api/client";
import { FitScoreBar } from "../components/FitScoreBar";
import { AxisBadge } from "../components/AxisBadge";
import { RecommendationBadge } from "../components/RecommendationBadge";
import { formatTicker, sectorLabel } from "../types/screen";
import { loadProfile } from "./Questionnaire";

export default function Recommendations() {
  const profile = loadProfile();

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["recommend", profile?.id, profile?.sector_filter],
    queryFn: () => fetchRecommendations(profile!),
    enabled: !!profile,
  });

  if (!profile) {
    return (
      <div className="mx-auto max-w-lg rounded-2xl bg-white/95 p-10 text-center shadow-sm ring-1 ring-slate-200/60">
        <h1 className="font-display text-2xl font-bold">Set up your profile</h1>
        <p className="mt-2 text-slate-600">Answer a few questions and we&apos;ll match stocks to your risk tolerance.</p>
        <Link
          to="/"
          className="mt-6 inline-block rounded-xl bg-accent px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-accent/90"
        >
          Start profile
        </Link>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-2xl bg-white/95 p-10 text-center shadow-sm ring-1 ring-slate-200/60">
        <p className="text-slate-600">
          Matching universe to <strong>{profile.label}</strong>…
        </p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl bg-white/95 p-8 shadow-sm ring-1 ring-slate-200/60">
        <p className="text-danger">Failed to load recommendations.</p>
        <button type="button" className="mt-3 text-sm font-medium text-accent hover:underline" onClick={() => refetch()}>
          Retry
        </button>
      </div>
    );
  }

  const bySector = data.picks_by_sector || {};

  return (
    <section>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Personalized</p>
          <h1 className="mt-1 font-display text-4xl font-bold tracking-tight">{data.risk_profile.label}</h1>
          <p className="mt-2 max-w-2xl text-slate-600">{data.summary}</p>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          className="rounded-xl bg-white/90 px-4 py-2 text-sm font-medium ring-1 ring-slate-200/80 hover:ring-accent/40 disabled:opacity-50"
          disabled={isFetching}
        >
          {isFetching ? "Refreshing…" : "Refresh"}
        </button>
        <Link
          to="/"
          className="rounded-xl bg-white/90 px-4 py-2 text-sm font-medium ring-1 ring-slate-200/80 hover:ring-accent/40"
        >
          Edit profile
        </Link>
      </div>

      {Object.keys(bySector).length > 0 ? (
        Object.entries(bySector).map(([sector, picks]) => (
          <div key={sector} className="mb-10">
            <h2 className="mb-4 font-display text-xl font-semibold text-ink">
              {sectorLabel(sector)} sector
            </h2>
            <div className="grid gap-3">
              {[...picks].sort((a, b) => b.fit_score - a.fit_score).map((p) => (
                <PickCard key={p.ticker} pick={p} />
              ))}
            </div>
          </div>
        ))
      ) : (
        <div className="grid gap-3">
          {data.picks.slice(0, 20).map((p) => (
            <PickCard key={p.ticker} pick={p} />
          ))}
        </div>
      )}

      {data.avoid.length > 0 && (
        <>
          <h2 className="mb-4 mt-12 font-display text-xl font-semibold text-ink">Excluded for your profile</h2>
          <div className="grid gap-2">
            {data.avoid.slice(0, 10).map((a) => (
              <div key={a.ticker} className="rounded-xl bg-white/80 px-4 py-3 text-sm ring-1 ring-slate-200/60">
                <span className="font-semibold">{formatTicker(a.ticker)}</span>
                <span className="text-slate-500"> — {a.reasons[0] || "Excluded"}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function PickCard({ pick: p }: { pick: import("../api/client").Fit }) {
  const action = p.action_label || p.recommendation;
  return (
    <Link
      to={`/stock/${encodeURIComponent(p.ticker)}`}
      className="block rounded-2xl bg-white/95 p-5 shadow-sm ring-1 ring-slate-200/60 transition hover:-translate-y-0.5 hover:shadow-md hover:ring-accent/30"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-display text-xl font-semibold text-ink">{formatTicker(p.ticker)}</h3>
            <RecommendationBadge value={action} />
          </div>
          <p className="mt-1.5 text-sm text-slate-600">{p.headline}</p>
          <div className="mt-3">
            <AxisBadge label="Score" value={`${p.composite_score.toFixed(0)}/100`} tone="neutral" />
          </div>
        </div>
        <div className="w-36 shrink-0">
          <FitScoreBar score={p.fit_score} label="Profile fit" />
        </div>
      </div>
      {p.reasons.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-1.5 border-t border-slate-100 pt-3">
          {p.reasons.slice(0, 4).map((r) => (
            <li key={r} className="rounded-md bg-slate-50 px-2 py-1 text-xs text-slate-600 ring-1 ring-slate-100">
              {r}
            </li>
          ))}
        </ul>
      )}
    </Link>
  );
}
