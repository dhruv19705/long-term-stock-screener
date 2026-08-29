"""External alignment audit vs documented street consensus."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from screener.config_loader import load_benchmark_suite  # noqa: E402
from screener.pipeline import run_evaluation, STATE  # noqa: E402

BEARISH = {"SELL", "AVOID"}
BULLISH = {"BUY", "STRONG BUY"}
NEUTRAL = {"HOLD"}


def _direction(label: str) -> str:
    u = label.upper()
    if u in BULLISH:
        return "bullish"
    if u in BEARISH:
        return "bearish"
    return "neutral"


def run_external_audit(suite: str = "all", use_cache: bool = True, refresh: bool = False) -> dict:
    run_evaluation(sector_filter="all", use_cache=use_cache, refresh=refresh)
    benchmark = load_benchmark_suite(suite)

    direction_ok = 0
    matched = 0
    false_sell = 0
    ours_dist: Counter = Counter()
    street_dist: Counter = Counter()
    sector_stats: dict = defaultdict(lambda: {"matched": 0, "direction_ok": 0})
    source_stats: dict = defaultdict(lambda: {"matched": 0, "direction_ok": 0})
    mismatches = []

    for ticker, spec in benchmark.items():
        if ticker not in STATE.scores:
            continue
        matched += 1
        s = STATE.scores[ticker]
        street = str(spec.get("street", "HOLD")).upper()
        ours = s.recommendation
        sector = spec.get("sector", "unknown")
        source = spec.get("source", "unknown")

        ours_dist[_direction(ours)] += 1
        street_dist[_direction(street)] += 1
        sector_stats[sector]["matched"] += 1
        source_stats[source]["matched"] += 1

        if _direction(ours) == _direction(street):
            direction_ok += 1
            sector_stats[sector]["direction_ok"] += 1
            source_stats[source]["direction_ok"] += 1
        else:
            mismatches.append(
                {
                    "ticker": ticker,
                    "ours": ours,
                    "street": street,
                    "source": source,
                    "sector": sector,
                }
            )
        if street in BULLISH and ours in BEARISH:
            false_sell += 1

    total = matched or 1
    sector_heatmap = {
        sec: round(100 * v["direction_ok"] / v["matched"], 1) if v["matched"] else 0
        for sec, v in sector_stats.items()
    }
    return {
        "suite": suite,
        "matched": matched,
        "direction_pct": round(100 * direction_ok / total, 1),
        "false_sell_on_buy": false_sell,
        "ours_distribution": dict(ours_dist),
        "street_distribution": dict(street_dist),
        "sector_heatmap": sector_heatmap,
        "by_source": {
            src: round(100 * v["direction_ok"] / v["matched"], 1) if v["matched"] else 0
            for src, v in source_stats.items()
        },
        "mismatches": mismatches[:30],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="all", choices=["nifty50", "nifty_next50", "golden", "all"])
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--compare-sources", action="store_true")
    args = parser.parse_args()

    report = run_external_audit(suite=args.suite, use_cache=not args.refresh, refresh=args.refresh)
    print("EXTERNAL ALIGNMENT AUDIT")
    print(f"Suite: {report['suite']}")
    print(f"Matched: {report['matched']}")
    print(f"Direction match: {report['direction_pct']}%")
    print(f"False SELL on street-Buy: {report['false_sell_on_buy']}")
    print(f"\nScreener distribution: {report['ours_distribution']}")
    print(f"Street distribution:     {report['street_distribution']}")
    print(f"\nSector heatmap (% direction match):")
    for sec, pct in sorted(report["sector_heatmap"].items(), key=lambda x: x[1]):
        print(f"  {sec:16} {pct}%")
    if args.compare_sources:
        print(f"\nBy source:")
        for src, pct in sorted(report["by_source"].items(), key=lambda x: -x[1]):
            print(f"  {src:24} {pct}%")

    out = ROOT / "reports" / "external_alignment.json"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
