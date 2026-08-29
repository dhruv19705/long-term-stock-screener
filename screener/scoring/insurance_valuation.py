from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from screener.models import StockMetrics
from screener.scoring.banking_valuation import pb_roe_residual


def valuation_label_from_insurance_residual(
    residual: Optional[float],
    pb: Optional[float],
    peer_median_pb: Optional[float],
) -> Tuple[str, Optional[float]]:
    """Life insurers carry higher P/B; widen Over band vs banks."""
    if residual is not None and np.isfinite(residual):
        if residual < -0.20:
            return "Under", residual
        if residual > 0.65:
            return "Over", residual
        return "Fair", residual
    if pb is not None and peer_median_pb not in (None, 0):
        ratio = pb / peer_median_pb
        if ratio < 0.90:
            return "Under", residual
        if ratio > 1.25:
            return "Over", residual
        return "Fair", residual
    return "Unknown", residual


def insurance_pb_roe_residual(metrics_list: List[StockMetrics]) -> Dict[str, Optional[float]]:
    return pb_roe_residual(metrics_list)
