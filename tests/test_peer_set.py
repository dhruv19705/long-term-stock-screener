from screener.config_loader import all_tickers, peer_set, sector_focus_for_ticker, ticker_index


def test_universe_size():
    tickers = all_tickers()
    assert len(tickers) >= 175


def test_sector_focus_known():
    assert sector_focus_for_ticker("TCS.NS") == "it"
    assert sector_focus_for_ticker("HDFCBANK.NS") == "banking"
    assert sector_focus_for_ticker("HINDUNILVR.NS") == "fmcg"
    assert sector_focus_for_ticker("MARUTI.NS") == "auto"


def test_peer_set_not_singleton():
    key, peers = peer_set("TCS.NS")
    assert key == "it"
    assert len(peers) >= 10

    key2, peers2 = peer_set("HDFCBANK.NS")
    assert key2.startswith("banking")
    assert len(peers2) >= 8

    key3, peers3 = peer_set("HINDUNILVR.NS")
    assert key3 == "fmcg"
    assert len(peers3) >= 10


def test_ticker_index_metadata():
    idx = ticker_index()
    tcs = idx["TCS.NS"]
    assert tcs["analysis_depth"] == "deep"
    assert tcs["model_sector"] == "IT"
    hul = idx["HINDUNILVR.NS"]
    assert hul["analysis_depth"] == "standard"
    assert hul["model_sector"] == "FMCG"
