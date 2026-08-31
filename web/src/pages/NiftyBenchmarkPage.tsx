import { useQuery } from "@tanstack/react-query";
import { fetchBenchmarkSummary } from "../api/client";
import { MethodCard } from "../components/MethodCard";
import { RecommendationBadge } from "../components/RecommendationBadge";

const REC_ORDER = ["STRONG BUY", "BUY", "HOLD", "AVOID", "SELL"] as const;
const MAX_MISMATCHES = 3;

const CAUSE_LABELS: Record<string, string> = {
  peer_rank_low: "Composite score below peer median in its cohort",
  valuation_over_cap: "Flagged expensive on our absolute valuation bands",
  data_missing_roe: "Missing ROE — completeness penalty lowered the score",
  hard_gate_artifact: "Hard gate or data-quality flag triggered",
  over_promoted: "Model more bullish than fundamentals support",
  other: "Quality and valuation mix differs from street view",
};

function mismatchReason(causes?: string[], error?: string): string {
  if (error) return error;
  if (!causes?.length) return "—";
  return causes.map((c) => CAUSE_LABELS[c] ?? c).join(" · ");
}

function KpiCard({ label, value, sub, ok }: { label: string; value: string; sub?: string; ok?: boolean }) {
  return (
    <div className="rounded-2xl bg-white/90 p-5 ring-1 ring-slate-200/80">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <p className={`mt-2 font-display text-3xl font-bold tabular-nums ${ok === false ? "text-warn" : "text-ink"}`}>
        {value}
      </p>
      {sub && <p className="mt-1 text-sm text-slate-500">{sub}</p>}
    </div>
  );
}

export default function NiftyBenchmarkPage() {
  const benchmark = useQuery({
    queryKey: ["benchmark"],
    queryFn: () => fetchBenchmarkSummary(),
    staleTime: 120_000,
    retry: 1,
  });

  const data = benchmark.data;
  const nifty = data?.nifty50;
  const dist = data?.distribution;
  const hasLiveData = nifty != null && nifty.matched != null && nifty.matched > 0;

  return (
    <section className="space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Methodology</p>
        <h1 className="mt-1 font-display text-4xl font-bold tracking-tight text-ink">Nifty 50 Benchmark</h1>
        <p className="mt-3 max-w-3xl text-slate-600">
          Nifty 50 plays two roles in PRISM: index-relative risk metrics for every stock, and a street-consensus
          alignment audit for all 50 index constituents.
        </p>
      </div>

      <MethodCard title="Index-relative risk" eyebrow="Role A · ^NSEI">
        <p>Every stock in the universe is compared against the Nifty 50 index (^NSEI) for risk metrics:</p>
        <ul className="mt-3 list-disc space-y-2 pl-5">
          <li>
            <strong className="text-ink">Beta</strong> — Cov(r_stock, r_nifty) / Var(r_nifty) on aligned daily returns
            (≥ 60 aligned days, 5Y history). Clamped to [−1, 4].
          </li>
          <li>
            <strong className="text-ink">RS vs Nifty</strong> — 6-month stock return minus 6-month Nifty return.
          </li>
        </ul>
        <p className="mt-3">These feed composite momentum, the action matrix (Over + weak RS → SELL), and the risk questionnaire.</p>
      </MethodCard>

      <MethodCard title="Street-consensus alignment" eyebrow="Role B · 50 constituents">
        <p>
          All 50 Nifty constituents are compared against documented analyst consensus labels (street BUY / HOLD / SELL)
          from <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">nifty50_benchmark.yaml</code>.
        </p>
        <ul className="mt-3 list-disc space-y-2 pl-5">
          <li>
            <strong className="text-ink">Direction match</strong> — bullish / neutral / bearish bucket alignment (target ≥
            80%). Primary KPI.
          </li>
          <li>
            <strong className="text-ink">Severity match</strong> — within ±1 step on the action ladder: SELL → AVOID →
            HOLD → BUY → STRONG BUY (target ≥ 92%).
          </li>
          <li>
            <strong className="text-ink">False SELL on street-Buy</strong> — street is bullish but our model says SELL or
            AVOID. Critical error metric.
          </li>
        </ul>
      </MethodCard>

      <MethodCard title="Calibration overlays">
        <p>When enabled, two post-processing steps tune Nifty 50 names toward street expectations:</p>
        <ul className="mt-3 list-disc space-y-2 pl-5">
          <li>
            <strong className="text-ink">Index anchor</strong> — lifts under-rated Nifty 50 mega/large caps from HOLD when
            quality is Grade A/B and valuation is Fair or Under.
          </li>
          <li>
            <strong className="text-ink">Street overlay</strong> — nudges well-covered names (analyst count ≥ 20) toward
            street consensus. Never auto-upgrades to STRONG BUY.
          </li>
        </ul>
      </MethodCard>

      <div className="rounded-2xl bg-white/90 p-5 ring-1 ring-slate-200/80">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Audit flow</p>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-slate-600">
          <span className="rounded-lg bg-slate-100 px-3 py-1.5">nifty50_benchmark.yaml</span>
          <span className="text-slate-400">→</span>
          <span className="rounded-lg bg-slate-100 px-3 py-1.5">Screen run</span>
          <span className="text-slate-400">→</span>
          <span className="rounded-lg bg-slate-100 px-3 py-1.5">Compare ours vs street</span>
          <span className="text-slate-400">→</span>
          <span className="rounded-lg bg-accent/10 px-3 py-1.5 text-accent">Direction / severity KPIs</span>
        </div>
      </div>

      <div>
        <h2 className="font-display text-2xl font-semibold text-ink">Live alignment stats</h2>
        <p className="mt-1 text-sm text-slate-500">
          {data?.generated_at
            ? `Last updated ${new Date(data.generated_at * 1000).toLocaleString()}`
            : "Populated after the screener runs"}
        </p>

        {benchmark.isLoading && (
          <p className="mt-6 text-slate-500">Loading benchmark summary…</p>
        )}

        {benchmark.isError && (
          <div className="mt-6 rounded-2xl bg-amber-50 p-5 ring-1 ring-amber-200/70">
            <p className="font-medium text-amber-900">Could not load benchmark data</p>
            <p className="mt-1 text-sm text-amber-800">
              Make sure the API server is running and the screener has completed at least one screen run.
            </p>
          </div>
        )}

        {!benchmark.isLoading && !benchmark.isError && !hasLiveData && (
          <div className="mt-6 rounded-2xl bg-slate-50 p-5 ring-1 ring-slate-200/80">
            <p className="font-medium text-ink">Run the screener first</p>
            <p className="mt-1 text-sm text-slate-600">
              Alignment stats populate after the backend completes a full screen. Start the API and trigger a screen run,
              then refresh this page.
            </p>
          </div>
        )}

        {hasLiveData && nifty && (
          <>
            <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <KpiCard
                label="Direction match"
                value={`${nifty.direction_pct?.toFixed(1) ?? "—"}%`}
                sub="Target ≥ 80%"
                ok={(nifty.direction_pct ?? 0) >= 80}
              />
              <KpiCard
                label="Severity match"
                value={`${nifty.severity_pct?.toFixed(1) ?? "—"}%`}
                sub="Target ≥ 92%"
                ok={(nifty.severity_pct ?? 0) >= 92}
              />
              <KpiCard
                label="False SELL on Buy"
                value={String(nifty.false_sell_on_buy ?? "—")}
                sub="Lower is better"
                ok={(nifty.false_sell_on_buy ?? 0) <= 4}
              />
              <KpiCard
                label="Names matched"
                value={`${nifty.matched ?? 0} / 50`}
                sub={`${data?.calibrated_count ?? 0} calibrated`}
              />
            </div>

            {dist && (
              <div className="mt-8 rounded-2xl bg-white/90 p-6 ring-1 ring-slate-200/80">
                <h3 className="font-display text-lg font-semibold text-ink">Universe recommendation distribution</h3>
                <div className="mt-4 flex flex-wrap gap-4 text-sm">
                  <span>
                    Bullish: <strong className="text-good">{dist.bullish_pct}%</strong>{" "}
                    <span className="text-slate-500">
                      (target {dist.targets.bullish_min}–{dist.targets.bullish_max}%)
                    </span>
                  </span>
                  <span>
                    Bearish: <strong className="text-danger">{dist.bearish_pct}%</strong>{" "}
                    <span className="text-slate-500">
                      (target {dist.targets.bearish_min}–{dist.targets.bearish_max}%)
                    </span>
                  </span>
                  <span className="text-slate-500">{dist.total} names total</span>
                </div>
                <div className="mt-4 flex flex-wrap gap-3">
                  {REC_ORDER.map((rec) => {
                    const count = dist.counts[rec] ?? 0;
                    if (count === 0) return null;
                    return (
                      <div key={rec} className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2">
                        <RecommendationBadge value={rec} />
                        <span className="tabular-nums font-semibold text-ink">{count}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {nifty.top_mismatches && nifty.top_mismatches.length > 0 && (
              <div className="mt-8 overflow-x-auto rounded-2xl bg-white/90 ring-1 ring-slate-200/80">
                <div className="border-b border-slate-100 px-6 py-4">
                  <h3 className="font-display text-lg font-semibold text-ink">Top mismatches</h3>
                  <p className="text-sm text-slate-500">Our recommendation vs street consensus</p>
                </div>
                <table className="w-full min-w-[560px] text-left text-sm">
                  <thead className="bg-slate-50/80">
                    <tr>
                      <th className="px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Ticker</th>
                      <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Ours</th>
                      <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Street</th>
                      <th className="px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Why we differ</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {nifty.top_mismatches.slice(0, MAX_MISMATCHES).map((m) => (
                      <tr key={m.ticker} className="bg-white/60">
                        <td className="px-6 py-3 font-medium text-ink">{m.ticker.replace(".NS", "")}</td>
                        <td className="px-4 py-3">
                          {m.ours ? <RecommendationBadge value={m.ours} /> : "—"}
                        </td>
                        <td className="px-4 py-3">
                          {m.street ? <RecommendationBadge value={m.street} /> : "—"}
                        </td>
                        <td className="px-6 py-3 text-slate-600">
                          {mismatchReason(m.causes, m.error)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
