from scripts.benchmark_gap_report import run_audit

import os

os.environ["SCREENER_BENCHMARK_CALIBRATION"] = "1"


def test_nifty50_direction_match():
    report = run_audit(suite="nifty50", use_cache=True)
    assert report["matched"] >= 45
    assert report["direction_pct"] >= 75.0
    # Absolute book can SELL expensive/lagging street-Buys; do not re-floor them.
    assert report["false_sell_on_buy"] <= 8


def test_nifty50_severity_match():
    report = run_audit(suite="nifty50", use_cache=True)
    assert report["severity_pct"] >= 90.0
