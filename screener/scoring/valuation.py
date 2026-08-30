from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from screener.models import StockMetrics
from screener.scoring.absolute_valuation import (
    absolute_valuation_label,
    cyclical_margin_penalty,
)
from screener.scoring.fcff_valuation import (
    combine_hybrid_votes,
    fcff_intrinsic_vote,
    peer_relative_votes,
)


@dataclass
class ValuationResult:
    label: str
    ref: Optional[float] = None
    valuation_method: str = "absolute"
    intrinsic_gap_pct: Optional[float] = None
    valuation_peer_pctile: Optional[float] = None


def evaluate_valuation(
    m: StockMetrics,
    peers: List[StockMetrics],
    model_sector: str,
    cyclical_sectors: Optional[List[str]] = None,
    pb_roe_residual: Optional[float] = None,
) -> ValuationResult:
    """Hybrid valuation: FCFF proxy + peer-relative + absolute bands fallback."""
    del pb_roe_residual
    cyclical_sectors = cyclical_sectors or []
    votes: List[str] = []
    intrinsic_gap: Optional[float] = None
    peer_pctile: Optional[float] = None
    method_parts: List[str] = []

    peer_fcf = [p.fcf_yield_pct for p in peers]
    fcff_vote, intrinsic_gap = fcff_intrinsic_vote(m, peer_fcf)
    if fcff_vote:
        votes.append(fcff_vote)
        method_parts.append("fcff")

    peer_votes, peer_pctile = peer_relative_votes(m, peers)
    if peer_votes:
        votes.extend(peer_votes)
        method_parts.append("peer")

    abs_label, ref = absolute_valuation_label(m, model_sector, cyclical_sectors)
    if abs_label != "Unknown":
        votes.append(abs_label)
        method_parts.append("absolute")

    if votes:
        label = combine_hybrid_votes(votes)
        method = "+".join(method_parts) if method_parts else "hybrid"
    else:
        label = abs_label
        method = "fallback"

    cyc_pen = cyclical_margin_penalty(m, model_sector, cyclical_sectors)
    if label == "Under" and cyc_pen >= 0.4:
        label = "Fair"

    return ValuationResult(
        label=label,
        ref=ref,
        valuation_method=method,
        intrinsic_gap_pct=intrinsic_gap,
        valuation_peer_pctile=peer_pctile,
    )
