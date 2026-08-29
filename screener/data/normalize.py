from __future__ import annotations

from functools import lru_cache
from typing import Optional

from screener.models import StockMetrics


@lru_cache(maxsize=1)
def _debt_adjustments() -> dict:
    from screener.config_loader import load_debt_adjustments

    return load_debt_adjustments()


def normalize_debt_to_equity(raw: Optional[float]) -> Optional[float]:
    """yfinance often reports D/E as a percentage (e.g. 954 → 9.54 ratio after /100)."""
    if raw is None:
        return None
    val = float(raw)
    if val > 4.0:
        return val / 100.0
    return val


def adjust_debt_for_finance_subsidiary(ticker: str, raw_de: Optional[float]) -> Optional[float]:
    """Cap or adjust D/E for auto OEMs with consolidated finance subsidiary debt."""
    if raw_de is None:
        return None
    adjustments = (_debt_adjustments().get("adjustments") or {}).get(ticker)
    if not adjustments:
        return raw_de
    strategy = adjustments.get("strategy", "cap_ratio")
    if strategy == "cap_ratio":
        cap = float(adjustments.get("cap_ratio", 1.5))
        return min(float(raw_de), cap)
    return raw_de


def clamp_pct(val: Optional[float], lo: float = -50.0, hi: float = 80.0) -> Optional[float]:
    if val is None:
        return None
    return max(lo, min(hi, float(val)))


def sanitize_ratio(val: Optional[float], lo: float = 0.0, hi: float = 500.0) -> Optional[float]:
    if val is None:
        return None
    v = float(val)
    if v <= lo or v > hi:
        return None
    return v


def sanitize_metrics(m: StockMetrics) -> StockMetrics:
    """Clamp obvious yfinance outliers before scoring."""
    d = m.to_dict()
    ticker = d.get("ticker", "")
    de = normalize_debt_to_equity(d.get("debt_to_equity"))
    d["debt_to_equity"] = adjust_debt_for_finance_subsidiary(ticker, de)
    d["roe_pct"] = clamp_pct(d.get("roe_pct"), -50, 80)
    d["roa_pct"] = clamp_pct(d.get("roa_pct"), -20, 30)
    d["operating_margin_pct"] = clamp_pct(d.get("operating_margin_pct"), -50, 60)
    d["profit_margin_pct"] = clamp_pct(d.get("profit_margin_pct"), -50, 60)
    d["ebitda_margin_pct"] = clamp_pct(d.get("ebitda_margin_pct"), -50, 60)
    d["pe"] = sanitize_ratio(d.get("pe"), 0, 500)
    d["pb"] = sanitize_ratio(d.get("pb"), 0, 50)
    d["ev_to_ebitda"] = sanitize_ratio(d.get("ev_to_ebitda"), 0, 100)
    d["beta"] = clamp_pct(d.get("beta"), -1, 4) if d.get("beta") is not None else None
    return StockMetrics(**d)
