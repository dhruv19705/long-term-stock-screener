"""Sector scoring audit: breakdown, calibration stats, golden-set alignment."""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from screener.config_loader import load_golden_set
from screener.pipeline import run_evaluation, STATE
from screener.scoring.action_matrix import ACTION_LADDER

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


def _golden_summary_from_state() -> dict:
    golden = load_golden_set().get("tickers") or {}
    matched = direction_ok = severity_ok = false_sell_buy = 0
    for ticker, spec in golden.items():
        if ticker not in STATE.scores:
            continue
        matched += 1
        street = str(spec.get("street", "HOLD")).upper()
        ours = STATE.scores[ticker].recommendation
        if _direction(ours) == _direction(street):
            direction_ok += 1
        if _severity_distance(ours, street) <= 1:
            severity_ok += 1
        cap = spec.get("cap_tier", "large")
        if street in BULLISH and ours in BEARISH and cap in ("large", "mega"):
            false_sell_buy += 1
    total = matched or 1
    return {
        "matched": matched,
        "direction_pct": round(100 * direction_ok / total, 1),
        "severity_pct": round(100 * severity_ok / total, 1),
        "false_sell_on_buy_large": false_sell_buy,
    }


def run_sector_audit(use_cache: bool = True) -> dict:
    run_evaluation(sector_filter="all", use_cache=use_cache)

    by_sector: dict[str, list] = defaultdict(list)
    for t, s in STATE.scores.items():
        m = STATE.metrics[t]
        row = {
            "ticker": t,
            "composite": round(s.composite_score, 1),
            "rec": s.recommendation,
            "val": s.valuation_label,
            "grade": s.quality_grade,
            "breakdown": dict(s.score_breakdown or {}),
        }
        by_sector[m.sector_focus].append(row)

    sector_stats = {}
    for sector, rows in sorted(by_sector.items()):
        scores = [r["composite"] for r in rows]
        breakdown_keys: Counter = Counter()
        breakdown_avg: dict[str, float] = defaultdict(float)
        for r in rows:
            for k, v in r["breakdown"].items():
                breakdown_keys[k] += 1
                breakdown_avg[k] += v
        n = len(rows) or 1
        sector_stats[sector] = {
            "count": len(rows),
            "mean_composite": round(statistics.mean(scores), 1),
            "std_composite": round(statistics.pstdev(scores), 1) if len(scores) > 1 else 0.0,
            "rec_distribution": dict(Counter(r["rec"] for r in rows)),
            "val_distribution": dict(Counter(r["val"] for r in rows)),
            "factor_means": {k: round(breakdown_avg[k] / breakdown_keys[k], 3) for k in breakdown_keys},
        }

    golden = _golden_summary_from_state()
    return {
        "universe_count": len(STATE.scores),
        "overall_rec": dict(Counter(s.recommendation for s in STATE.scores.values())),
        "sector_stats": sector_stats,
        "golden_alignment": {
            "matched": golden["matched"],
            "direction_pct": golden["direction_pct"],
            "severity_pct": golden["severity_pct"],
            "false_sell_on_buy_large": golden["false_sell_on_buy_large"],
        },
    }


def main() -> None:
    report = run_sector_audit(use_cache=True)
    out_path = Path("docs/sector_scoring_audit.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nWrote {out_path}")
    if report["golden_alignment"]["false_sell_on_buy_large"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
