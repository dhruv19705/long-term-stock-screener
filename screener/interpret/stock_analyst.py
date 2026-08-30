from __future__ import annotations

from typing import Any, Dict, List

from screener.config_loader import (
    load_banking_risk_questions,
    load_generic_risk_questions,
    load_insurance_risk_questions,
    load_it_risk_questions,
    load_sector_risk_overrides,
)
from screener.interpret import narrative
from screener.interpret.signals import evaluate_signal
from screener.scoring.action_matrix import assign_action
from screener.models import QuestionAnswer, ScoreResult, StockInterpretation, StockMetrics


def _context(m: StockMetrics, score: ScoreResult) -> Dict[str, Any]:
    d = m.to_dict()
    d["valuation_label"] = score.valuation_label
    d["valuation_method"] = getattr(score, "valuation_method", "absolute")
    d["intrinsic_gap_pct"] = getattr(score, "intrinsic_gap_pct", None)
    d["valuation_peer_pctile"] = getattr(score, "valuation_peer_pctile", None)
    d["red_flag"] = score.red_flag
    d["composite_score"] = score.composite_score
    d["data_completeness"] = m.data_completeness
    if m.rs_vs_sector_pct is not None:
        d["rs_vs_nifty_pct"] = m.rs_vs_sector_pct
    peg = m.peg
    if peg is None and m.pe and m.profit_growth_pct and m.profit_growth_pct > 0:
        peg = m.pe / m.profit_growth_pct
    d["peg"] = peg
    return d


def _signal_override_key(sector_focus: str, cyclical: bool) -> str:
    if sector_focus == "banking":
        return "banking"
    if sector_focus == "fmcg":
        return "fmcg"
    if sector_focus == "pharma":
        return "defensive"
    if cyclical or sector_focus in load_sector_risk_overrides().get("cyclical_buckets", []):
        return "cyclical"
    return "default"


def _merge_question_signals(qid: str, sector_focus: str, cyclical: bool, base: dict) -> dict:
    cfg = load_sector_risk_overrides()
    ov = (cfg.get("overrides") or {}).get(qid) or {}
    key = _signal_override_key(sector_focus, cyclical)
    if key in ov:
        return dict(ov[key])
    return dict(base)


def _load_questions(sector_focus: str, analysis_depth: str) -> List[dict]:
    if analysis_depth == "deep" and sector_focus == "banking":
        return list(load_banking_risk_questions()["questions"])
    if analysis_depth == "deep" and sector_focus == "insurance":
        return list(load_insurance_risk_questions()["questions"])
    if analysis_depth == "deep" and sector_focus == "it":
        return list(load_it_risk_questions()["questions"])
    return list(load_generic_risk_questions()["questions"])


def stock_risk_score(answers: List[QuestionAnswer]) -> float:
    if not answers:
        return 50.0
    map_pts = {"good": 0.0, "warn": 1.0, "bad": 2.0, "unknown": 1.0}
    num = 0.0
    den = 0.0
    for a in answers:
        w = a.weight or 1.0
        num += w * map_pts.get(a.signal, 1.0)
        den += w * 2.0
    if den <= 0:
        return 50.0
    return float(100.0 * num / den)


def compute_confidence_v2(
    m: StockMetrics,
    score: ScoreResult,
    stock_risk: float,
) -> float:
    completeness = m.data_completeness or score.confidence or 0.5
    risk_component = 1.0 - (stock_risk / 100.0)
    fund = score.fundamental_strength
    return float(max(0.0, min(1.0, 0.35 * completeness + 0.35 * risk_component + 0.30 * fund)))


def analyze_stock(m: StockMetrics, score: ScoreResult) -> StockInterpretation:
    ctx = _context(m, score)
    qdefs = _load_questions(m.sector_focus, m.analysis_depth)
    answers: List[QuestionAnswer] = []
    for qd in qdefs:
        metrics_snap = {k: ctx.get(k) for k in qd.get("metrics", [])}
        signals = _merge_question_signals(
            qd["id"],
            m.sector_focus,
            m.cyclical,
            qd.get("signals") or {},
        )
        for band in signals.values():
            for k in band.keys():
                metrics_snap.setdefault(k, ctx.get(k))
        sig = evaluate_signal(ctx, signals)
        qa = QuestionAnswer(
            id=qd["id"],
            question=qd["question"],
            dimension=qd["dimension"],
            signal=sig,
            metrics={k: v for k, v in metrics_snap.items() if v is not None},
            peer_rank=(
                f"{score.peer_rank}/{score.peer_count}"
                if score.peer_rank and score.peer_count
                else None
            ),
            weight=float(qd.get("weight", 1.0)),
        )
        qa.answer = narrative.answer_for(qa, metrics_snap)
        answers.append(qa)

    risk = stock_risk_score(answers)
    conf = compute_confidence_v2(m, score, risk)
    score.confidence = conf
    assign_action(score, m)
    bull, bear = narrative.bull_bear(answers)
    return StockInterpretation(
        ticker=m.ticker,
        sector=m.sector,
        sector_focus=m.sector_focus,
        model_sector=m.model_sector,
        analysis_depth=m.analysis_depth,
        recommendation=score.recommendation,
        composite_score=score.composite_score,
        composite_percentile=score.composite_percentile,
        quality_grade=score.quality_grade,
        peer_band=score.peer_band,
        stock_risk_score=risk,
        confidence=conf,
        valuation_label=score.valuation_label,
        headline=narrative.headline(m, score, risk),
        questions=answers,
        bull_case=bull,
        bear_case=bear,
        key_risk=narrative.key_risk(answers, m),
        verdict=narrative.verdict(score, risk),
        score_breakdown=dict(score.score_breakdown),
        peer_rank=score.peer_rank,
        peer_count=score.peer_count,
        red_flag=score.red_flag,
        hard_gate_fail=score.hard_gate_fail,
        risk_flags=list(score.risk_flags),
        data_quality_flags=list(score.data_quality_flags or []),
    )
