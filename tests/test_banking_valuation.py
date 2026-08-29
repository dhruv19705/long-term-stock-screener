from screener.models import StockMetrics
from screener.scoring.absolute_valuation import absolute_valuation_label
from screener.scoring.banking_valuation import pb_roe_residual


def test_pb_roe_residual_ranks_cheap():
    peers = [
        StockMetrics("A.NS", "Financial Services", "banking", pb=1.0, roe_pct=10),
        StockMetrics("B.NS", "Financial Services", "banking", pb=2.0, roe_pct=15),
        StockMetrics("C.NS", "Financial Services", "banking", pb=3.0, roe_pct=20),
        StockMetrics("D.NS", "Financial Services", "banking", pb=1.2, roe_pct=20),
        StockMetrics("E.NS", "Financial Services", "banking", pb=4.0, roe_pct=12),
    ]
    resid = pb_roe_residual(peers)
    assert resid["D.NS"] is not None
    assert resid["E.NS"] is not None
    assert resid["D.NS"] < resid["E.NS"]


def test_absolute_banking_pb_bands():
    cheap = StockMetrics("X.NS", "Financial Services", pb=1.5)
    fair = StockMetrics("Y.NS", "Financial Services", pb=2.8)
    rich = StockMetrics("Z.NS", "Financial Services", pb=4.0)
    assert absolute_valuation_label(cheap, "BANKING")[0] == "Under"
    assert absolute_valuation_label(fair, "BANKING")[0] == "Fair"
    assert absolute_valuation_label(rich, "BANKING")[0] == "Over"


def test_absolute_it_pe_bands():
    cheap = StockMetrics("TCS.NS", "Technology", pe=18)
    fair = StockMetrics("INFY.NS", "Technology", pe=28)
    rich = StockMetrics("WIPRO.NS", "Technology", pe=35)
    assert absolute_valuation_label(cheap, "IT")[0] == "Under"
    assert absolute_valuation_label(fair, "IT")[0] == "Fair"
    assert absolute_valuation_label(rich, "IT")[0] == "Over"


def test_absolute_fmcg_pe_bands():
    cheap = StockMetrics("ITC.NS", "Consumer", pe=25)
    rich = StockMetrics("HUL.NS", "Consumer", pe=50)
    assert absolute_valuation_label(cheap, "FMCG")[0] == "Under"
    assert absolute_valuation_label(rich, "FMCG")[0] == "Over"
