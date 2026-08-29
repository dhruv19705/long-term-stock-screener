"""Sector-relative momentum and small-peer percentile shrinkage."""

from __future__ import annotations

from statistics import median
from typing import Dict, List, Optional

from screener.models import StockMetrics


def enrich_sector_relative_momentum(metrics: Dict[str, StockMetrics]) -> None:
    """Set rs_vs_sector_pct = 6m return minus sector median 6m return."""
    by_focus: Dict[str, List[StockMetrics]] = {}
    for m in metrics.values():
        by_focus.setdefault(m.sector_focus, []).append(m)

    for group in by_focus.values():
        rets = [m.return_6m_pct for m in group if m.return_6m_pct is not None]
        if not rets:
            continue
        med = float(median(rets))
        for m in group:
            if m.return_6m_pct is not None:
                m.rs_vs_sector_pct = float(m.return_6m_pct) - med


def shrink_percentile(raw: Optional[float], peer_count: int, min_peers: int = 8) -> Optional[float]:
    """Blend toward 50 when peer group is small to reduce ranking noise."""
    if raw is None:
        return None
    if peer_count >= min_peers:
        return raw
    w = peer_count / float(min_peers)
    return 50.0 * (1.0 - w) + raw * w
