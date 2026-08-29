"""Resolve sector-specific metric bands from sector_weights.yaml."""

from __future__ import annotations

from typing import Dict, Tuple

from screener.config_loader import load_sector_weights
from screener.models import StockMetrics


def _sector_config(model_sector: str) -> Dict:
    sw = load_sector_weights()
    return sw.get(model_sector) or sw.get("DEFAULT", {})


def metric_bands(model_sector: str, metric: str, default_good: float, default_bad: float) -> Tuple[float, float]:
    spec = (_sector_config(model_sector).get("metrics") or {}).get(metric)
    if not spec:
        return default_good, default_bad
    good = float(spec["good"])
    bad = float(spec.get("warn", default_bad))
    return good, bad


def margin_value(m: StockMetrics, model_sector: str) -> float | None:
    if model_sector == "FMCG" and m.ebitda_margin_pct is not None:
        return m.ebitda_margin_pct
    return m.operating_margin_pct


def margin_bands(model_sector: str) -> Tuple[float, float]:
    if model_sector == "FMCG":
        good, bad = metric_bands(model_sector, "ebitda_margin_pct", 15.0, 10.0)
        if (_sector_config(model_sector).get("metrics") or {}).get("ebitda_margin_pct"):
            return good, bad
    return metric_bands(model_sector, "operating_margin_pct", 12.0, 5.0)


def growth_bands(model_sector: str) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    rev_good, rev_bad = metric_bands(model_sector, "revenue_growth_pct", 10.0, 2.0)
    prof_good, prof_bad = 10.0, 0.0
    return (rev_good, rev_bad), (prof_good, prof_bad)
