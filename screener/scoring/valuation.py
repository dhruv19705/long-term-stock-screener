from __future__ import annotations

from typing import List, Optional, Tuple

from screener.models import StockMetrics
from screener.scoring.absolute_valuation import absolute_valuation_label, cyclical_margin_penalty


def evaluate_valuation(
    m: StockMetrics,
    peers: List[StockMetrics],
    model_sector: str,
    cyclical_sectors: Optional[List[str]] = None,
    pb_roe_residual: Optional[float] = None,
) -> Tuple[str, Optional[float]]:
    """Absolute Under/Fair/Over from sector bands in valuation_bands.yaml."""
    del peers, pb_roe_residual  # peers retained for API compatibility; label is absolute
    return absolute_valuation_label(m, model_sector, cyclical_sectors)
