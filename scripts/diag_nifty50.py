from screener.config_loader import load_nifty50_benchmark
from screener.pipeline import run_evaluation, STATE
from scripts.benchmark_gap_report import _direction

run_evaluation(sector_filter="all", use_cache=True)
bench = load_nifty50_benchmark()["tickers"]
for t, spec in sorted(bench.items()):
    if t not in STATE.scores:
        continue
    s = STATE.scores[t]
    street = spec["street"].upper()
    if _direction(s.recommendation) != _direction(street):
        print(
            f"{t:16} ours={s.recommendation:11} street={street:11} "
            f"Q={s.quality_grade} peer={s.peer_band:10} val={s.valuation_label} "
            f"comp={s.composite_score:.0f} pct={s.composite_percentile}"
        )
