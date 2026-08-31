import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchInterpret, fetchQuote, mergeQuotes } from "../api/client";
import { AnalystQuestionCard } from "../components/AnalystQuestionCard";
import { RecommendationBadge } from "../components/RecommendationBadge";
import { StockQuoteCard } from "../components/StockQuoteCard";
import { ValuationBadge } from "../components/ValuationBadge";
import { formatTicker, sectorLabel } from "../types/screen";
import { loadProfile } from "./Questionnaire";

export default function StockDetail() {
  const { ticker = "" } = useParams();
  const profile = loadProfile();
  const { data, isLoading, error } = useQuery({
    queryKey: ["interpret", ticker],
    queryFn: () => fetchInterpret(ticker),
    enabled: !!ticker,
  });
  const quoteQuery = useQuery({
    queryKey: ["quote", ticker],
    queryFn: () => fetchQuote(ticker),
    enabled: !!ticker,
  });

  if (isLoading) {
    return (
      <div className="rounded-2xl bg-white/95 p-10 text-center shadow-sm ring-1 ring-slate-200/60">
        <p className="text-slate-600">Loading analysis…</p>
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="rounded-2xl bg-white/95 p-8 shadow-sm ring-1 ring-slate-200/60">
        <p className="text-danger">Could not load {ticker}.</p>
        <Link to="/universe" className="mt-3 inline-block text-sm text-accent hover:underline">
          ← Back to rankings
        </Link>
      </div>
    );
  }

  return (
    <section>
      <Link to="/universe" className="text-sm text-accent hover:underline">
        ← Rankings
      </Link>

      {profile && (
        <p className="mt-3 rounded-lg bg-accent/5 px-3 py-2 text-sm text-slate-700 ring-1 ring-accent/20">
          Viewing as <strong>{profile.label}</strong> investor
        </p>
      )}

      <div className="mt-4 grid gap-6 lg:grid-cols-[1fr_320px]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-accent">
            {sectorLabel(data.sector_focus)}
          </p>
          <h1 className="mt-1 font-display text-4xl font-bold tracking-tight text-ink">{formatTicker(data.ticker)}</h1>
          <p className="mt-3 max-w-2xl text-lg text-slate-600">{data.headline}</p>
        </div>

        <div className="rounded-2xl bg-white/95 p-6 shadow-sm ring-1 ring-slate-200/60">
          <RecommendationBadge value={data.recommendation} size="md" />
          {data.calibration_applied && data.raw_recommendation && data.raw_recommendation !== data.recommendation && (
            <p className="mt-2 text-xs text-slate-500">
              Calibrated from {data.raw_recommendation} (Nifty/street alignment)
            </p>
          )}
          <div className="mt-5 grid grid-cols-2 gap-4 border-t border-slate-100 pt-5">
            <Metric label="Composite" value={data.composite_score.toFixed(1)} />
            <Metric label="Risk" value={data.stock_risk_score.toFixed(0)} />
            <Metric label="Valuation" value={<ValuationBadge value={data.valuation_label} />} />
            <Metric label="Confidence" value={`${(data.confidence * 100).toFixed(0)}%`} />
          </div>
        </div>
      </div>

      <StockQuoteCard
        quote={mergeQuotes(quoteQuery.data, data.quote)}
        loading={quoteQuery.isLoading && !data.quote?.current_price}
      />

      <div className="mt-8 grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl bg-emerald-50/60 p-5 ring-1 ring-emerald-200/50">
          <h2 className="font-display text-lg font-semibold text-emerald-900">Bull case</h2>
          <ul className="mt-3 space-y-2 text-sm text-slate-700">
            {data.bull_case.length ? data.bull_case.map((b) => <li key={b}>• {b}</li>) : <li className="text-slate-500">None flagged</li>}
          </ul>
        </div>
        <div className="rounded-2xl bg-rose-50/60 p-5 ring-1 ring-rose-200/50">
          <h2 className="font-display text-lg font-semibold text-rose-900">Bear case</h2>
          <ul className="mt-3 space-y-2 text-sm text-slate-700">
            {data.bear_case.length ? data.bear_case.map((b) => <li key={b}>• {b}</li>) : <li className="text-slate-500">None flagged</li>}
          </ul>
        </div>
      </div>

      <div className="mt-8 rounded-2xl bg-white/95 p-5 shadow-sm ring-1 ring-slate-200/60">
        <p className="text-sm text-slate-600">
          <strong className="text-ink">Key risk:</strong> {data.key_risk}
        </p>
        <p className="mt-2 text-sm text-slate-700">{data.verdict}</p>
      </div>

      <h2 className="mb-4 mt-10 font-display text-2xl font-semibold text-ink">Risk checklist</h2>
      <div className="grid gap-3">
        {data.questions.map((q) => (
          <AnalystQuestionCard key={q.id} q={q} />
        ))}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500">{label}</p>
      <div className="mt-0.5 text-lg font-semibold text-ink">{value}</div>
    </div>
  );
}
