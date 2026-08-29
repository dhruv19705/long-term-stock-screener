import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Quote, QuoteSnapshot } from "../api/client";

type Props = {
  quote?: QuoteSnapshot | Quote | null;
  loading?: boolean;
};

function isFiniteNumber(n: unknown): n is number {
  return typeof n === "number" && Number.isFinite(n);
}

export function formatInr(n: number | null | undefined, digits = 2): string {
  if (!isFiniteNumber(n)) return "—";
  return `₹${n.toLocaleString("en-IN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  })}`;
}

export function formatCompactInr(n: number | null | undefined): string {
  if (!isFiniteNumber(n)) return "—";
  const abs = Math.abs(n);
  if (abs >= 1e12) return `₹${(n / 1e12).toFixed(1)}T`;
  if (abs >= 1e9) return `₹${(n / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `₹${(n / 1e6).toFixed(1)}M`;
  return formatInr(n, 0);
}

export function formatVolume(n: number | null | undefined): string {
  if (!isFiniteNumber(n)) return "—";
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return n.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

export function formatPct(n: number | null | undefined, digits = 1): string {
  if (!isFiniteNumber(n)) return "—";
  return `${n.toFixed(digits)}%`;
}

export function formatRatio(n: number | null | undefined): string {
  if (!isFiniteNumber(n)) return "—";
  return n.toFixed(1);
}

function historyOf(quote?: QuoteSnapshot | Quote | null) {
  if (quote && "history" in quote && Array.isArray(quote.history)) {
    return quote.history;
  }
  return [];
}

export function StockQuoteCard({ quote, loading }: Props) {
  const history = historyOf(quote);
  const change = quote?.change;
  const up = isFiniteNumber(change) && change > 0;
  const down = isFiniteNumber(change) && change < 0;
  const changeClass = up ? "text-good" : down ? "text-danger" : "text-slate-600";
  const lastDate = history.length ? history[history.length - 1].date : null;

  return (
    <div className="mt-6 rounded-2xl bg-white/95 p-5 shadow-sm ring-1 ring-slate-200/60">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          {quote?.company_name && (
            <p className="text-sm font-medium text-slate-600">{quote.company_name}</p>
          )}
          <div className="mt-1 flex flex-wrap items-baseline gap-3">
            <p className="font-display text-3xl font-bold tabular-nums text-ink">
              {formatInr(quote?.current_price)}
            </p>
            <p className={`text-sm font-semibold tabular-nums ${changeClass}`}>
              {isFiniteNumber(change) ? `${change > 0 ? "+" : ""}${change.toFixed(2)}` : "—"}
              {isFiniteNumber(quote?.change_pct)
                ? ` (${quote.change_pct > 0 ? "+" : ""}${quote.change_pct.toFixed(2)}%)`
                : ""}
            </p>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {lastDate ? `As of ${lastDate}` : loading ? "Fetching latest quote…" : "Latest available quote"}
          </p>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <Stat label="Day high" value={formatInr(quote?.day_high)} />
        <Stat label="Day low" value={formatInr(quote?.day_low)} />
        <Stat label="52w high" value={formatInr(quote?.week_52_high)} />
        <Stat label="52w low" value={formatInr(quote?.week_52_low)} />
        <Stat label="Volume" value={formatVolume(quote?.volume)} />
        <Stat label="Avg volume" value={formatVolume(quote?.avg_volume)} />
      </div>

      {history.length > 1 && (
        <div className="mt-6">
          <p className="mb-2 text-[10px] font-medium uppercase tracking-wider text-slate-500">
            6-month price
          </p>
          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={history} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11, fill: "#64748b" }}
                  tickFormatter={(d: string) => d.slice(5)}
                  minTickGap={28}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  domain={["auto", "auto"]}
                  tick={{ fontSize: 11, fill: "#64748b" }}
                  tickFormatter={(v: number) => `₹${Number(v).toFixed(0)}`}
                  width={56}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  formatter={(value: number) => [formatInr(value), "Close"]}
                  labelFormatter={(label) => `Date: ${label}`}
                />
                <Line type="monotone" dataKey="close" stroke="#0d6e6e" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="mt-5 grid grid-cols-2 gap-3 border-t border-slate-100 pt-5 sm:grid-cols-3 lg:grid-cols-6">
        <Stat label="Market cap" value={formatCompactInr(quote?.market_cap)} />
        <Stat label="P/E" value={formatRatio(quote?.pe)} />
        <Stat label="P/B" value={formatRatio(quote?.pb)} />
        <Stat label="Div yield" value={formatPct(quote?.dividend_yield_pct)} />
        <Stat label="ROE" value={formatPct(quote?.roe_pct)} />
        <Stat label="1Y return" value={formatPct(quote?.return_1y_pct)} />
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] font-medium uppercase tracking-wider text-slate-500">{label}</p>
      <p className="mt-0.5 text-sm font-semibold tabular-nums text-ink">{value}</p>
    </div>
  );
}
