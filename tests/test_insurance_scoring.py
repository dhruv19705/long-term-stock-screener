from screener.config_loader import insurance_tickers, load_insurance_metrics
from screener.pipeline import run_evaluation, STATE


def test_insurance_tickers_in_universe():
    assert "HDFCLIFE.NS" in insurance_tickers()
    assert "SBILIFE.NS" in insurance_tickers()


def test_insurance_scoring_not_bottom_grade_d():
    run_evaluation(sector_filter="insurance", use_cache=True)
    for t in ("HDFCLIFE.NS", "SBILIFE.NS"):
        assert t in STATE.scores
        s = STATE.scores[t]
        assert s.sector_focus == "insurance"
        assert s.model_sector == "INSURANCE"
        assert s.quality_grade != "D"
        assert s.peer_band != "Bottom"


def test_insurance_curated_metrics_loaded():
    metrics = load_insurance_metrics()
    assert "HDFCLIFE.NS" in metrics
    assert metrics["HDFCLIFE.NS"]["solvency_ratio_pct"] >= 150
