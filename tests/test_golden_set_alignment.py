from scripts.golden_set_audit import run_audit

import os

os.environ["SCREENER_BENCHMARK_CALIBRATION"] = "1"


def test_golden_set_large_cap_alignment():
    report = run_audit(use_cache=True, large_cap_only=True)
    assert report["matched"] >= 20
    assert report["direction_pct"] >= 70.0
    assert report["severity_pct"] >= 88.0
    assert report["false_sell_on_buy_large"] <= 4


def test_golden_set_no_hard_gate_large_high_comp():
    report = run_audit(use_cache=True, large_cap_only=True)
    assert report["hard_gate_large_high_comp"] == 0
