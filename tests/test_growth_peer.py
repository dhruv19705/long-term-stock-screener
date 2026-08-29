from screener.scoring.growth import effective_revenue_cagr
from screener.scoring.peer_stats import shrink_percentile
from screener.models import StockMetrics


def test_effective_revenue_cagr_fallback():
    m = StockMetrics("TCS.NS", "IT", revenue_growth_pct=12.0)
    assert effective_revenue_cagr(m) == 12.0
    m2 = StockMetrics("TCS.NS", "IT", revenue_cagr_3y_pct=15.0, revenue_growth_pct=8.0)
    assert effective_revenue_cagr(m2) == 15.0


def test_shrink_percentile_small_peer_group():
    assert shrink_percentile(90.0, 3, 8) == 65.0
    assert shrink_percentile(90.0, 10, 8) == 90.0
