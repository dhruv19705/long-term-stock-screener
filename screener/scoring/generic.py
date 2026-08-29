from __future__ import annotations

import math
from typing import Dict, List, Optional

import numpy as np

from screener.config_loader import load_sector_weights, load_settings
from screener.models import ScoreResult, StockMetrics
from screener.scoring.adjustments import apply_cyclical_composite_penalty, calibrate_sector_composites
from screener.scoring.factors import (
    percentile_rank,
    soft_score_higher,
    soft_score_lower,
    weighted_mean,
)
from screener.scoring.growth import effective_profit_cagr, effective_revenue_cagr
from screener.scoring.peer_stats import shrink_percentile
from screener.scoring.action_matrix import assign_action
from screener.scoring.hard_gates import evaluate_generic_gates
from screener.scoring.sector_bands import growth_bands, margin_bands, margin_value, metric_bands
from screener.scoring.valuation import evaluate_valuation


def _sector_config(model_sector: str) -> Dict:
    sw = load_sector_weights()
    return sw.get(model_sector) or sw.get("DEFAULT", {})


def _overlay_metric_score(val: Optional[float], spec: dict) -> Optional[float]:
    if val is None or not np.isfinite(val):
        return None
    good = float(spec["good"])
    warn = float(spec["warn"])
    higher = spec.get("higher_better", True)
    if higher:
        if val >= good:
            return 1.0
        if val >= warn:
            return 0.6
        return 0.2
    if val <= good:
        return 1.0
    if val <= warn:
        return 0.6
    return 0.2


def _revenue_acceleration(m: StockMetrics) -> Optional[float]:
    if m.revenue_growth_pct is None or m.revenue_cagr_3y_pct is None:
        return None
    return float(m.revenue_growth_pct) - float(m.revenue_cagr_3y_pct)


def score_generic_group(
    peers: List[StockMetrics],
    model_sector: str,
    sector_focus: str,
) -> Dict[str, ScoreResult]:
    cfg = _sector_config(model_sector)
    weights = dict(cfg.get("weights") or load_sector_weights()["DEFAULT"]["weights"])
    cyclical_sectors = load_sector_weights().get("cyclical_sectors", [])
    overlay_metrics = cfg.get("metrics") or {}

    tickers = [m.ticker for m in peers]
    composites: Dict[str, float] = {}
    results: Dict[str, ScoreResult] = {}

    mom_pctile = percentile_rank(tickers, [m.return_6m_pct for m in peers], higher_better=True)
    dd_pctile = percentile_rank(tickers, [m.max_drawdown_1y_pct for m in peers], higher_better=False)
    roe_pctile = percentile_rank(tickers, [m.roe_pct for m in peers], higher_better=True)
    pe_pctile = percentile_rank(tickers, [m.pe for m in peers], higher_better=False)

    roe_good, roe_bad = metric_bands(model_sector, "roe_pct", 15.0, 6.0)
    roce_good, roce_bad = metric_bands(model_sector, "roce_pct", 15.0, 8.0)
    margin_good, margin_bad = margin_bands(model_sector)
    (rev_good, rev_bad), (prof_good, prof_bad) = growth_bands(model_sector)
    de_good, de_bad = metric_bands(model_sector, "debt_to_equity", 0.6, 1.8)
    ic_good, ic_bad = metric_bands(model_sector, "interest_coverage", 3.0, 1.2)

    for m in peers:
        margin_val = margin_value(m, model_sector)
        quality_parts = {
            "roe": soft_score_higher(m.roe_pct, good=roe_good, bad=roe_bad),
            "roce": soft_score_higher(m.roce_pct, good=roce_good, bad=roce_bad),
            "margin": soft_score_higher(margin_val, good=margin_good, bad=margin_bad),
            "de": soft_score_lower(m.debt_to_equity, good=de_good, bad=de_bad),
            "ic": soft_score_higher(m.interest_coverage, good=ic_good, bad=ic_bad),
            "roe_peer": None if roe_pctile[m.ticker] is None else roe_pctile[m.ticker] / 100.0,
        }
        growth_parts = {
            "rev_cagr": soft_score_higher(effective_revenue_cagr(m), good=rev_good, bad=rev_bad),
            "prof_cagr": soft_score_higher(effective_profit_cagr(m), good=prof_good, bad=prof_bad),
            "margin_trend": soft_score_higher(m.operating_margin_trend_pct, good=1.0, bad=-4.0),
        }
        if model_sector in ("AUTO", "CAPITAL_GOODS"):
            growth_parts["accel"] = soft_score_higher(_revenue_acceleration(m), good=3.0, bad=-3.0)

        ey = None if m.pe in (None, 0) else 100.0 / m.pe
        fcf_good, fcf_bad = metric_bands(model_sector, "free_cash_flow_ttm", 0.0, -1.0)
        value_parts = {
            "pe_peer": None if pe_pctile[m.ticker] is None else pe_pctile[m.ticker] / 100.0,
            "ey": soft_score_higher(ey, good=5.0, bad=1.5),
            "fcf": soft_score_higher(m.fcf_yield_pct, good=3.0, bad=0.0),
        }
        mom = None if mom_pctile[m.ticker] is None else mom_pctile[m.ticker] / 100.0
        if mom is None:
            rs = m.rs_vs_sector_pct if m.rs_vs_sector_pct is not None else m.rs_vs_nifty_pct
            mom = soft_score_higher(rs, good=5.0, bad=-15.0)
        risk_pen = None if dd_pctile[m.ticker] is None else dd_pctile[m.ticker] / 100.0
        if risk_pen is None:
            risk_pen = soft_score_lower(m.downside_deviation, good=0.15, bad=0.5) or 0.5

        cashflow = soft_score_higher(m.fcf_yield_pct, good=4.0, bad=0.0)
        cashflow = cashflow or soft_score_higher(
            1.0 if (m.free_cash_flow_ttm or 0) > 0 else 0.0, good=1.0, bad=0.0
        )
        if model_sector == "ENERGY" and m.free_cash_flow_ttm is not None:
            cashflow = soft_score_higher(m.free_cash_flow_ttm, good=fcf_good, bad=fcf_bad) or cashflow

        overlay_scores: Dict[str, float] = {}
        for metric_name, spec in overlay_metrics.items():
            val = getattr(m, metric_name, None)
            sc = _overlay_metric_score(val, spec)
            if sc is not None:
                w = float(spec.get("weight", 1.0))
                overlay_scores[f"ov_{metric_name}"] = sc * w

        if overlay_scores:
            ov_mean = float(np.mean(list(overlay_scores.values())))
            quality_parts["overlay"] = ov_mean

        parts = {
            "quality": _avg_dict(quality_parts),
            "growth": _avg_dict(growth_parts),
            "value": _avg_dict(value_parts),
            "momentum": mom,
            "risk_penalty": risk_pen,
        }
        if "cashflow" in weights:
            parts["cashflow"] = cashflow

        comp01, used = weighted_mean(parts, weights)
        composite = comp01 * 100.0
        composite = apply_cyclical_composite_penalty(composite, m, model_sector, cyclical_sectors)
        composites[m.ticker] = composite

        vl, _ = evaluate_valuation(m, peers, model_sector, cyclical_sectors)
        fund = _avg_dict({"q": parts["quality"], "g": parts["growth"]}) or 0.0
        hard_fail, rf, margin_distortion = evaluate_generic_gates(m, sector_focus)
        m.margin_distortion = margin_distortion
        dq_flags: List[str] = []
        if margin_distortion:
            dq_flags.append("margin_distortion")

        results[m.ticker] = ScoreResult(
            sector=m.sector,
            sector_focus=sector_focus,
            model_sector=model_sector,
            analysis_depth="standard",
            fundamental_pass=not hard_fail and (fund or 0) >= 0.35,
            fundamental_strength=float(fund or 0),
            composite_score=float(composite),
            valuation_label=vl,
            red_flag=rf,
            hard_gate_fail=hard_fail,
            score_breakdown={k: float(v) for k, v in used.items()},
            confidence=float(m.data_completeness or 0.5),
            peer_count=len(peers),
            margin_distortion=margin_distortion,
            data_quality_flags=dq_flags,
            risk_flags=_risk_flags_generic(m, hard_fail, rf, margin_distortion),
        )

    composites = calibrate_sector_composites(composites)
    comp_pctile = percentile_rank(tickers, [composites[t] for t in tickers], higher_better=True)
    min_peers = int(load_settings().get("min_peers_for_rank", 8))
    for t, r in results.items():
        pr = shrink_percentile(comp_pctile.get(t), len(peers), min_peers)
        r.composite_score = composites[t]
        r.peer_rank = None if pr is None else int(round((100 - pr) / 100 * max(len(peers) - 1, 0))) + 1
        r.composite_percentile = pr
        m = next(x for x in peers if x.ticker == t)
        assign_action(r, m)

    return results


def _avg_dict(parts: Dict[str, Optional[float]]) -> Optional[float]:
    vals = [v for v in parts.values() if v is not None and math.isfinite(v)]
    if not vals:
        return None
    return float(np.mean(vals))


def _risk_flags_generic(
    m: StockMetrics, hard_fail: bool, red_flag: bool, margin_distortion: bool = False
) -> List[str]:
    flags = []
    if hard_fail:
        flags.append("hard_gate_fail")
    if red_flag:
        flags.append("red_flag")
    if margin_distortion:
        flags.append("margin_distortion")
    if m.debt_to_equity is not None and m.debt_to_equity > 2.0:
        flags.append("high_leverage")
    if m.operating_margin_pct is not None and m.operating_margin_pct < 5:
        flags.append("weak_margins")
    return flags
