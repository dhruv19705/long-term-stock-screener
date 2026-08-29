from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from screener.config_loader import is_cyclical_ticker, load_risk_profile_matrix
from screener.models import FitResult, RiskProfile, StockInterpretation, StockMetrics
from screener.scoring.quality_grade import compute_quality_score


def _fit_label(score: float, labels: List[dict]) -> str:
    for row in sorted(labels, key=lambda x: -x["min"]):
        if score >= row["min"]:
            return row["label"]
    return "Poor"


def _bad_dimensions(interp: StockInterpretation, dims: List[str]) -> bool:
    return any(q.signal == "bad" and q.dimension in dims for q in interp.questions)


def _risk_alignment(
    interp: StockInterpretation,
    profile: RiskProfile,
    metrics: StockMetrics,
) -> float:
    score = 100.0
    if interp.stock_risk_score > profile.max_stock_risk:
        excess = interp.stock_risk_score - profile.max_stock_risk
        score -= min(40.0, excess * 0.8)
    if metrics.beta is not None and metrics.beta > profile.max_beta:
        score -= min(20.0, (metrics.beta - profile.max_beta) * 15.0)
    if profile.needs_liquidity and metrics.ann_volatility is not None and metrics.ann_volatility > 0.45:
        score -= 15.0
    return max(0.0, min(100.0, score))


def _valuation_fit(valuation_label: str, profile_id: str) -> float:
    if valuation_label == "Under":
        return 100.0
    if valuation_label == "Fair":
        return 70.0
    if valuation_label == "Over":
        return 30.0 if profile_id == "conservative" else 40.0
    return 50.0


def _profile_bonus(
    interp: StockInterpretation,
    profile: RiskProfile,
    metrics: StockMetrics,
    bonuses: dict,
) -> float:
    bonus = 0.0
    if interp.analysis_depth == "deep" and "deep_sector_fit" in bonuses:
        bonus += float(bonuses.get("deep_sector_fit", bonuses.get("specialized_sector_fit", 0))) * 5.0

    if profile.id == "conservative" and interp.sector_focus in ("fmcg", "pharma"):
        bonus += 8.0
    if profile.id == "growth" and (metrics.revenue_growth_pct or 0) > 10:
        bonus += float(bonuses.get("strong_growth", 0)) * 0.5

    if "low_drawdown" in bonuses:
        dd = metrics.max_drawdown_1y_pct
        if dd is not None and dd > -15.0:
            bonus += float(bonuses["low_drawdown"]) * 5.0

    rs = metrics.rs_vs_sector_pct if metrics.rs_vs_sector_pct is not None else metrics.rs_vs_nifty_pct
    if rs is not None and rs > 0 and "strong_momentum" in bonuses:
        bonus += float(bonuses["strong_momentum"]) * 0.5

    return min(100.0, bonus)


def _compute_fit_score(
    interp: StockInterpretation,
    profile: RiskProfile,
    metrics: StockMetrics,
    score_result_quality: float,
    bonuses: dict,
) -> float:
    risk = _risk_alignment(interp, profile, metrics)
    quality_norm = max(0.0, min(100.0, score_result_quality * 100.0))
    val_fit = _valuation_fit(interp.valuation_label, profile.id)
    prof_b = _profile_bonus(interp, profile, metrics, bonuses)
    fit = (
        0.27 * risk
        + 0.25 * quality_norm
        + 0.18 * val_fit
        + 0.10 * prof_b
        + 0.20 * max(0.0, min(100.0, float(interp.composite_score)))
    )
    return max(0.0, min(100.0, fit))


def _sector_floor_quotas(matcher_cfg: dict) -> Dict[str, int]:
    """Minimum picks per sector when diversifying; supports legacy deep_sector_min key."""
    quotas = matcher_cfg.get("sector_floor_quotas") or matcher_cfg.get("deep_sector_min") or {}
    return dict(quotas)


def _positive_reasons(
    interp: StockInterpretation,
    profile: RiskProfile,
    metrics: StockMetrics,
    quality_score: float,
    bonuses: dict,
) -> List[str]:
    positives: List[str] = []
    grade = interp.quality_grade or "C"
    if grade in ("A", "B"):
        positives.append("Strong fundamental profile")
    if interp.valuation_label == "Under":
        positives.append("Undervalued vs absolute bands")
    if interp.stock_risk_score <= profile.max_stock_risk * 0.85:
        positives.append(f"Stock risk {interp.stock_risk_score:.0f} within your {profile.max_stock_risk:.0f} limit")
    if interp.composite_score >= 70:
        positives.append(f"High composite score ({interp.composite_score:.0f}/100)")
    if profile.id == "growth" and (metrics.revenue_growth_pct or 0) > 10:
        positives.append("Revenue growth supports growth profile")
    if interp.recommendation in ("STRONG BUY", "BUY"):
        positives.append(f"Model rating: {interp.recommendation}")
    if quality_score >= 0.75:
        positives.append("Solid fundamental quality score")
    if not positives and interp.valuation_label == "Fair":
        positives.append("Fair valuation with acceptable risk profile")
    return positives[:3]


def _negative_reasons(
    profile: RiskProfile,
    interp: StockInterpretation,
    metrics: StockMetrics,
    cfg: dict,
    penalties: dict,
    exclude: bool,
) -> List[str]:
    negatives: List[str] = []
    if interp.stock_risk_score > profile.max_stock_risk:
        pen = float(penalties.get("stock_risk_over_max", 20))
        negatives.append(
            f"Stock risk {interp.stock_risk_score:.0f} > max {profile.max_stock_risk:.0f} (−{pen:.0f})"
        )
    excl_val = cfg.get("exclude_valuation") or []
    if interp.valuation_label in excl_val:
        pen = float(penalties.get("valuation_over", 25))
        negatives.append(f"Valuation {interp.valuation_label} excluded (−{pen:.0f})")
    if _bad_dimensions(interp, ["leverage_risk", "credit_risk", "solvency_risk"]):
        pen = float(penalties.get("bad_leverage", penalties.get("any_bad_credit_or_solvency", 25)))
        negatives.append(f"Leverage/credit concern (−{pen:.0f})")
    if _bad_dimensions(interp, ["market_risk"]):
        pen = float(penalties.get("bad_market_risk", 15))
        negatives.append(f"Momentum/tail risk (−{pen:.0f})")
    if interp.red_flag or metrics.fetch_failed:
        pen = float(penalties.get("red_flag", 35))
        negatives.append(f"Red flag (−{pen:.0f})")
    if interp.hard_gate_fail:
        negatives.append("Hard risk gate failed")
    if not profile.cyclical_ok and is_cyclical_ticker(metrics.ticker):
        pen = float(penalties.get("cyclical_sector", 20))
        negatives.append(f"Cyclical sector not preferred (−{pen:.0f})")
    if metrics.beta is not None and metrics.beta > profile.max_beta:
        pen = float(penalties.get("high_beta", 10))
        negatives.append(f"Beta {metrics.beta:.2f} > {profile.max_beta} (−{pen:.0f})")
    if profile.needs_liquidity and metrics.ann_volatility is not None and metrics.ann_volatility > 0.45:
        negatives.append("High volatility for liquidity need (−15)")
    return negatives[:2] if not exclude else negatives


def match_stock(
    profile: RiskProfile,
    interp: StockInterpretation,
    metrics: StockMetrics,
    quality_score: float = 0.5,
) -> FitResult:
    matrix = load_risk_profile_matrix()
    cfg = matrix["profiles"].get(profile.id) or matrix["profiles"]["moderate"]
    exclude = False
    penalties = cfg.get("penalties") or {}
    bonuses = cfg.get("bonuses") or {}

    if interp.stock_risk_score > profile.max_stock_risk and profile.id == "conservative":
        exclude = True

    excl_val = cfg.get("exclude_valuation") or []
    if interp.valuation_label in excl_val:
        exclude = True

    if _bad_dimensions(interp, ["leverage_risk", "credit_risk", "solvency_risk"]) and cfg.get("require_hard_gates"):
        exclude = True

    if (interp.red_flag or metrics.fetch_failed) and cfg.get("require_hard_gates"):
        exclude = True

    if interp.hard_gate_fail:
        exclude = True

    if not profile.cyclical_ok and is_cyclical_ticker(metrics.ticker) and profile.id == "conservative":
        exclude = True

    if metrics.beta is not None and metrics.beta > profile.max_beta and profile.id == "conservative":
        exclude = True

    positives = _positive_reasons(interp, profile, metrics, quality_score, bonuses)
    negatives = _negative_reasons(profile, interp, metrics, cfg, penalties, exclude)
    reasons = positives + negatives

    score = _compute_fit_score(interp, profile, metrics, quality_score, bonuses)
    label = _fit_label(score, matrix.get("fit_labels") or [])
    if exclude:
        label = "Poor"

    action = interp.recommendation
    return FitResult(
        ticker=interp.ticker,
        fit_score=score,
        fit_label=label,
        exclude=exclude,
        reasons=reasons,
        recommendation=action,
        action_label=action,
        headline=interp.headline,
        composite_score=interp.composite_score,
        stock_risk_score=interp.stock_risk_score,
        quality_grade=interp.quality_grade,
        peer_percentile=interp.composite_percentile,
        peer_band=interp.peer_band,
        sector_focus=interp.sector_focus,
        analysis_depth=interp.analysis_depth,
        data_quality_flags=list(getattr(interp, "data_quality_flags", []) or []),
    )


def diversify_picks(
    picks: List[FitResult],
    profile: RiskProfile,
) -> List[FitResult]:
    matrix = load_risk_profile_matrix()
    matcher_cfg = matrix.get("matcher") or {}
    top_n_total = int(matcher_cfg.get("top_n_total", 20))
    top_n_per = int(matcher_cfg.get("top_n_per_sector", 3))
    min_fit = float(matcher_cfg.get("min_fit_score", 45))
    floor_quotas = _sector_floor_quotas(matcher_cfg)

    eligible = [p for p in picks if p.fit_score >= min_fit]
    if not profile.diversify_sectors:
        return eligible[:top_n_total]

    by_sector: Dict[str, List[FitResult]] = defaultdict(list)
    for p in eligible:
        by_sector[p.sector_focus].append(p)

    diversified: List[FitResult] = []
    used: set[str] = set()

    for sector, min_n in sorted(floor_quotas.items()):
        sector_picks = sorted(by_sector.get(sector, []), key=lambda x: -x.fit_score)[:min_n]
        for p in sector_picks:
            if p.ticker not in used:
                diversified.append(p)
                used.add(p.ticker)

    for sector in sorted(by_sector.keys()):
        sector_picks = sorted(by_sector[sector], key=lambda x: -x.fit_score)
        taken = 0
        for p in sector_picks:
            if p.ticker in used:
                continue
            if taken >= top_n_per:
                break
            diversified.append(p)
            used.add(p.ticker)
            taken += 1

    diversified.sort(key=lambda x: (-x.fit_score, -x.composite_score))
    return diversified[:top_n_total]


def rank_for_profile(
    profile: RiskProfile,
    interps: Dict[str, StockInterpretation],
    metrics: Dict[str, StockMetrics],
    scores: Dict[str, object] | None = None,
) -> Tuple[List[FitResult], List[FitResult]]:
    from screener.models import ScoreResult

    fits = []
    for t, interp in interps.items():
        m = metrics.get(t)
        if m is None or m.fetch_failed:
            continue
        q = 0.5
        if scores and t in scores:
            sr = scores[t]
            if isinstance(sr, ScoreResult):
                q = compute_quality_score(sr, m)
        fits.append(match_stock(profile, interp, m, quality_score=q))

    picks = [f for f in fits if not f.exclude]
    avoid = [f for f in fits if f.exclude]
    picks.sort(key=lambda x: (-x.fit_score, -x.composite_score))
    avoid.sort(key=lambda x: (x.fit_score, x.composite_score))
    picks = diversify_picks(picks, profile)
    return picks, avoid
