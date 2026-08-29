"""Quick market-standard recheck — distribution, outliers, sector mix."""
from __future__ import annotations

from collections import Counter, defaultdict

from screener.pipeline import run_evaluation, STATE

run_evaluation(sector_filter="all", use_cache=True)

scores = STATE.scores
metrics = STATE.metrics
recs = Counter(s.recommendation for s in scores.values())
total = len(scores)
buy = recs.get("BUY", 0) + recs.get("STRONG BUY", 0)
bear = recs.get("AVOID", 0) + recs.get("SELL", 0)

print("=" * 60)
print("MARKET STANDARD RECHECK")
print("=" * 60)
print(f"Universe: {total}")
print(f"Distribution: {dict(recs)}")
print(f"Buy/Overweight side: {buy}/{total} = {100 * buy / total:.0f}%  (broker norm ~25-35%)")
print(f"Bearish side:        {bear}/{total} = {100 * bear / total:.0f}%  (broker norm ~15-25%)")

sb = sorted(
    [
        (t, s.composite_score, s.quality_grade, s.peer_band, s.valuation_label)
        for t, s in scores.items()
        if s.recommendation == "STRONG BUY"
    ],
    key=lambda x: -x[1],
)
print(f"\nSTRONG BUY ({len(sb)}):")
for row in sb:
    print(f"  {row[0]:18} comp={row[1]:5.1f} Q={row[2]} peer={row[3]:10} val={row[4]}")

print("\nSELL:")
for t, s in sorted(scores.items()):
    if s.recommendation == "SELL":
        m = metrics.get(t)
        cap = f"{m.market_cap / 1e12:.2f}T" if m and m.market_cap else "?"
        print(
            f"  {t:18} Q={s.quality_grade} peer={s.peer_band:10} "
            f"val={s.valuation_label} comp={s.composite_score:.1f} cap={cap}"
        )

print("\nAVOID with quality A/B (cap floor shouldn't apply):")
cnt = 0
for t, s in sorted(scores.items(), key=lambda x: -x[1].composite_score):
    if s.recommendation == "AVOID" and s.quality_grade in ("A", "B"):
        print(f"  {t:18} Q={s.quality_grade} peer={s.peer_band} val={s.valuation_label}")
        cnt += 1
        if cnt >= 10:
            break

by_sec: dict[str, Counter] = defaultdict(Counter)
for t, s in scores.items():
    sec = (metrics[t].sector if t in metrics else None) or "unknown"
    by_sec[sec][s.recommendation] += 1

print("\nSector mix:")
for sec in sorted(by_sec):
    c = by_sec[sec]
    n = sum(c.values())
    b = c.get("BUY", 0) + c.get("STRONG BUY", 0)
    print(
        f"  {sec:20} n={n:3} buy={b:2} ({100 * b / n:.0f}%) "
        f"hold={c.get('HOLD', 0):2} avoid={c.get('AVOID', 0):2} sell={c.get('SELL', 0)}"
    )

# IT large caps detail
print("\nIT large-cap peer context:")
for t in ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS", "LTIM.NS"]:
    if t not in scores:
        continue
    s = scores[t]
    print(
        f"  {t:14} rec={s.recommendation:11} comp={s.composite_score:.1f} "
        f"pct={s.composite_percentile:.0f} Q={s.quality_grade} peer={s.peer_band} val={s.valuation_label}"
    )
