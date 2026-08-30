import statistics

from screener.interpret.risk_matcher import (
    _beta_penalty,
    diversify_picks,
    match_stock,
)
from screener.models import FitResult, QuestionAnswer, RiskProfile, ScoreResult, StockInterpretation, StockMetrics


def _interp(ticker, focus, depth="standard", risk=25.0, composite=70, val="Fair", grade="B", pctile=70):
    return StockInterpretation(
        ticker=ticker,
        sector=focus,
        sector_focus=focus,
        analysis_depth=depth,
        recommendation="BUY",
        composite_score=composite,
        composite_percentile=pctile,
        quality_grade=grade,
        peer_band="Top" if pctile >= 70 else "Upper-Mid",
        stock_risk_score=risk,
        confidence=0.7,
        valuation_label=val,
        headline="test",
        questions=[QuestionAnswer("GQ1", "Q?", "leverage_risk", "good", {})],
        bull_case=[],
        bear_case=[],
        key_risk="",
        verdict="",
    )


def test_beta_penalty_interpolates():
    schedule = {
        "comfort": 1.0,
        "knots": [
            {"beta": 1.0, "penalty": 0},
            {"beta": 1.3, "penalty": 6},
            {"beta": 1.6, "penalty": 14},
            {"beta": 2.2, "penalty": 25},
        ],
        "exclude_above": 2.2,
    }
    assert _beta_penalty(1.0, schedule) == 0.0
    assert 9.0 < _beta_penalty(1.45, schedule) < 11.0
    assert _beta_penalty(2.2, schedule) == 25.0


def test_conservative_excludes_high_beta_not_moderate():
    schedule = {
        "comfort": 1.0,
        "knots": [
            {"beta": 1.0, "penalty": 0},
            {"beta": 1.3, "penalty": 6},
            {"beta": 1.6, "penalty": 14},
            {"beta": 2.2, "penalty": 25},
        ],
        "exclude_above": 2.2,
    }
    profile = RiskProfile(id="conservative", label="Cons", cyclical_ok=False, max_stock_risk=50, max_beta=1.0)
    m_ok = StockMetrics("HUL.NS", "Consumer Defensive", sector_focus="fmcg", cyclical=False, beta=1.4)
    m_bad = StockMetrics("SMALL.NS", "Consumer Defensive", sector_focus="fmcg", cyclical=False, beta=2.3)
    i_ok = _interp("HUL.NS", "fmcg", risk=30.0, val="Fair")
    i_bad = _interp("SMALL.NS", "fmcg", risk=30.0, val="Fair")
    fit_ok = match_stock(profile, i_ok, m_ok, quality_score=0.6)
    fit_bad = match_stock(profile, i_bad, m_bad, quality_score=0.6)
    assert not fit_ok.exclude
    assert fit_bad.exclude


def test_diversify_picks_spreads_sectors():
    profile = RiskProfile(id="moderate", label="Mod", diversify_sectors=True, diversification_level="moderate")
    picks = [
        FitResult("A.NS", 80, "Good", False, [], sector_focus="banking", analysis_depth="deep"),
        FitResult("B.NS", 78, "Good", False, [], sector_focus="banking", analysis_depth="deep"),
        FitResult("C.NS", 77, "Good", False, [], sector_focus="banking", analysis_depth="deep"),
        FitResult("D.NS", 76, "Good", False, [], sector_focus="banking", analysis_depth="deep"),
        FitResult("TCS.NS", 75, "Good", False, [], sector_focus="it", analysis_depth="deep"),
        FitResult("HUL.NS", 74, "Good", False, [], sector_focus="fmcg", analysis_depth="standard"),
        FitResult("MARUTI.NS", 73, "Good", False, [], sector_focus="auto", analysis_depth="standard"),
    ]
    out = diversify_picks(picks, profile)
    sectors = {p.sector_focus for p in out}
    assert len(sectors) >= 3


def test_fit_score_spreads_by_quality():
    profile = RiskProfile(id="conservative", label="Cons", cyclical_ok=False, max_stock_risk=50, max_beta=1.0)
    m1 = StockMetrics("ZYDUS.NS", "Healthcare", sector_focus="pharma", cyclical=False, max_drawdown_1y_pct=-10)
    m2 = StockMetrics("ALKEM.NS", "Healthcare", sector_focus="pharma", cyclical=False, max_drawdown_1y_pct=-20)
    i1 = _interp("ZYDUS.NS", "pharma", composite=83, grade="A", pctile=85, val="Fair")
    i2 = _interp("ALKEM.NS", "pharma", composite=65, grade="C", pctile=55, val="Fair")
    f1 = match_stock(profile, i1, m1, quality_score=0.82)
    f2 = match_stock(profile, i2, m2, quality_score=0.58)
    assert f1.fit_score > f2.fit_score
    scores = [f1.fit_score, f2.fit_score]
    assert statistics.pstdev(scores) > 2
