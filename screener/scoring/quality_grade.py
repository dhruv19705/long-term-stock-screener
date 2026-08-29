from __future__ import annotations

from screener.models import ScoreResult, StockMetrics


def compute_quality_score(
    score: ScoreResult,
    metrics: StockMetrics,
) -> float:
    """Absolute quality 0-1 from fundamentals, not peer rank."""
    fund = max(0.0, min(1.0, float(score.fundamental_strength or 0.0)))
    completeness = max(0.0, min(1.0, float(metrics.data_completeness or score.confidence or 0.5)))
    return float(0.85 * fund + 0.15 * completeness)


def quality_grade_from_score(
    quality_score: float,
    red_flag: bool,
    hard_gate_fail: bool,
) -> str:
    if hard_gate_fail:
        return "F"
    if red_flag and quality_score < 0.55:
        return "D"
    if quality_score >= 0.85 and not red_flag:
        return "A"
    if quality_score >= 0.65:
        return "B"
    if quality_score >= 0.45:
        return "C"
    return "D"


def assign_quality_fields(score: ScoreResult, metrics: StockMetrics) -> None:
    q = compute_quality_score(score, metrics)
    score.quality_score = q
    score.quality_grade = quality_grade_from_score(q, score.red_flag, score.hard_gate_fail)
