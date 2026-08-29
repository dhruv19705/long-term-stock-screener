"""Centralized hard-gate and red-flag evaluation with sector overrides."""

from __future__ import annotations

from functools import lru_cache
from typing import Tuple

from screener.config_loader import load_settings
from screener.models import StockMetrics


@lru_cache(maxsize=1)
def _load_hard_gates() -> dict:
    from screener.config_loader import load_hard_gates

    return load_hard_gates()


def _de_limits(sector_focus: str) -> Tuple[float, float]:
    cfg = _load_hard_gates()
    sectors = cfg.get("sectors") or {}
    if sector_focus in sectors and "debt_to_equity" in sectors[sector_focus]:
        spec = sectors[sector_focus]["debt_to_equity"]
        return float(spec.get("hard", 3.0)), float(spec.get("red", 2.5))
    from screener.config_loader import load_debt_adjustments

    adj = load_debt_adjustments()
    sector_limits = (adj.get("sector_de_limits") or {}).get(sector_focus)
    if sector_limits:
        return float(sector_limits.get("hard", 3.0)), float(sector_limits.get("red", 2.5))
    default = (adj.get("sector_de_limits") or {}).get("default") or {}
    return float(default.get("hard", 3.0)), float(default.get("red", 2.5))


def _large_cap_threshold() -> float:
    return float(load_settings().get("cap_tiers", {}).get("large", 500_000_000_000))


def _margin_distortion_applies(m: StockMetrics, sector_focus: str) -> bool:
    if sector_focus != "energy":
        return False
    cfg = (_load_hard_gates().get("sectors") or {}).get("energy", {})
    md = cfg.get("margin_distortion") or {}
    if not md.get("enabled"):
        return False
    if m.operating_margin_pct is None or m.operating_margin_pct >= float(md.get("op_margin_hard_min", -2.0)):
        return False
    min_roe = float(md.get("min_roe_pct", 8.0))
    min_cap = float(md.get("min_market_cap", _large_cap_threshold()))
    if m.roe_pct is not None and m.roe_pct >= min_roe:
        return True
    if m.market_cap is not None and m.market_cap >= min_cap:
        return True
    if md.get("min_fcf_positive") and (m.free_cash_flow_ttm or 0) > 0:
        return True
    return False


def evaluate_generic_gates(m: StockMetrics, sector_focus: str = "") -> Tuple[bool, bool, bool]:
    """
    Returns (hard_gate_fail, red_flag, margin_distortion).
    margin_distortion=True when energy margin hard gate is suppressed.
    """
    defaults = _load_hard_gates().get("defaults") or {}
    sector_cfg = (_load_hard_gates().get("sectors") or {}).get(sector_focus) or {}

    roe_hard = float(defaults.get("roe_hard_min", -5.0))
    roe_red = float(defaults.get("roe_red_min", 0.0))
    margin_hard = float(sector_cfg.get("op_margin_hard_min", defaults.get("op_margin_hard_min", -2.0)))
    margin_red = float(defaults.get("op_margin_red_min", 0.0))
    ic_hard = float(defaults.get("interest_coverage_hard_min", 0.8))

    de_hard, de_red = _de_limits(sector_focus)
    margin_distortion = _margin_distortion_applies(m, sector_focus)

    hard_fail = False
    red_flag = False

    if m.roe_pct is not None and m.roe_pct < roe_hard:
        hard_fail = True
    if m.operating_margin_pct is not None and m.operating_margin_pct < margin_hard:
        if margin_distortion:
            pass
        else:
            hard_fail = True
    if m.debt_to_equity is not None and m.debt_to_equity > de_hard:
        hard_fail = True
    if m.interest_coverage is not None and m.interest_coverage < ic_hard:
        hard_fail = True

    if m.roe_pct is not None and m.roe_pct < roe_red:
        red_flag = True
    if m.operating_margin_pct is not None and m.operating_margin_pct < margin_red:
        if not margin_distortion:
            red_flag = True
    if m.debt_to_equity is not None and m.debt_to_equity > de_red:
        red_flag = True

    return hard_fail, red_flag, margin_distortion


def evaluate_banking_gates(m: StockMetrics) -> Tuple[bool, bool]:
    cfg = (_load_hard_gates().get("sectors") or {}).get("banking") or {}
    hard_fail = False
    if m.gnpa_pct is not None and m.gnpa_pct >= float(cfg.get("gnpa_hard", 3.5)):
        hard_fail = True
    if m.nnpa_pct is not None and m.nnpa_pct >= float(cfg.get("nnpa_hard", 1.2)):
        hard_fail = True
    if m.car_pct is not None and m.car_pct < float(cfg.get("car_hard_min", 12.0)):
        hard_fail = True
    red_flag = hard_fail
    if m.roe_pct is not None and m.roe_pct < 0:
        red_flag = True
    return hard_fail, red_flag


def evaluate_it_gates(m: StockMetrics) -> Tuple[bool, bool]:
    cfg = (_load_hard_gates().get("sectors") or {}).get("it") or {}
    hard_fail = False
    margin_hard = float(cfg.get("op_margin_hard_min", 0.0))
    de_hard = float(cfg.get("debt_to_equity_hard", 2.5))
    de_red = float(cfg.get("debt_to_equity_red", 2.0))
    if m.operating_margin_pct is not None and m.operating_margin_pct < margin_hard:
        hard_fail = True
    if m.roe_pct is not None and m.roe_pct < 0:
        hard_fail = True
    if m.debt_to_equity is not None and m.debt_to_equity > de_hard:
        hard_fail = True
    red_flag = m.roe_pct is not None and m.roe_pct < 0
    if m.operating_margin_pct is not None and m.operating_margin_pct < 0:
        red_flag = True
    if m.debt_to_equity is not None and m.debt_to_equity > de_red:
        red_flag = True
    return hard_fail, red_flag


def evaluate_insurance_gates(m: StockMetrics) -> Tuple[bool, bool]:
    cfg = (_load_hard_gates().get("sectors") or {}).get("insurance") or {}
    hard_fail = False
    if m.solvency_ratio_pct is not None and m.solvency_ratio_pct < float(cfg.get("solvency_hard_min", 150.0)):
        hard_fail = True
    if m.persistency_13m_pct is not None and m.persistency_13m_pct < float(cfg.get("persistency_hard_min", 75.0)):
        hard_fail = True
    red_flag = hard_fail
    if m.roe_pct is not None and m.roe_pct < 5.0:
        red_flag = True
    return hard_fail, red_flag
