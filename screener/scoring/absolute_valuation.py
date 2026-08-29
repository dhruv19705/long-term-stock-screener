from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from screener.config_loader import load_valuation_bands
from screener.models import StockMetrics


def _sector_bands(model_sector: str) -> Dict[str, Any]:
    cfg = load_valuation_bands()
    sectors = cfg.get("sectors") or {}
    defaults = cfg.get("defaults") or {}
    spec = sectors.get(model_sector) or sectors.get("DEFAULT") or {}
    merged = dict(defaults)
    for key, val in spec.items():
        if key == "metrics":
            merged["metrics"] = val
        elif isinstance(val, dict):
            merged[key] = {**(defaults.get(key) or {}), **val}
    if "metrics" not in merged:
        merged["metrics"] = spec.get("metrics") or ["pe", "pb"]
    return merged


def _label_from_upper_band(value: float, under_max: float, fair_max: float) -> str:
    if value <= under_max:
        return "Under"
    if value <= fair_max:
        return "Fair"
    return "Over"


def _label_from_lower_band(value: float, under_min: float, fair_min: float) -> str:
    """Higher yield = cheaper."""
    if value >= under_min:
        return "Under"
    if value >= fair_min:
        return "Fair"
    return "Over"


def _metric_label(metric: str, value: Optional[float], bands: Dict[str, Any]) -> Optional[str]:
    if value is None or not np.isfinite(value) or value <= 0:
        return None
    spec = bands.get(metric)
    if not spec:
        return None
    if "under_min" in spec:
        return _label_from_lower_band(float(value), float(spec["under_min"]), float(spec["fair_min"]))
    if "under_max" in spec:
        return _label_from_upper_band(float(value), float(spec["under_max"]), float(spec["fair_max"]))
    return None


def _metric_value(m: StockMetrics, metric: str) -> Optional[float]:
    if metric == "pe":
        return m.pe if m.pe is not None and m.pe > 0 else None
    if metric == "pb":
        return m.pb if m.pb is not None and m.pb > 0 else None
    if metric == "peg":
        if m.peg is not None and m.peg > 0:
            return m.peg
        if m.pe is not None and m.profit_growth_pct is not None and m.profit_growth_pct > 0:
            return float(m.pe) / float(m.profit_growth_pct)
        return None
    if metric == "ev_ebitda":
        return m.ev_to_ebitda if m.ev_to_ebitda is not None and m.ev_to_ebitda > 0 else None
    if metric == "earnings_yield_pct":
        return (100.0 / m.pe) if m.pe is not None and m.pe > 0 else None
    if metric == "fcf_yield_pct":
        return m.fcf_yield_pct
    return None


def _combine_votes(votes: List[str]) -> str:
    if not votes:
        return "Unknown"
    under = votes.count("Under")
    over = votes.count("Over")
    if under > over and under >= len(votes) // 2 + (1 if len(votes) % 2 else 0):
        return "Under"
    if over > under and over >= len(votes) // 2 + (1 if len(votes) % 2 else 0):
        return "Over"
    if under == over and under > 0:
        return "Fair"
    if len(set(votes)) == 1:
        return votes[0]
    return "Fair"


def absolute_valuation_label(
    m: StockMetrics,
    model_sector: str,
    cyclical_sectors: Optional[List[str]] = None,
) -> Tuple[str, Optional[float]]:
    """
    Assign Under / Fair / Over from absolute sector bands (not peer-relative).
    """
    bands = _sector_bands(model_sector)
    metrics = bands.get("metrics") or ["pe", "pb"]
    votes: List[str] = []
    ref: Optional[float] = None

    for metric in metrics:
        val = _metric_value(m, metric)
        lbl = _metric_label(metric, val, bands)
        if lbl:
            votes.append(lbl)
            if ref is None and val is not None:
                ref = float(val)

    label = _combine_votes(votes)

    cyclical_sectors = cyclical_sectors or []
    cyc_pen = cyclical_margin_penalty(m, model_sector, cyclical_sectors)
    if label == "Under" and cyc_pen >= 0.4:
        label = "Fair"

    return label, ref


def absolute_valuation_label_banking(m: StockMetrics) -> Tuple[str, Optional[float]]:
    return absolute_valuation_label(m, "BANKING")


def absolute_valuation_label_insurance(m: StockMetrics) -> Tuple[str, Optional[float]]:
    return absolute_valuation_label(m, "INSURANCE")


def absolute_valuation_label_it(m: StockMetrics) -> Tuple[str, Optional[float]]:
    return absolute_valuation_label(m, "IT")


def cyclical_margin_penalty(m: StockMetrics, model_sector: str, cyclical_sectors: List[str]) -> float:
    """
    Return 0..1 penalty: high when margins likely at cycle peak (cheap P/E trap).
    """
    if model_sector not in cyclical_sectors:
        return 0.0
    om = m.operating_margin_pct
    trend = m.operating_margin_trend_pct
    if om is None:
        return 0.0
    penalty = 0.0
    if trend is not None and trend > 3.0:
        penalty += 0.3
    if om > 18.0:
        penalty += 0.2
    return min(1.0, penalty)
