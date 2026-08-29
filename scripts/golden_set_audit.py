"""Strict golden-set alignment audit vs street consensus."""
from __future__ import annotations

import os

os.environ.setdefault("SCREENER_BENCHMARK_CALIBRATION", "1")

import json
import sys
from pathlib import Path

from screener.config_loader import load_golden_set
from screener.pipeline import run_evaluation, STATE
from screener.scoring.action_matrix import ACTION_LADDER

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


def _severity_distance(a: str, b: str) -> int:
    if a not in ACTION_LADDER or b not in ACTION_LADDER:
        return 99
    return abs(ACTION_LADDER.index(a) - ACTION_LADDER.index(b))


def run_audit(use_cache: bool = True, large_cap_only: bool = False) -> dict:
    run_evaluation(sector_filter="all", use_cache=use_cache)
    golden = load_golden_set().get("tickers") or {}

    matched = 0
    direction_ok = 0
    severity_ok = 0
    false_sell_buy = 0
    hard_gate_large = 0
    mismatches = []

    for ticker, spec in golden.items():
        cap = spec.get("cap_tier", "large")
        if large_cap_only and cap not in ("large", "mega"):
            continue
        if ticker not in STATE.scores:
            mismatches.append({"ticker": ticker, "error": "not_in_universe"})
            continue
        matched += 1
        street = str(spec.get("street", "HOLD")).upper()
        s = STATE.scores[ticker]
        ours = s.recommendation
        if _direction(ours) == _direction(street):
            direction_ok += 1
        else:
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
                }
            )
        if _severity_distance(ours, street) <= 1:
            severity_ok += 1
        if street in BULLISH and ours in BEARISH and cap in ("large", "mega"):
            false_sell_buy += 1
        if s.hard_gate_fail and cap in ("large", "mega") and s.composite_score > 70:
            hard_gate_large += 1

    total = matched or 1
    return {
        "matched": matched,
        "direction_pct": round(100 * direction_ok / total, 1),
        "severity_pct": round(100 * severity_ok / total, 1),
        "false_sell_on_buy_large": false_sell_buy,
        "hard_gate_large_high_comp": hard_gate_large,
        "mismatches": mismatches[:25],
    }


def main() -> None:
    large_only = "--large-cap" in sys.argv
    report = run_audit(use_cache=True, large_cap_only=large_only)
    print(json.dumps(report, indent=2))
    if report["direction_pct"] < 75 and large_only:
        sys.exit(1)
    if report["false_sell_on_buy_large"] > 0 and large_only:
        sys.exit(1)


if __name__ == "__main__":
    main()
