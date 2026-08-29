"""Composite adjustments: completeness penalties, peer caps, sector calibration."""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np

from screener.config_loader import load_settings
from screener.models import StockMetrics
from screener.scoring.absolute_valuation import cyclical_margin_penalty


def banking_field_completeness(m: StockMetrics) -> float:
    fields = ["gnpa_pct", "nnpa_pct", "nim_pct", "car_pct", "roe_pct", "roa_pct"]
    ok = sum(1 for f in fields if getattr(m, f, None) is not None)
    return ok / len(fields) if fields else 0.0


def banking_has_core_metrics(m: StockMetrics) -> bool:
    return m.gnpa_pct is not None or m.nim_pct is not None


def apply_composite_completeness_penalty(
    composite: float,
    completeness: float,
    floor: float = 0.65,
) -> float:
    mult = floor + (1.0 - floor) * max(0.0, min(1.0, completeness))
    return float(composite * mult)


def cap_banking_peer_percentile(pct: Optional[float], m: StockMetrics) -> Optional[float]:
    """No Top peer band without GNPA or NIM."""
    if pct is None:
        return None
    if not banking_has_core_metrics(m) and pct >= 70.0:
        return 69.0
    return pct


def calibrate_sector_composites(
    composites: Dict[str, float],
    target_mean: Optional[float] = None,
) -> Dict[str, float]:
    cfg = load_settings().get("sector_calibration") or {}
    if not cfg.get("enabled", True):
        return composites
    if not composites:
        return composites
    target = float(target_mean if target_mean is not None else cfg.get("target_mean", 57.5))
    mean = float(np.mean(list(composites.values())))
    shift = target - mean
    return {t: float(np.clip(v + shift, 0.0, 100.0)) for t, v in composites.items()}


def apply_cyclical_composite_penalty(
    composite: float,
    m: StockMetrics,
    model_sector: str,
    cyclical_sectors: list[str],
) -> float:
    if model_sector not in cyclical_sectors:
        return composite
    penalty = cyclical_margin_penalty(m, model_sector, cyclical_sectors)
    if penalty <= 0:
        return composite
    return float(composite * (1.0 - 0.15 * penalty))


def insurance_min_peers() -> int:
    cfg = load_settings().get("sector_calibration") or {}
    return int(cfg.get("insurance_min_peers", 5))
