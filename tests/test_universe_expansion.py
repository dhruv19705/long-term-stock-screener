from screener.config_loader import all_tickers


def test_universe_expansion():
    tickers = all_tickers()
    assert len(tickers) >= 200
    for t in (
        "TATAMOTORS.NS",
        "HDFCLIFE.NS",
        "SBILIFE.NS",
        "ADANIENT.NS",
        "JIOFIN.NS",
        "SHRIRAMFIN.NS",
        "DMART.NS",
        "CHOLAFIN.NS",
    ):
        assert t in tickers
