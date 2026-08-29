from screener.models import ScoreResult, StockMetrics
from screener.scoring.adjustments import (
    apply_composite_completeness_penalty,
    banking_has_core_metrics,
    calibrate_sector_composites,
    cap_banking_peer_percentile,
)
from screener.scoring.quality_grade import compute_quality_score


def test_quality_grade_decoupled_from_composite():
    m = StockMetrics("T.NS", "Tech", data_completeness=0.9)
    high_comp = ScoreResult("Tech", "it", fundamental_strength=0.5, composite_score=95, confidence=0.9)
    low_comp = ScoreResult("Tech", "it", fundamental_strength=0.5, composite_score=30, confidence=0.9)
    assert compute_quality_score(high_comp, m) == compute_quality_score(low_comp, m)


def test_banking_peer_cap_without_core_metrics():
    m = StockMetrics("X.NS", "Financial Services", sector_focus="banking")
    assert not banking_has_core_metrics(m)
    assert cap_banking_peer_percentile(85.0, m) == 69.0
    m.gnpa_pct = 2.0
    assert banking_has_core_metrics(m)
    assert cap_banking_peer_percentile(85.0, m) == 85.0


def test_completeness_penalty_reduces_score():
    raw = 80.0
    penalized = apply_composite_completeness_penalty(raw, 0.0)
    assert penalized < raw
    assert apply_composite_completeness_penalty(raw, 1.0) == raw


def test_sector_calibration_centers_mean():
    composites = {"A": 40.0, "B": 60.0, "C": 80.0}
    out = calibrate_sector_composites(composites, target_mean=57.5)
    assert abs(sum(out.values()) / 3 - 57.5) < 0.01
