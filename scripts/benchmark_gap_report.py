"""Benchmark gap report with root-cause classification."""
from __future__ import annotations

import os

os.environ.setdefault("SCREENER_BENCHMARK_CALIBRATION", "1")

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from screener.config_loader import all_tickers, load_benchmark_suite  # noqa: E402
from screener.pipeline import run_evaluation, STATE  # noqa: E402
from screener.scoring.action_matrix import ACTION_LADDER  # noqa: E402

BEARISH = {"SELL", "AVOID"}
BULLISH = {"BUY", "STRONG BUY"}


def _direction(label: str) -> str:
    u = label.upper()
    if u in BULLISH:
        return "bullish"
    if u in BEARISH:
        return "bearish"
    return "neutral"


def _severity_distance(a: str, b: str) -> int:
    if a not in ACTION_LADDER or b not in ACTION_LADDER:
        return 99
    return abs(ACTION_LADDER.index(a) - ACTION_LADDER.index(b))


def _root_cause(ticker: str, s, street: str, metrics=None) -> list[str]:
    causes: list[str] = []
    if ticker not in all_tickers():
        return ["not_in_universe"]
    roe = getattr(metrics, "roe_pct", None) if metrics else None
    if roe is None and (s.confidence or 0) < 0.5:
        causes.append("data_missing_roe")
    if s.hard_gate_fail and s.composite_score > 70:
        causes.append("hard_gate_artifact")
    street_dir = _direction(street)
    ours_dir = _direction(s.recommendation)
    if street_dir == "bullish" and ours_dir == "neutral" and s.valuation_label == "Over":
        causes.append("valuation_over_cap")
    if street_dir == "bullish" and s.peer_band in ("Bottom", "Lower-Mid"):
        causes.append("peer_rank_low")
    if street_dir == "neutral" and ours_dir == "bullish":
        causes.append("over_promoted")
    if not causes:
        causes.append("other")
    return causes


def audit_from_state(suite: str = "nifty50") -> dict:
    """Run benchmark audit against current STATE without re-fetching."""
    benchmark = load_benchmark_suite(suite)
    universe = set(all_tickers())

    matched = 0
    direction_ok = 0
    severity_ok = 0
    false_sell_buy = 0
    mismatches = []
    cause_counts: Counter = Counter()

    for ticker, spec in benchmark.items():
        street = str(spec.get("street", "HOLD")).upper()
        if ticker not in STATE.scores:
            mismatches.append({"ticker": ticker, "error": "not_in_universe", "street": street})
            cause_counts["not_in_universe"] += 1
            continue
        matched += 1
        s = STATE.scores[ticker]
        ours = s.recommendation
        if _direction(ours) == _direction(street):
            direction_ok += 1
        else:
            causes = _root_cause(ticker, s, street, STATE.metrics.get(ticker))
            for c in causes:
                cause_counts[c] += 1
            mismatches.append(
                {
                    "ticker": ticker,
                    "ours": ours,
                    "street": street,
                    "Q": s.quality_grade,
                    "peer": s.peer_band,
                    "val": s.valuation_label,
                    "hard_gate": s.hard_gate_fail,
                    "comp": round(s.composite_score, 1),
                    "causes": causes,
                }
            )
        if _severity_distance(ours, street) <= 1:
            severity_ok += 1
        if street in BULLISH and ours in BEARISH:
            false_sell_buy += 1

    total = matched or 1
    return {
        "suite": suite,
        "matched": matched,
        "total_benchmark": len(benchmark),
        "in_universe": sum(1 for t in benchmark if t in universe),
        "direction_pct": round(100 * direction_ok / total, 1),
        "severity_pct": round(100 * severity_ok / total, 1),
        "false_sell_on_buy": false_sell_buy,
        "root_causes": dict(cause_counts),
        "mismatches": mismatches,
    }


def run_audit(suite: str = "nifty50", use_cache: bool = True, refresh: bool = False) -> dict:
    run_evaluation(sector_filter="all", use_cache=use_cache, refresh=refresh)
    return audit_from_state(suite)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="nifty50", choices=["nifty50", "nifty_next50", "golden", "all"])
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--csv", type=str, help="Write mismatches to CSV path")
    args = parser.parse_args()

    suites = ["nifty50", "golden"] if args.compare else [args.suite]
    reports = []
    for suite in suites:
        r = run_audit(suite=suite, use_cache=not args.refresh, refresh=args.refresh)
        reports.append(r)
        print(f"\n{suite.upper()} BENCHMARK GAP REPORT")
        print(f"Direction: {r['direction_pct']}% ({r['matched']} matched)")
        print(f"Severity:  {r['severity_pct']}%")
        print(f"False SELL on street-Buy: {r['false_sell_on_buy']}")
        if r["root_causes"]:
            print("\nBY ROOT CAUSE:")
            for cause, count in sorted(r["root_causes"].items(), key=lambda x: -x[1]):
                print(f"  {cause:22} {count}")
        print("\nTOP MISMATCHES:")
        for m in r["mismatches"][:15]:
            if "error" in m:
                print(f"  {m['ticker']:16} {m['error']}")
            else:
                causes = ",".join(m.get("causes", []))
                print(f"  {m['ticker']:16} {m['ours']:11} vs {m['street']:11} [{causes}]")

    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "benchmark_gap.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(reports if len(reports) > 1 else reports[0], f, indent=2)
    print(f"\nWrote {out_path}")

    if args.csv and reports:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=["ticker", "ours", "street", "Q", "peer", "val", "causes"],
                extrasaction="ignore",
            )
            w.writeheader()
            for m in reports[0].get("mismatches", []):
                if "error" not in m:
                    row = dict(m)
                    row["causes"] = ",".join(m.get("causes", []))
                    w.writerow(row)

    if args.json:
        print(json.dumps(reports if len(reports) > 1 else reports[0], indent=2))


if __name__ == "__main__":
    main()
