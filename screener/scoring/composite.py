from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, List, Optional

import numpy as np

from screener.config_loader import analysis_depth_for_ticker, load_settings, model_sector_for_ticker, peer_set
from screener.models import ScoreResult, SectorAverages, StockMetrics
from screener.data.banking import banking_data_stale
from screener.data.insurance import insurance_data_stale
from screener.scoring.absolute_valuation import (
    absolute_valuation_label_banking,
    absolute_valuation_label_insurance,
    absolute_valuation_label_it,
)
from screener.scoring.adjustments import (
    apply_composite_completeness_penalty,
    apply_cyclical_composite_penalty,
    banking_field_completeness,
    calibrate_sector_composites,
    cap_banking_peer_percentile,
    insurance_min_peers,
)
from screener.scoring.banking_valuation import pb_roe_residual, valuation_label_from_residual
from screener.scoring.insurance_valuation import insurance_pb_roe_residual
from screener.scoring.factors import (
    median_or_none,
    percentile_rank,
    soft_score_higher,
    soft_score_lower,
    weighted_mean,
)
from screener.scoring.generic import score_generic_group
from screener.scoring.growth import effective_profit_cagr, effective_revenue_cagr
from screener.scoring.peer_stats import shrink_percentile
from screener.scoring.action_matrix import assign_action


def _effective_peg(m: StockMetrics) -> Optional[float]:
    if m.peg is not None and m.peg > 0 and math.isfinite(m.peg):
        return float(m.peg)
    if m.pe is None or m.profit_growth_pct is None or m.profit_growth_pct <= 0:
        return None
    return float(m.pe) / float(m.profit_growth_pct)


from screener.scoring.hard_gates import evaluate_banking_gates, evaluate_insurance_gates, evaluate_it_gates


def _avg_scores(parts: Dict[str, Optional[float]]) -> Optional[float]:
    vals = [v for v in parts.values() if v is not None and math.isfinite(v)]
    if not vals:
        return None
    return float(np.mean(vals))


def _risk_flags_banking(m: StockMetrics, hard_fail: bool, rf: bool) -> List[str]:
    flags = []
    if hard_fail:
        flags.append("hard_gate_fail")
    if rf:
        flags.append("red_flag")
    if m.gnpa_pct is not None and m.gnpa_pct >= 2.5:
        flags.append("elevated_gnpa")
    if banking_data_stale():
        flags.append("stale_banking_curated")
    return flags


def _data_completeness(m: StockMetrics, used_count: int) -> float:
    base = min(1.0, used_count / 4.0)
    if m.data_source == "proxy":
        base *= 0.7
    elif m.data_source in ("curated", "mixed"):
        base *= 0.9
    return float(base)


def _score_banking(peers: List[StockMetrics], weights: Dict[str, float]) -> Dict[str, ScoreResult]:
    residuals = pb_roe_residual(peers)
    med_pb = median_or_none(m.pb for m in peers)
    tickers = [m.ticker for m in peers]
    gnpa_pctile = percentile_rank(tickers, [m.gnpa_pct for m in peers], higher_better=False)
    nim_pctile = percentile_rank(tickers, [m.nim_pct for m in peers], higher_better=True)
    roe_pctile = percentile_rank(tickers, [m.roe_pct for m in peers], higher_better=True)
    mom_pctile = percentile_rank(tickers, [m.return_6m_pct for m in peers], higher_better=True)
    dd_pctile = percentile_rank(tickers, [m.max_drawdown_1y_pct for m in peers], higher_better=False)

    results: Dict[str, ScoreResult] = {}
    composites: Dict[str, float] = {}

    for m in peers:
        aq = _avg_scores(
            {
                "gnpa": soft_score_lower(m.gnpa_pct, good=1.5, bad=3.0),
                "nnpa": soft_score_lower(m.nnpa_pct, good=0.4, bad=1.0),
                "car": soft_score_higher(m.car_pct, good=16.0, bad=12.0),
                "gnpa_peer": None if gnpa_pctile[m.ticker] is None else gnpa_pctile[m.ticker] / 100.0,
            }
        )
        franchise = _avg_scores(
            {
                "nim": soft_score_higher(m.nim_pct, good=3.8, bad=2.2),
                "roa": soft_score_higher(m.roa_pct, good=1.5, bad=0.6),
                "roe": soft_score_higher(m.roe_pct, good=15.0, bad=8.0),
                "nim_peer": None if nim_pctile[m.ticker] is None else nim_pctile[m.ticker] / 100.0,
                "roe_peer": None if roe_pctile[m.ticker] is None else roe_pctile[m.ticker] / 100.0,
            }
        )
        resid = residuals.get(m.ticker)
        if resid is not None:
            val_score = float(np.clip(0.5 - resid * 0.4, 0.0, 1.0))
        elif m.pb is not None and med_pb:
            ratio = m.pb / med_pb
            val_score = float(np.clip((1.15 - ratio) / 0.5, 0.0, 1.0))
        else:
            val_score = None

        vl, _ = valuation_label_from_residual(resid, m.pb, med_pb, m.roe_pct)
        if vl == "Unknown":
            vl, _ = absolute_valuation_label_banking(m)
        mom = None if mom_pctile[m.ticker] is None else mom_pctile[m.ticker] / 100.0
        if mom is None:
            rs = m.rs_vs_sector_pct if m.rs_vs_sector_pct is not None else m.rs_vs_nifty_pct
            mom = soft_score_higher(rs, good=5.0, bad=-15.0)
        risk_pen = None if dd_pctile[m.ticker] is None else dd_pctile[m.ticker] / 100.0
        if risk_pen is None:
            risk_pen = 0.5

        parts = {"asset_quality": aq, "franchise": franchise, "valuation": val_score, "momentum": mom, "risk_penalty": risk_pen}
        comp01, used = weighted_mean(parts, weights)
        composite = comp01 * 100.0
        b_comp = banking_field_completeness(m)
        composite = apply_composite_completeness_penalty(composite, b_comp)
        composites[m.ticker] = composite

        fund = _avg_scores({"aq": aq, "fr": franchise}) or 0.0
        hard_fail, rf = evaluate_banking_gates(m)
        completeness = _data_completeness(m, len(used))

        results[m.ticker] = ScoreResult(
            sector=m.sector,
            sector_focus="banking",
            model_sector="BANKING",
            analysis_depth="deep",
            fundamental_pass=not hard_fail and fund >= 0.35,
            fundamental_strength=float(fund),
            composite_score=float(composite),
            valuation_label=vl,
            red_flag=rf,
            hard_gate_fail=hard_fail,
            score_breakdown={k: float(v) for k, v in used.items()},
            confidence=completeness,
            pb_roe_residual=resid,
            peer_count=len(peers),
            risk_flags=_risk_flags_banking(m, hard_fail, rf),
        )
        m.data_completeness = completeness

    composites = calibrate_sector_composites(composites)
    comp_pctile = percentile_rank(tickers, [composites[t] for t in tickers], higher_better=True)
    min_peers = int(load_settings().get("min_peers_for_rank", 8))
    for t, r in results.items():
        pr = shrink_percentile(comp_pctile.get(t), len(peers), min_peers)
        m = next(x for x in peers if x.ticker == t)
        pr = cap_banking_peer_percentile(pr, m)
        r.composite_score = composites[t]
        r.composite_percentile = pr
        r.peer_rank = None if pr is None else int(round((100 - pr) / 100 * max(len(peers) - 1, 0))) + 1
        assign_action(r, m)
    return results


def _risk_flags_insurance(m: StockMetrics, hard_fail: bool, rf: bool) -> List[str]:
    flags = []
    if hard_fail:
        flags.append("hard_gate_fail")
    if rf:
        flags.append("red_flag")
    if insurance_data_stale():
        flags.append("stale_insurance_curated")
    return flags


def _score_insurance(peers: List[StockMetrics], weights: Dict[str, float]) -> Dict[str, ScoreResult]:
    residuals = insurance_pb_roe_residual(peers)
    med_pb = median_or_none(m.pb for m in peers)
    tickers = [m.ticker for m in peers]
    roe_pctile = percentile_rank(tickers, [m.roe_pct for m in peers], higher_better=True)
    mom_pctile = percentile_rank(tickers, [m.return_6m_pct for m in peers], higher_better=True)
    dd_pctile = percentile_rank(tickers, [m.max_drawdown_1y_pct for m in peers], higher_better=False)

    results: Dict[str, ScoreResult] = {}
    composites: Dict[str, float] = {}

    for m in peers:
        solvency = _avg_scores(
            {
                "solvency": soft_score_higher(m.solvency_ratio_pct, good=180.0, bad=150.0),
                "persistency": soft_score_higher(m.persistency_13m_pct, good=85.0, bad=75.0),
            }
        )
        franchise = _avg_scores(
            {
                "vnb": soft_score_higher(m.vnb_margin_pct, good=25.0, bad=18.0),
                "roe": soft_score_higher(m.roe_pct, good=14.0, bad=8.0),
                "aum": soft_score_higher(m.aum_growth_pct, good=15.0, bad=5.0),
                "pg": soft_score_higher(m.profit_growth_pct, good=12.0, bad=0.0),
                "roe_peer": None if roe_pctile[m.ticker] is None else roe_pctile[m.ticker] / 100.0,
            }
        )
        resid = residuals.get(m.ticker)
        if resid is not None:
            val_score = float(np.clip(0.5 - resid * 0.35, 0.0, 1.0))
        elif m.pb is not None and med_pb:
            ratio = m.pb / med_pb
            val_score = float(np.clip((1.20 - ratio) / 0.6, 0.0, 1.0))
        else:
            val_score = None

        vl, _ = absolute_valuation_label_insurance(m)
        mom = None if mom_pctile[m.ticker] is None else mom_pctile[m.ticker] / 100.0
        if mom is None:
            rs = m.rs_vs_sector_pct if m.rs_vs_sector_pct is not None else m.rs_vs_nifty_pct
            mom = soft_score_higher(rs, good=5.0, bad=-15.0)
        risk_pen = None if dd_pctile[m.ticker] is None else dd_pctile[m.ticker] / 100.0
        if risk_pen is None:
            risk_pen = 0.5

        parts = {
            "solvency_quality": solvency,
            "franchise_growth": franchise,
            "valuation": val_score,
            "momentum": mom,
            "risk_penalty": risk_pen,
        }
        comp01, used = weighted_mean(parts, weights)
        composite = comp01 * 100.0
        composites[m.ticker] = composite

        fund = _avg_scores({"solv": solvency, "fr": franchise}) or 0.0
        hard_fail, rf = evaluate_insurance_gates(m)
        completeness = _data_completeness(m, len(used))

        results[m.ticker] = ScoreResult(
            sector=m.sector,
            sector_focus="insurance",
            model_sector="INSURANCE",
            analysis_depth="deep",
            fundamental_pass=not hard_fail and fund >= 0.35,
            fundamental_strength=float(fund),
            composite_score=float(composite),
            valuation_label=vl,
            red_flag=rf,
            hard_gate_fail=hard_fail,
            score_breakdown={k: float(v) for k, v in used.items()},
            confidence=completeness,
            pb_roe_residual=resid,
            peer_count=len(peers),
            risk_flags=_risk_flags_insurance(m, hard_fail, rf),
        )
        m.data_completeness = completeness

    composites = calibrate_sector_composites(composites)
    use_peer_rank = len(peers) >= insurance_min_peers()
    comp_pctile = (
        percentile_rank(tickers, [composites[t] for t in tickers], higher_better=True)
        if use_peer_rank
        else {t: None for t in tickers}
    )
    min_peers = max(2, int(load_settings().get("min_peers_for_rank", 8)))
    for t, r in results.items():
        pr = None if not use_peer_rank else shrink_percentile(comp_pctile.get(t), len(peers), min_peers)
        r.composite_score = composites[t]
        r.composite_percentile = pr
        r.peer_rank = None if pr is None else int(round((100 - pr) / 100 * max(len(peers) - 1, 0))) + 1
        m = next(x for x in peers if x.ticker == t)
        assign_action(r, m)
    return results


def _score_it(peers: List[StockMetrics], weights: Dict[str, float]) -> Dict[str, ScoreResult]:
    tickers = [m.ticker for m in peers]
    med_pe = median_or_none(m.pe for m in peers)
    pe_pctile = percentile_rank(tickers, [m.pe for m in peers], higher_better=False)
    mom_pctile = percentile_rank(tickers, [m.return_6m_pct for m in peers], higher_better=True)
    dd_pctile = percentile_rank(tickers, [m.max_drawdown_1y_pct for m in peers], higher_better=False)

    results: Dict[str, ScoreResult] = {}
    composites: Dict[str, float] = {}

    for m in peers:
        margin_q = _avg_scores(
            {
                "om": soft_score_higher(m.operating_margin_pct, good=18.0, bad=8.0),
                "trend": soft_score_higher(m.operating_margin_trend_pct, good=1.0, bad=-5.0),
                "roe": soft_score_higher(m.roe_pct, good=22.0, bad=10.0),
            }
        )
        growth = _avg_scores(
            {
                "cagr": soft_score_higher(effective_revenue_cagr(m), good=12.0, bad=3.0),
                "pcagr": soft_score_higher(effective_profit_cagr(m), good=12.0, bad=0.0),
            }
        )
        peg = _effective_peg(m)
        ey = None if m.pe in (None, 0) else 100.0 / m.pe
        val = _avg_scores(
            {
                "peg": soft_score_lower(peg, good=1.0, bad=2.8),
                "pe_peer": None if pe_pctile[m.ticker] is None else pe_pctile[m.ticker] / 100.0,
                "fcf": soft_score_higher(m.fcf_yield_pct, good=4.0, bad=0.0),
                "ey": soft_score_higher(ey, good=5.0, bad=1.5),
            }
        )
        vl, _ = absolute_valuation_label_it(m)

        mom = None if mom_pctile[m.ticker] is None else mom_pctile[m.ticker] / 100.0
        if mom is None:
            rs = m.rs_vs_sector_pct if m.rs_vs_sector_pct is not None else m.rs_vs_nifty_pct
            mom = soft_score_higher(rs, good=5.0, bad=-15.0)
        risk_pen = None if dd_pctile[m.ticker] is None else dd_pctile[m.ticker] / 100.0
        if risk_pen is None:
            risk_pen = 0.5

        w = {
            "margin_quality": weights.get("margin_quality", 0.25),
            "growth": weights.get("growth", 0.30),
            "valuation": weights.get("valuation", 0.25),
            "momentum": weights.get("momentum", 0.10),
            "risk_penalty": weights.get("risk_penalty", 0.10),
        }
        parts = {"margin_quality": margin_q, "growth": growth, "valuation": val, "momentum": mom, "risk_penalty": risk_pen}
        comp01, used = weighted_mean(parts, w)
        composite = comp01 * 100.0
        composites[m.ticker] = composite
        fund = _avg_scores({"mq": margin_q, "g": growth}) or 0.0
        hard_fail, rf = evaluate_it_gates(m)
        completeness = _data_completeness(m, len(used))

        results[m.ticker] = ScoreResult(
            sector=m.sector,
            sector_focus="it",
            model_sector="IT",
            analysis_depth="deep",
            fundamental_pass=not hard_fail and fund >= 0.35,
            fundamental_strength=float(fund),
            composite_score=float(composite),
            valuation_label=vl,
            red_flag=rf,
            hard_gate_fail=hard_fail,
            score_breakdown={k: float(v) for k, v in used.items()},
            confidence=completeness,
            peer_count=len(peers),
            risk_flags=["hard_gate_fail"] if hard_fail else (["red_flag"] if rf else []),
        )
        m.data_completeness = completeness

    composites = calibrate_sector_composites(composites)
    comp_pctile = percentile_rank(tickers, [composites[t] for t in tickers], higher_better=True)
    min_peers = int(load_settings().get("min_peers_for_rank", 8))
    for t, r in results.items():
        pr = shrink_percentile(comp_pctile.get(t), len(peers), min_peers)
        r.composite_score = composites[t]
        r.composite_percentile = pr
        r.peer_rank = None if pr is None else int(round((100 - pr) / 100 * max(len(peers) - 1, 0))) + 1
        m = next(x for x in peers if x.ticker == t)
        assign_action(r, m)
    return results


def sector_averages(metrics: Dict[str, StockMetrics]) -> Dict[str, SectorAverages]:
    by_sector: Dict[str, List[StockMetrics]] = defaultdict(list)
    for m in metrics.values():
        by_sector[m.sector].append(m)
    out: Dict[str, SectorAverages] = {}
    for sec, ms in by_sector.items():
        pe_vals = [m.pe for m in ms if m.pe is not None]
        pb_vals = [m.pb for m in ms if m.pb is not None]
        out[sec] = SectorAverages(
            avg_pe=float(np.mean(pe_vals)) if pe_vals else None,
            avg_pb=float(np.mean(pb_vals)) if pb_vals else None,
            n_stocks_pe=len(pe_vals),
            n_stocks_pb=len(pb_vals),
            median_pe=float(np.median(pe_vals)) if pe_vals else None,
            median_pb=float(np.median(pb_vals)) if pb_vals else None,
        )
    return out


def score_universe(metrics: Dict[str, StockMetrics]) -> Dict[str, ScoreResult]:
    settings = load_settings()
    bw = settings.get("composite_weights", {}).get("banking", {})
    iw = settings.get("composite_weights", {}).get("it", {})
    inw = settings.get("composite_weights", {}).get("insurance", {})

    groups: Dict[str, List[StockMetrics]] = defaultdict(list)
    for m in metrics.values():
        if m.fetch_failed:
            continue
        key, _ = peer_set(m.ticker, metrics)
        groups[key].append(m)

    results: Dict[str, ScoreResult] = {}
    for key, peers in groups.items():
        if not peers:
            continue
        sample = peers[0]
        depth = analysis_depth_for_ticker(sample.ticker)
        focus = sample.sector_focus
        if depth == "deep" and focus == "banking":
            results.update(_score_banking(peers, bw))
        elif depth == "deep" and focus == "insurance":
            results.update(_score_insurance(peers, inw))
        elif depth == "deep" and focus == "it":
            results.update(_score_it(peers, iw))
        else:
            model = model_sector_for_ticker(sample.ticker)
            results.update(score_generic_group(peers, model, focus))

    return results
