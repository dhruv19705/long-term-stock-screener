"""Walk-forward style check: BUY picks vs HOLD/SELL average 6m return (cached data)."""
from __future__ import annotations

from screener.config_loader import load_golden_set
from screener.pipeline import run_evaluation, STATE

BULLISH_SET = {"BUY", "STRONG BUY"}
BEARISH_SET = {"SELL", "AVOID"}


def main() -> None:
    run_evaluation(sector_filter="all", use_cache=True)
    golden = set((load_golden_set().get("tickers") or {}).keys())

    buckets = {"bullish": [], "neutral": [], "bearish": []}
    for t in golden:
        if t not in STATE.scores or t not in STATE.metrics:
            continue
        rec = STATE.scores[t].recommendation
        ret = STATE.metrics[t].return_6m_pct
        if ret is None:
            continue
        if rec in BULLISH_SET:
            buckets["bullish"].append(ret)
        elif rec in BEARISH_SET:
            buckets["bearish"].append(ret)
        else:
            buckets["neutral"].append(ret)

    def avg(xs):
        return round(sum(xs) / len(xs), 2) if xs else None

    print("Golden set 6m return by screener bucket:")
    for k, xs in buckets.items():
        print(f"  {k}: n={len(xs)} avg_6m={avg(xs)}%")


if __name__ == "__main__":
    main()
