from screener.config_loader import BUCKET_KEYS, sector_focus_for_ticker, ticker_index


def test_universe_no_duplicate_tickers():
    idx = ticker_index()
    assert len(idx) >= 400


def test_relocated_tickers_in_correct_buckets():
    idx = ticker_index()
    assert idx["TRENT.NS"]["bucket"] == "fmcg"
    assert idx["M&M.NS"]["bucket"] == "auto"
    assert idx["IRCTC.NS"]["bucket"] == "capital_goods"
    assert sector_focus_for_ticker("TRENT.NS") == "fmcg"


def test_all_buckets_known():
    idx = ticker_index()
    for meta in idx.values():
        assert meta["bucket"] in BUCKET_KEYS
