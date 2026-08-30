from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from screener.models import StockMetrics
from screener.scoring.factors import percentile_rank


def _median(values: List[Optional[float]]) -> Optional[float]:
    valid = [float(v) for v in values if v is not None and np.isfinite(v)]
    if not valid:
        return None
    return float(np.median(valid))


def fcff_intrinsic_vote(m: StockMetrics, peer_fcf_yields: List[Optional[float]]) -> Tuple[Optional[str], Optional[float]]:
    """
    Simplified FCFF margin-of-safety: compare FCF yield to sector median.
    Returns (Under/Fair/Over vote, intrinsic_gap_pct).
    intrinsic_gap_pct > 0 means cheaper than peers (positive margin of safety).
    """
    fcf_y = m.fcf_yield_pct
    if fcf_y is None or not np.isfinite(fcf_y):
        return None, None

    med = _median(peer_fcf_yields)
    if med is None or med <= 0:
        if fcf_y >= 4.0:
            return "Under", fcf_y - 4.0
        if fcf_y >= 2.0:
            return "Fair", fcf_y - 2.0
        return "Over", fcf_y - 2.0

    gap = float(fcf_y) - float(med)
    de = m.debt_to_equity or 0.0
    if de > 2.0:
        gap -= 0.5
    if (m.free_cash_flow_ttm or 0) <= 0:
        return "Over", gap

    if gap >= 1.5:
        return "Under", gap
    if gap >= -0.5:
        return "Fair", gap
    return "Over", gap


def peer_relative_votes(
    m: StockMetrics,
    peers: List[StockMetrics],
) -> Tuple[List[str], Optional[float]]:
    """Sector-relative PE, EV/EBITDA, FCF yield percentile votes."""
    tickers = [p.ticker for p in peers]
    pe_pct = percentile_rank(tickers, [p.pe for p in peers], higher_better=False)
    ev_pct = percentile_rank(tickers, [p.ev_to_ebitda for p in peers], higher_better=False)
    fcf_pct = percentile_rank(tickers, [p.fcf_yield_pct for p in peers], higher_better=True)

    votes: List[str] = []
    ref_pctile: Optional[float] = None

    for pct_map in (pe_pct, ev_pct, fcf_pct):
        pct = pct_map.get(m.ticker)
        if pct is None:
            continue
        ref_pctile = pct if ref_pctile is None else (ref_pctile + pct) / 2.0
        if pct >= 70:
            votes.append("Under")
        elif pct >= 30:
            votes.append("Fair")
        else:
            votes.append("Over")

    return votes, ref_pctile


def combine_hybrid_votes(votes: List[str]) -> str:
    if not votes:
        return "Unknown"
    under = votes.count("Under")
    over = votes.count("Over")
    n = len(votes)
    majority = n // 2 + (1 if n % 2 else 0)
    if under > over and under >= majority:
        return "Under"
    if over > under and over >= majority:
        return "Over"
    if under == over and under > 0:
        return "Fair"
    if len(set(votes)) == 1:
        return votes[0]
    return "Fair"
