"""Benchmark summary for API — Nifty50/golden alignment and distribution."""

from __future__ import annotations

import time
from collections import Counter
from typing import Any, Dict

from screener.pipeline import STATE
from scripts.benchmark_gap_report import audit_from_state

_CACHE: Dict[str, Any] = {}
_CACHE_AT: float = 0.0
_CACHE_TTL_SEC = 3600.0


def invalidate_benchmark_cache() -> None:
    global _CACHE_AT
    _CACHE_AT = 0.0


def _distribution() -> Dict[str, Any]:
    recs = Counter(s.recommendation for s in STATE.scores.values())
    total = sum(recs.values()) or 1
    bullish = recs.get("STRONG BUY", 0) + recs.get("BUY", 0)
    bearish = recs.get("AVOID", 0) + recs.get("SELL", 0)
    return {
        "counts": dict(recs),
        "total": total,
        "bullish_pct": round(100 * bullish / total, 1),
        "bearish_pct": round(100 * bearish / total, 1),
        "targets": {"bullish_min": 30, "bullish_max": 42, "bearish_min": 15, "bearish_max": 25},
    }


def _suite_summary(suite: str) -> Dict[str, Any]:
    report = audit_from_state(suite=suite)
    mismatches = report.get("mismatches", [])[:10]
    top = []
    for m in mismatches:
        if "error" in m:
            top.append({"ticker": m["ticker"], "error": m["error"], "street": m.get("street")})
        else:
            top.append(
                {
                    "ticker": m["ticker"],
                    "ours": m["ours"],
                    "street": m["street"],
                    "causes": m.get("causes", []),
                }
            )
    return {
        "suite": suite,
        "direction_pct": report.get("direction_pct"),
        "severity_pct": report.get("severity_pct"),
        "false_sell_on_buy": report.get("false_sell_on_buy"),
        "matched": report.get("matched"),
        "top_mismatches": top,
    }


def benchmark_summary(force: bool = False) -> Dict[str, Any]:
    global _CACHE, _CACHE_AT
    now = time.time()
    if not force and _CACHE and (now - _CACHE_AT) < _CACHE_TTL_SEC:
        return _CACHE

    out = {
        "distribution": _distribution(),
        "nifty50": _suite_summary("nifty50"),
        "golden": _suite_summary("golden"),
        "calibrated_count": sum(1 for s in STATE.scores.values() if s.calibration_applied),
        "generated_at": int(now),
    }
    _CACHE = out
    _CACHE_AT = now
    return out
