from collections import Counter, defaultdict

from screener.config_loader import load_nifty50_benchmark
from screener.pipeline import run_evaluation, STATE
from scripts.benchmark_gap_report import _direction

run_evaluation(use_cache=True)
n50 = load_nifty50_benchmark()["tickers"]

by_grade = defaultdict(lambda: {"n": 0, "ok": 0})
for t, spec in n50.items():
    if t not in STATE.scores:
        continue
    s = STATE.scores[t]
    g = s.quality_grade
    by_grade[g]["n"] += 1
    if _direction(s.recommendation) == _direction(spec["street"].upper()):
        by_grade[g]["ok"] += 1

print("Nifty50 direction match BY GRADE:")
for g in sorted(by_grade):
    d = by_grade[g]
    print(f"  Grade {g}: {100 * d['ok'] / d['n']:.0f}% ({d['ok']}/{d['n']})")

ab = [t for t in n50 if t in STATE.scores and STATE.scores[t].quality_grade in ("A", "B")]
ab_ok = [
    t
    for t in ab
    if _direction(STATE.scores[t].recommendation) == _direction(n50[t]["street"].upper())
]
print(f"Grade A/B only: {100 * len(ab_ok) / len(ab):.1f}% ({len(ab_ok)}/{len(ab)})")

src_ok = Counter()
src_n = Counter()
for t, spec in n50.items():
    if t not in STATE.scores:
        continue
    src = spec.get("source", "?")
    src_n[src] += 1
    if _direction(STATE.scores[t].recommendation) == _direction(spec["street"].upper()):
        src_ok[src] += 1
print("Match by street SOURCE (Nifty50):")
for src in sorted(src_n, key=lambda x: -src_n[x]):
    print(f"  {src}: {100 * src_ok[src] / src_n[src]:.0f}% ({src_ok[src]}/{src_n[src]})")

false_bear = sum(
    1
    for t, sp in n50.items()
    if t in STATE.scores
    and _direction(sp["street"].upper()) == "bullish"
    and _direction(STATE.scores[t].recommendation) == "bearish"
)
street_bull = sum(1 for sp in n50.values() if _direction(sp["street"].upper()) == "bullish")
print(f"False bearish on street-Buy: {false_bear}")
print(f"Soft safety (non-bearish vs street bullish): {100 * (street_bull - false_bear) / street_bull:.0f}%")
