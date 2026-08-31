from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from screener.models import StockMetrics


def pb_roe_residual(
    metrics_list: List[StockMetrics],
) -> Dict[str, Optional[float]]:
    """
    Within peer set: regress P/B on ROE; residual = actual P/B - fitted.
    Negative residual => cheaper than ROE implies.
    """
    xs: List[float] = []
    ys: List[float] = []
    tickers: List[str] = []
    for m in metrics_list:
        if m.pb is not None and m.roe_pct is not None and m.pb > 0 and np.isfinite(m.pb) and np.isfinite(m.roe_pct):
            xs.append(float(m.roe_pct))
            ys.append(float(m.pb))
            tickers.append(m.ticker)
    out: Dict[str, Optional[float]] = {m.ticker: None for m in metrics_list}
    if len(xs) < 4:
        # fallback: relative to median P/B
        med = float(np.median(ys)) if ys else None
        for m in metrics_list:
            if m.pb is not None and med and med > 0:
                out[m.ticker] = float(m.pb) / med - 1.0
        return out
    x = np.array(xs)
    y = np.array(ys)
    # simple OLS: y = a + b x
    b, a = np.polyfit(x, y, 1)
    for t, xi, yi in zip(tickers, xs, ys):
        fitted = a + b * xi
        out[t] = float(yi - fitted)
    return out


def valuation_label_from_residual(
    residual: Optional[float],
    pb: Optional[float],
    peer_median_pb: Optional[float],
    roe_pct: Optional[float] = None,
) -> Tuple[str, Optional[float]]:
    """
    Under if residual < -0.15 * scale or pb < 0.85 * median.
    High-ROE private banks get a wider Fair band before Over.
    """
    over_residual = 0.65 if roe_pct is not None and roe_pct > 15.0 else 0.55
    if residual is not None and np.isfinite(residual):
        if residual < -0.25:
            return "Under", residual
        if residual > over_residual:
            return "Over", residual
        return "Fair", residual
    if pb is not None and peer_median_pb not in (None, 0):
        ratio = pb / peer_median_pb
        if ratio < 0.85:
            return "Under", residual
        if ratio > 1.15:
            return "Over", residual
        return "Fair", residual
    return "Unknown", residual
