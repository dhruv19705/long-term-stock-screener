"""Compare screener outputs vs market-standard expectations for large caps."""
from __future__ import annotations

from collections import Counter

from screener.pipeline import run_evaluation, STATE

# Market-standard directional view (2025-26 consensus themes, not live broker PDFs)
# Format: ticker -> (expected_range, note)
MARKET_BENCHMARK = {
    "HDFCBANK.NS": ({"BUY", "STRONG BUY", "HOLD"}, "Quality private bank; beaten down 1y"),
    "ICICIBANK.NS": ({"BUY", "STRONG BUY", "HOLD"}, "Leading private bank"),
    "SBIN.NS": ({"HOLD", "BUY"}, "PSU turnaround; cheap P/B"),
    "KOTAKBANK.NS": ({"HOLD", "BUY"}, "Premium franchise, rich valuation"),
    "AXISBANK.NS": ({"BUY", "HOLD"}, "Recovery play"),
    "TCS.NS": ({"HOLD", "BUY"}, "Quality IT; sector headwinds"),
    "INFY.NS": ({"HOLD", "BUY"}, "Large-cap IT staple"),
    "WIPRO.NS": ({"HOLD", "AVOID"}, "Weaker vs IT peers"),
    "HCLTECH.NS": ({"HOLD", "BUY"}, "Diversified IT"),
    "RELIANCE.NS": ({"BUY", "HOLD"}, "Conglomerate anchor"),
    "ITC.NS": ({"HOLD", "BUY"}, "Defensive; SELL too harsh"),
    "HINDUNILVR.NS": ({"HOLD", "BUY"}, "Defensive staple"),
    "NESTLEIND.NS": ({"HOLD", "BUY"}, "Premium FMCG"),
    "SUNPHARMA.NS": ({"BUY", "HOLD"}, "Pharma leader"),
    "MARUTI.NS": ({"HOLD", "BUY"}, "Auto leader, expensive"),
    "BAJAJ-AUTO.NS": ({"HOLD", "BUY"}, "Strong franchise"),
    "LT.NS": ({"HOLD", "BUY"}, "Infra/industrial bellwether"),
    "TATASTEEL.NS": ({"HOLD", "AVOID"}, "Cyclical metals"),
    "JSWSTEEL.NS": ({"HOLD", "BUY"}, "Efficient steel"),
}


def main() -> None:
    import sys

    if "--strict" in sys.argv:
        from scripts.golden_set_audit import run_audit

        report = run_audit(use_cache=True, large_cap_only=True)
        print("STRICT GOLDEN SET AUDIT")
        print(f"Direction match: {report['direction_pct']}%")
        print(f"False SELL on street-Buy: {report['false_sell_on_buy_large']}")
        return

    run_evaluation(sector_filter="all", use_cache=True)
    recs = Counter(s.recommendation for s in STATE.scores.values())

    print("=" * 60)
    print("MARKET ALIGNMENT AUDIT")
    print("=" * 60)
    print(f"\nUniverse: {len(STATE.scores)} scored")
    print(f"Distribution: {dict(recs)}")
    bearish = recs.get("AVOID", 0) + recs.get("SELL", 0)
    total = sum(recs.values())
    print(f"Bearish (AVOID+SELL): {bearish}/{total} = {100*bearish/total:.0f}%")
    print("Typical broker universe: ~15-25% Sell/Underweight, ~25-35% Buy/Overweight\n")

    aligned, misaligned = 0, []
    print(f"{'Ticker':16} {'Ours':11} {'Market OK?':10} Note")
    print("-" * 70)
    for t, (ok_set, note) in MARKET_BENCHMARK.items():
        if t not in STATE.scores:
            print(f"{t:16} {'N/A':11} {'—':10} not in universe")
            continue
        s = STATE.scores[t]
        ok = s.recommendation in ok_set
        if ok:
            aligned += 1
            flag = "YES"
        else:
            misaligned.append((t, s.recommendation, ok_set, note))
            flag = "NO"
        print(f"{t:16} {s.recommendation:11} {flag:10} Q={s.quality_grade} peer={s.peer_band} val={s.valuation_label}")

    print(f"\nAligned: {aligned}/{len(MARKET_BENCHMARK)} ({100*aligned/len(MARKET_BENCHMARK):.0f}%)")
    if misaligned:
        print("\nMisalignments:")
        for t, rec, ok_set, note in misaligned:
            print(f"  {t}: got {rec}, expected one of {ok_set} — {note}")

    # Coherence checks
    print("\n--- COHERENCE CHECKS ---")
    sb_over = [t for t, s in STATE.scores.items() if s.recommendation == "STRONG BUY" and s.valuation_label == "Over"]
    print(f"STRONG BUY + Over valuation: {len(sb_over)} ({sb_over[:5]})")
    f_buy = [t for t, s in STATE.scores.items() if s.quality_grade == "F" and s.recommendation in ("BUY", "STRONG BUY")]
    print(f"Grade F but BUY/STRONG BUY: {len(f_buy)} ({f_buy[:5]})")
    a_sell = [t for t, s in STATE.scores.items() if s.quality_grade in ("A", "B") and s.recommendation == "SELL"]
    print(f"Grade A/B but SELL: {len(a_sell)} ({a_sell[:5]})")

    # ZYDUS anomaly from user screenshot
    if "ZYDUSLIFE.NS" in STATE.scores:
        s = STATE.scores["ZYDUSLIFE.NS"]
        print(f"\nZYDUSLIFE: rec={s.recommendation} comp={s.composite_score:.1f} val={s.valuation_label} peer={s.peer_band} pct={s.composite_percentile}")


if __name__ == "__main__":
    main()
