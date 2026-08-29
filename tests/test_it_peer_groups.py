from screener.config_loader import peer_set
from screener.models import StockMetrics


def _m(ticker: str, cap: float) -> StockMetrics:
    return StockMetrics(ticker=ticker, sector="Technology", sector_focus="it", market_cap=cap)


def test_it_large_cap_sub_cohort():
    metrics = {
        "TCS.NS": _m("TCS.NS", 12_000_000_000_000),
        "INFY.NS": _m("INFY.NS", 7_000_000_000_000),
        "HCLTECH.NS": _m("HCLTECH.NS", 4_500_000_000_000),
        "WIPRO.NS": _m("WIPRO.NS", 2_500_000_000_000),
        "TECHM.NS": _m("TECHM.NS", 1_500_000_000_000),
        "HEXT.NS": _m("HEXT.NS", 80_000_000_000),
        "NETWEB.NS": _m("NETWEB.NS", 60_000_000_000),
        "AFFLE.NS": _m("AFFLE.NS", 50_000_000_000),
        "TANLA.NS": _m("TANLA.NS", 40_000_000_000),
        "ROUTE.NS": _m("ROUTE.NS", 30_000_000_000),
        "MAPMYINDIA.NS": _m("MAPMYINDIA.NS", 25_000_000_000),
    }
    key, peers = peer_set("TCS.NS", metrics)
    assert key == "it_large"
    assert "TCS.NS" in peers
    assert "HEXT.NS" not in peers
    assert len(peers) >= 5


def test_it_mid_cap_sub_cohort():
    metrics = {
        "HEXT.NS": _m("HEXT.NS", 80_000_000_000),
        "NETWEB.NS": _m("NETWEB.NS", 60_000_000_000),
        "AFFLE.NS": _m("AFFLE.NS", 50_000_000_000),
        "TANLA.NS": _m("TANLA.NS", 40_000_000_000),
        "ROUTE.NS": _m("ROUTE.NS", 30_000_000_000),
        "MAPMYINDIA.NS": _m("MAPMYINDIA.NS", 25_000_000_000),
        "TCS.NS": _m("TCS.NS", 12_000_000_000_000),
    }
    key, peers = peer_set("HEXT.NS", metrics)
    assert key in ("it_mid", "it")
