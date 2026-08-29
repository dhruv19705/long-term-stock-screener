"""Audit recommendation quality vs current cached data."""
from __future__ import annotations

import statistics
from collections import Counter

from screener.interpret.questionnaire import profile_from_answers
from screener.interpret.risk_matcher import rank_for_profile
from screener.models import RiskProfile
from screener.pipeline import run_evaluation, STATE

WATCH = [
    "HDFCBANK.NS", "ICICIBANK.NS", "TCS.NS", "INFY.NS", "RELIANCE.NS",
    "ITC.NS", "HINDUNILVR.NS", "SBIN.NS", "KOTAKBANK.NS", "WIPRO.NS",
    "MARUTI.NS", "SUNPHARMA.NS", "NESTLEIND.NS", "AXISBANK.NS",
    "BAJAJ-AUTO.NS", "LT.NS", "ZYDUSLIFE.NS", "DIVISLAB.NS", "ALKEM.NS",
]


def main() -> None:
    run_evaluation(sector_filter="all", use_cache=True)
    rows = []
    for t, s in STATE.scores.items():
        m = STATE.metrics[t]
        rows.append({
            "ticker": t,
            "sector": m.sector_focus,
            "composite": s.composite_score,
            "pctile": s.composite_percentile,
            "rec": s.recommendation,
            "grade": s.quality_grade,
            "band": s.peer_band,
            "val": s.valuation_label,
        })

    print("=== DISTRIBUTION ===")
    print(dict(Counter(r["rec"] for r in rows)))
    print()
    print("=== QUALITY GRADES ===")
    print(dict(Counter(r["grade"] for r in rows)))
    print()
    print("=== BLUE CHIPS ===")
    for t in WATCH:
        if t not in STATE.scores:
            print(f"  {t}: not in universe")
            continue
        s = STATE.scores[t]
        print(
            f"  {t:16} {s.recommendation:11} Q={s.quality_grade} "
            f"peer={s.peer_band:10} pct={s.composite_percentile or 0:5.1f} "
            f"comp={s.composite_score:5.1f} val={s.valuation_label}"
        )

    profile = RiskProfile(
        id="conservative",
        label="Capital Preservation",
        sector_filter="all",
        cyclical_ok=False,
        max_stock_risk=40,
        max_beta=1.15,
        diversify_sectors=True,
    )
    picks, _ = rank_for_profile(profile, STATE.interps, STATE.metrics, scores=STATE.scores)
    if len(picks) >= 2:
        fit_scores = [p.fit_score for p in picks]
        spread = statistics.pstdev(fit_scores)
        print()
        print(f"=== CONSERVATIVE FIT SPREAD (n={len(picks)}, std={spread:.1f}) ===")
        for p in picks[:8]:
            print(
                f"  {p.ticker:16} fit={p.fit_score:5.1f} Q={p.quality_grade} "
                f"peer={p.peer_band:10} action={p.action_label}"
            )
        if spread <= 3.5:
            print("  WARNING: fit scores still clustered")


if __name__ == "__main__":
    main()
