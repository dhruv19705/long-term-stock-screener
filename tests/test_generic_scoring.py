from screener.models import StockMetrics
from screener.scoring.generic import score_generic_group


def _m(ticker: str, **kwargs) -> StockMetrics:
    base = dict(
        ticker=ticker,
        sector="Consumer Defensive",
        sector_focus="fmcg",
        model_sector="FMCG",
        analysis_depth="standard",
        pe=25.0,
        pb=5.0,
        roe_pct=20.0,
        operating_margin_pct=15.0,
        ebitda_margin_pct=16.0,
        roce_pct=18.0,
        revenue_growth_pct=8.0,
        profit_growth_pct=10.0,
        revenue_cagr_3y_pct=7.0,
        debt_to_equity=0.3,
        interest_coverage=5.0,
        return_6m_pct=5.0,
        rs_vs_nifty_pct=2.0,
        max_drawdown_1y_pct=-15.0,
        data_completeness=0.8,
    )
    base.update(kwargs)
    return StockMetrics(**base)


def test_fmcg_scoring_produces_ranked_results():
    peers = [
        _m("HINDUNILVR.NS", roe_pct=25, operating_margin_pct=22, pe=30),
        _m("DABUR.NS", roe_pct=18, operating_margin_pct=14, pe=35),
        _m("ITC.NS", roe_pct=22, operating_margin_pct=18, pe=28),
        _m("MARICO.NS", roe_pct=20, operating_margin_pct=16, pe=32),
        _m("BRITANNIA.NS", roe_pct=19, operating_margin_pct=15, pe=33),
    ]
    results = score_generic_group(peers, "FMCG", "fmcg")
    assert len(results) == 5
    scores = [r.composite_score for r in results.values()]
    assert max(scores) > min(scores)
    assert results["HINDUNILVR.NS"].composite_score > results["DABUR.NS"].composite_score
    assert results["HINDUNILVR.NS"].analysis_depth == "standard"
    assert results["HINDUNILVR.NS"].recommendation in ("BUY", "STRONG BUY", "HOLD", "AVOID", "SELL")


def test_composite_percentile_assigned():
    peers = [_m(f"T{i}.NS", roe_pct=10 + i * 2) for i in range(6)]
    results = score_generic_group(peers, "FMCG", "fmcg")
    assert all(r.composite_percentile is not None for r in results.values())
