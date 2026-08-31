import pytest

from screener.models import ScoreResult, StockMetrics
from screener.scoring.action_matrix import assign_action, peer_band_from_percentile
from screener.scoring.quality_grade import compute_quality_score, quality_grade_from_score


@pytest.fixture(autouse=True)
def _production_action_book(monkeypatch):
    monkeypatch.delenv("SCREENER_BENCHMARK_CALIBRATION", raising=False)
    monkeypatch.setattr(
        "screener.scoring.action_matrix._benchmark_calibration",
        lambda: {"street_overlay": False, "index_anchor": False},
    )


def _score(composite=70, fund=0.7, pctile=60, val="Fair", red=False, hard=False, conf=0.8):
    return ScoreResult(
        sector="Technology",
        sector_focus="it",
        fundamental_strength=fund,
        composite_score=composite,
        composite_percentile=pctile,
        valuation_label=val,
        red_flag=red,
        hard_gate_fail=hard,
        confidence=conf,
    )


def _metrics(ticker="TCS.NS", mcap=12_000_000_000_000, roe=45.0, **kwargs):
    return StockMetrics(
        ticker=ticker,
        sector="Technology",
        sector_focus=kwargs.pop("sector_focus", "it"),
        analysis_depth="deep",
        market_cap=mcap,
        roe_pct=roe,
        data_completeness=kwargs.pop("data_completeness", 0.85),
        **kwargs,
    )


def test_peer_band_top():
    assert peer_band_from_percentile(75) == "Top"
    assert peer_band_from_percentile(25) == "Bottom"


def test_large_cap_over_grade_c_is_avoid():
    s = _score(composite=54, fund=0.50, pctile=29, val="Over")
    m = _metrics("TCS.NS")
    assign_action(s, m)
    assert s.quality_grade == "C"
    assert s.recommendation == "AVOID"


def test_large_cap_over_grade_c_weak_rs_is_sell():
    s = _score(composite=54, fund=0.50, pctile=29, val="Over")
    m = _metrics("TCS.NS", rs_vs_nifty_pct=-12.0)
    assign_action(s, m)
    assert s.quality_grade == "C"
    assert s.recommendation == "SELL"


def test_large_cap_over_weak_rs_is_sell():
    s = _score(composite=70, fund=0.90, pctile=55, val="Over")
    m = _metrics("TCS.NS", rs_vs_nifty_pct=-12.0)
    assign_action(s, m)
    assert s.quality_grade == "A"
    assert s.recommendation == "SELL"


def test_large_cap_over_grade_a_flat_rs_is_hold():
    s = _score(composite=78, fund=0.90, pctile=60, val="Over")
    m = _metrics("TCS.NS", rs_vs_nifty_pct=0.0)
    assign_action(s, m)
    assert s.quality_grade == "A"
    assert s.recommendation == "HOLD"


def test_quality_a_fair_strong_buy():
    s = _score(composite=82, fund=0.90, pctile=78, val="Fair")
    m = _metrics("HEXT.NS", mcap=100_000_000_000, rs_vs_nifty_pct=2.0)
    assign_action(s, m)
    assert s.recommendation == "STRONG BUY"
    assert s.quality_grade == "A"


def test_midcap_grade_a_under_positive_rs_strong_buy():
    s = _score(composite=80, fund=0.90, pctile=72, val="Under")
    m = _metrics("HEXT.NS", mcap=100_000_000_000, rs_vs_nifty_pct=4.0)
    assign_action(s, m)
    assert s.recommendation == "STRONG BUY"


def test_itc_over_quality_is_hold():
    s = _score(composite=69, fund=0.70, pctile=67, val="Over", red=False, hard=False)
    m = _metrics("ITC.NS", mcap=500_000_000_000, roe=25.0, sector_focus="fmcg", rs_vs_nifty_pct=1.0)
    assign_action(s, m)
    assert s.quality_grade in ("A", "B")
    assert s.recommendation == "HOLD"


def test_hard_gate_avoid():
    s = _score(composite=40, fund=0.3, pctile=10, val="Fair", hard=True)
    m = _metrics("YESBANK.NS", mcap=300_000_000_000)
    assign_action(s, m)
    assert s.recommendation in ("AVOID", "SELL")


def test_hcltech_fair_grade_b_is_buy():
    s = _score(composite=60, fund=0.70, pctile=50, val="Fair")
    m = _metrics("HCLTECH.NS", mcap=4_500_000_000_000, roe=22.0)
    assign_action(s, m)
    assert s.recommendation in ("HOLD", "BUY")


def test_grade_b_large_cap_fair_is_buy():
    s = _score(composite=68, fund=0.70, pctile=55, val="Fair")
    m = _metrics("ICICIBANK.NS", mcap=10_000_000_000_000, roe=18.0, sector_focus="banking")
    assign_action(s, m)
    assert s.recommendation in ("BUY", "STRONG BUY", "HOLD")


def test_banking_over_soft_bands_sell_without_hard_gate():
    s = _score(composite=52, fund=0.70, pctile=25, val="Over", hard=False)
    m = _metrics(
        "YESBANK.NS",
        mcap=800_000_000_000,
        roe=7.0,
        sector_focus="banking",
        gnpa_pct=3.0,
        rs_vs_nifty_pct=1.0,
    )
    assign_action(s, m)
    assert not s.hard_gate_fail
    assert s.recommendation == "SELL"


def test_it_over_lagging_nifty_is_sell():
    s = _score(composite=58, fund=0.70, pctile=40, val="Over")
    m = _metrics("TECHM.NS", mcap=1_200_000_000_000, roe=16.0, rs_vs_nifty_pct=-12.0)
    assign_action(s, m)
    assert s.recommendation == "SELL"


def test_quality_grade_mapping():
    q = compute_quality_score(_score(fund=0.90), _metrics())
    assert quality_grade_from_score(q, False, False) == "A"
    assert quality_grade_from_score(0.70, False, False) == "B"
    assert quality_grade_from_score(0.50, False, False) == "C"
    assert quality_grade_from_score(0.30, False, False) == "D"
