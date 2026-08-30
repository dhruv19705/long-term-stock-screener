from screener.models import StockMetrics
from screener.scoring.fcff_valuation import combine_hybrid_votes, fcff_intrinsic_vote, peer_relative_votes
from screener.scoring.valuation import evaluate_valuation


def _m(ticker: str, pe=20.0, fcf_y=3.0, fcf_ttm=100.0) -> StockMetrics:
    return StockMetrics(
        ticker=ticker,
        sector="Test",
        pe=pe,
        fcf_yield_pct=fcf_y,
        free_cash_flow_ttm=fcf_ttm,
        debt_to_equity=0.5,
        ev_to_ebitda=12.0,
    )


def test_fcff_intrinsic_vote_cheaper_than_peers():
    peers = [_m("A.NS", fcf_y=2.0), _m("B.NS", fcf_y=2.5)]
    vote, gap = fcff_intrinsic_vote(_m("C.NS", fcf_y=5.0), [p.fcf_yield_pct for p in peers])
    assert vote == "Under"
    assert gap is not None and gap > 0


def test_hybrid_valuation_combines_signals():
    peers = [_m("A.NS", pe=25, fcf_y=2.0), _m("B.NS", pe=28, fcf_y=2.5), _m("C.NS", pe=30, fcf_y=1.5)]
    cheap = _m("D.NS", pe=12, fcf_y=6.0, fcf_ttm=200.0)
    result = evaluate_valuation(cheap, peers, "FMCG", cyclical_sectors=[])
    assert result.label in ("Under", "Fair")
    assert result.valuation_method != "fallback"


def test_combine_hybrid_votes_majority():
    assert combine_hybrid_votes(["Under", "Under", "Fair"]) == "Under"
    assert combine_hybrid_votes(["Over", "Fair", "Fair"]) == "Fair"
