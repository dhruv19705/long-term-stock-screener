import { Link } from "react-router-dom";
import { MethodCard, WeightTable } from "../components/MethodCard";

const BANKING_WEIGHTS = [
  { pillar: "Asset quality", weight: "30%", metrics: "GNPA, NNPA, CAR, GNPA vs peers" },
  { pillar: "Franchise", weight: "25%", metrics: "NIM, ROA, ROE vs peers" },
  { pillar: "Valuation", weight: "25%", metrics: "P/B–ROE residual within cohort" },
  { pillar: "Momentum", weight: "10%", metrics: "6M return percentile / RS vs Nifty" },
  { pillar: "Risk penalty", weight: "10%", metrics: "Max drawdown (lower is better)" },
];

const IT_WEIGHTS = [
  { pillar: "Margin quality", weight: "25%", metrics: "Op margin, margin trend, ROE" },
  { pillar: "Growth", weight: "30%", metrics: "Revenue + profit CAGR" },
  { pillar: "Valuation", weight: "25%", metrics: "PEG, PE vs peers, FCF / earnings yield" },
  { pillar: "Momentum", weight: "10%", metrics: "6M return / RS vs Nifty" },
  { pillar: "Risk penalty", weight: "10%", metrics: "Drawdown percentile" },
];

export default function SectorRankingPage() {
  return (
    <section className="space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Methodology</p>
        <h1 className="mt-1 font-display text-4xl font-bold tracking-tight text-ink">How we rank Banking &amp; IT</h1>
        <p className="mt-3 max-w-3xl text-slate-600">
          Both sectors use deep scoring engines. Each stock is ranked only within its peer cohort, graded on absolute
          quality and valuation, then labelled via a deterministic action matrix — not by raw composite score alone.
        </p>
      </div>

      <div className="rounded-2xl bg-white/90 p-5 ring-1 ring-slate-200/80">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Pipeline</p>
        <p className="mt-2 font-mono text-sm text-slate-700">
          Universe → QC → peer-relative scoring → quality grade + valuation → action matrix (BUY / HOLD / SELL)
        </p>
      </div>

      <MethodCard title="Shared concepts" eyebrow="Both sectors">
        <ul className="list-disc space-y-2 pl-5">
          <li>
            Stocks are ranked <strong className="text-ink">only within their peer cohort</strong>, not across sectors.
            Do not compare raw composite scores between Banking and IT.
          </li>
          <li>
            Three axes drive the final label:{" "}
            <strong className="text-ink">Quality grade</strong> (A–F),{" "}
            <strong className="text-ink">Peer band</strong> (Top / Upper-Mid / Lower-Mid / Bottom), and{" "}
            <strong className="text-ink">Valuation</strong> (Under / Fair / Over).
          </li>
          <li>
            Peer band thresholds: Top ≥ 70th percentile, Upper-Mid 50–70, Lower-Mid 30–50, Bottom &lt; 30 within the
            cohort.
          </li>
          <li>
            The final recommendation comes from the action matrix — a high composite alone does not produce STRONG BUY
            if valuation is Over.
          </li>
        </ul>
      </MethodCard>

      <MethodCard title="Banking" eyebrow="Deep engine">
        <p>
          Banking weights <strong className="text-ink">asset quality and franchise</strong> (55% combined) because credit
          health and NIM drive returns. Peers are split: private banks rank against private banks; PSU banks rank
          against PSU banks. HDFC Bank is ranked against other private banks, not SBI.
        </p>
        <WeightTable rows={BANKING_WEIGHTS} />
        <div className="mt-4 space-y-3">
          <div>
            <p className="font-medium text-ink">Valuation (P/B–ROE residual)</p>
            <p>
              Within the private or PSU cohort, the model regresses P/B on ROE. A negative residual means cheaper than
              the ROE the market usually pays for → leans Under. A large positive residual → expensive vs that ROE line
              → leans Over.
            </p>
          </div>
          <div>
            <p className="font-medium text-ink">Hard gates (automatic fail → Grade F)</p>
            <ul className="mt-1 list-disc pl-5">
              <li>GNPA ≥ 3.5%</li>
              <li>NNPA ≥ 1.2%</li>
              <li>CAR &lt; 12%</li>
            </ul>
          </div>
          <div>
            <p className="font-medium text-ink">Valuation bands (absolute)</p>
            <p>P/B ≤ 2.0 → Under · P/B ≤ 3.5 → Fair · above → Over</p>
          </div>
          <div>
            <p className="font-medium text-ink">Special rules</p>
            <ul className="mt-1 list-disc pl-5">
              <li>Without both GNPA and NIM, peer percentile is capped at 69 — cannot reach Top band.</li>
              <li>Incomplete bank data shrinks the composite score (floor 65% of original).</li>
              <li>Over valuation + ROE &lt; 8% or GNPA ≥ 2.8% → SELL.</li>
            </ul>
          </div>
        </div>
        <Link
          to="/sectors/banking"
          className="mt-4 inline-block text-sm font-medium text-accent hover:underline"
        >
          View Banking rankings →
        </Link>
      </MethodCard>

      <MethodCard title="IT" eyebrow="Deep engine">
        <p>
          IT weights <strong className="text-ink">growth and margins</strong> (55% combined) because revenue and margin
          expansion drive multiples. Large-cap IT (market cap ≥ ₹500B) ranks separately from mid-cap IT when at least 5
          large-cap names exist — TCS and Infosys are not ranked against high-growth mid-caps.
        </p>
        <WeightTable rows={IT_WEIGHTS} />
        <div className="mt-4 space-y-3">
          <div>
            <p className="font-medium text-ink">Valuation</p>
            <p>
              Composite valuation uses PEG, PE vs IT peers, FCF yield, and earnings yield. Absolute valuation labels use
              sector bands, not peer-relative PE alone.
            </p>
          </div>
          <div>
            <p className="font-medium text-ink">Hard gates (automatic fail → Grade F)</p>
            <ul className="mt-1 list-disc pl-5">
              <li>Operating margin &lt; 0%</li>
              <li>ROE &lt; 0%</li>
              <li>Debt / equity &gt; 2.5</li>
            </ul>
          </div>
          <div>
            <p className="font-medium text-ink">Valuation bands (absolute)</p>
            <p>PE ≤ 22 → Under · PE ≤ 32 → Fair · PEG ≤ 1.2 → Under · above thresholds → Over</p>
          </div>
          <div>
            <p className="font-medium text-ink">Special rules</p>
            <ul className="mt-1 list-disc pl-5">
              <li>Over valuation + operating margin &lt; 12% → SELL.</li>
              <li>Red flags (softer): negative ROE, negative op margin, D/E &gt; 2.0.</li>
            </ul>
          </div>
        </div>
        <Link to="/sectors/it" className="mt-4 inline-block text-sm font-medium text-accent hover:underline">
          View IT rankings →
        </Link>
      </MethodCard>

      <MethodCard title="Banking vs IT — at a glance">
        <div className="overflow-x-auto rounded-xl ring-1 ring-slate-200/80">
          <table className="w-full min-w-[520px] text-left text-sm">
            <thead className="bg-slate-50/80">
              <tr>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Dimension</th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Banking</th>
                <th className="px-4 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">IT</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {[
                ["Top pillars", "Asset quality (30%) + Franchise (25%)", "Growth (30%) + Margins (25%)"],
                ["Valuation method", "P/B–ROE residual within cohort", "PEG + PE percentile + yields"],
                ["Peer cohort", "Private vs PSU banks", "Large-cap (≥ ₹500B) vs mid-cap IT"],
                ["Primary hard gates", "GNPA, NNPA, CAR", "Op margin, ROE, D/E"],
              ].map(([dim, bank, it]) => (
                <tr key={dim} className="bg-white/60">
                  <td className="px-4 py-3 font-medium text-ink">{dim}</td>
                  <td className="px-4 py-3 text-slate-600">{bank}</td>
                  <td className="px-4 py-3 text-slate-600">{it}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </MethodCard>

      <MethodCard title="Action matrix" eyebrow="Final label">
        <p>
          STRONG BUY requires <strong className="text-ink">Grade A</strong> and{" "}
          <strong className="text-ink">non-Over valuation</strong>. If valuation is Fair, the stock must not be losing
          to Nifty (RS vs Nifty ≥ 0).
        </p>
        <ul className="mt-3 list-disc space-y-2 pl-5">
          <li>Grade F or hard gate fail → SELL (if Over) or AVOID.</li>
          <li>Over + weak quality or RS vs Nifty ≤ −10% → SELL.</li>
          <li>Grade C/D/F and RS vs Nifty ≤ −15% → AVOID.</li>
          <li>Grade A + Under valuation → STRONG BUY; Grade A + Fair + positive RS → STRONG BUY.</li>
        </ul>
      </MethodCard>
    </section>
  );
}
