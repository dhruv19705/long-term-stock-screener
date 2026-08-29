"""Effective growth metrics with yfinance fallbacks for sparse CAGR fields."""

from __future__ import annotations

from typing import Optional

from screener.models import StockMetrics


def effective_revenue_cagr(m: StockMetrics) -> Optional[float]:
    if m.revenue_cagr_3y_pct is not None:
        return m.revenue_cagr_3y_pct
    if m.revenue_growth_pct is not None:
        return m.revenue_growth_pct
    return None


def effective_profit_cagr(m: StockMetrics) -> Optional[float]:
    if m.profit_cagr_3y_pct is not None:
        return m.profit_cagr_3y_pct
    if m.profit_growth_pct is not None:
        return m.profit_growth_pct
    return None


def effective_growth_score_inputs(m: StockMetrics) -> dict[str, Optional[float]]:
    return {
        "rev_cagr": effective_revenue_cagr(m),
        "rev_yoy": m.revenue_growth_pct,
        "prof_yoy": m.profit_growth_pct,
        "prof_cagr": effective_profit_cagr(m),
    }
