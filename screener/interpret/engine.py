from __future__ import annotations

from collections import defaultdict
from typing import Dict, Optional

from screener.interpret.risk_matcher import rank_for_profile
from screener.interpret.stock_analyst import analyze_stock
from screener.models import (
    RecommendationResult,
    RiskProfile,
    ScoreResult,
    StockInterpretation,
    StockMetrics,
)


def interpret_stock(m: StockMetrics, score: ScoreResult) -> StockInterpretation:
    return analyze_stock(m, score)


def interpret_universe(
    metrics: Dict[str, StockMetrics],
    scores: Dict[str, ScoreResult],
) -> Dict[str, StockInterpretation]:
    out: Dict[str, StockInterpretation] = {}
    for t, m in metrics.items():
        if t not in scores:
            continue
        out[t] = analyze_stock(m, scores[t])
    return out


def recommend_for_profile(
    profile: RiskProfile,
    metrics: Dict[str, StockMetrics],
    scores: Dict[str, ScoreResult],
    interps: Optional[Dict[str, StockInterpretation]] = None,
) -> RecommendationResult:
    if interps is None:
        interps = interpret_universe(metrics, scores)
    picks, avoid = rank_for_profile(profile, interps, metrics, scores=scores)

    by_sector: Dict[str, list] = defaultdict(list)
    for p in picks:
        by_sector[p.sector_focus].append(p)

    sectors = len(by_sector)
    summary = (
        f"{len(picks)} picks for {profile.label} across {sectors} sector"
        f"{'s' if sectors != 1 else ''}; "
        f"{len(avoid)} names excluded for risk, valuation, or profile fit."
    )

    return RecommendationResult(
        risk_profile=profile,
        picks=picks,
        avoid=avoid,
        summary=summary,
        picks_by_sector=dict(by_sector),
    )
