from __future__ import annotations

from typing import Any, Dict, Optional

from screener.config_loader import load_settings, nifty50_tickers, sector_focus_for_ticker
from screener.models import ScoreResult, StockMetrics
from screener.scoring.quality_grade import assign_quality_fields

ACTION_LADDER = ["SELL", "AVOID", "HOLD", "BUY", "STRONG BUY"]
CYCLICAL_SECTORS = frozenset({"auto", "energy", "metals", "capital_goods"})


def _benchmark_calibration() -> dict:
    import os

    cfg = dict(load_settings().get("benchmark_calibration") or {})
    if os.environ.get("SCREENER_BENCHMARK_CALIBRATION", "").lower() in ("1", "true", "yes"):
        return {"street_overlay": True, "index_anchor": True}
    return cfg


def _action_book() -> Dict[str, Any]:
    return dict(load_settings().get("action_book") or {})


def peer_band_from_percentile(pctile: Optional[float]) -> str:
    p = pctile if pctile is not None else 50.0
    if p >= 70:
        return "Top"
    if p >= 50:
        return "Upper-Mid"
    if p >= 30:
        return "Lower-Mid"
    return "Bottom"


def _cap_tier(market_cap: Optional[float]) -> Optional[str]:
    if market_cap is None:
        return None
    cfg = load_settings().get("cap_tiers") or {}
    mega = float(cfg.get("mega", 2_000_000_000_000))
    large = float(cfg.get("large", 500_000_000_000))
    if market_cap >= mega:
        return "mega"
    if market_cap >= large:
        return "large"
    return None


def _focus(metrics: StockMetrics) -> str:
    focus = sector_focus_for_ticker(metrics.ticker)
    if not focus or focus == "unknown":
        return metrics.sector_focus or "unknown"
    return focus


def _rs_nifty(metrics: StockMetrics) -> Optional[float]:
    return metrics.rs_vs_nifty_pct


def _cyclical_ok_for_buy(metrics: StockMetrics, val_label: str, rs: Optional[float]) -> bool:
    if _focus(metrics) not in CYCLICAL_SECTORS:
        return True
    if val_label == "Under":
        return True
    return rs is not None and rs >= 0


def _apply_large_cap_quality_floor(score: ScoreResult, metrics: StockMetrics) -> None:
    """Lift weak large-cap percentiles for display; never into Top (>=70)."""
    tier = _cap_tier(metrics.market_cap)
    if tier not in ("mega", "large"):
        return
    if score.quality_score >= 0.65 and score.composite_percentile is not None:
        floor_pct = 50.0 if tier == "mega" else 30.0
        floor_pct = min(floor_pct, 69.0)
        score.composite_percentile = max(float(score.composite_percentile), floor_pct)


def _resolve_peer_band(score: ScoreResult, metrics: StockMetrics) -> str:
    band = peer_band_from_percentile(score.composite_percentile)
    if (
        score.quality_grade in ("A", "B")
        and _cap_tier(metrics.market_cap) is not None
        and band == "Bottom"
    ):
        band = "Lower-Mid"
    return band


def _apply_cap_floor(
    action: str,
    metrics: StockMetrics,
    score: ScoreResult,
) -> str:
    """HOLD floor only for Grade A/B Fair large/mega names — never for Over."""
    if action not in ("SELL", "AVOID"):
        return action
    if score.valuation_label != "Fair":
        return action
    if score.quality_grade not in ("A", "B"):
        return action
    if score.hard_gate_fail or score.red_flag:
        return action
    if _cap_tier(metrics.market_cap) is None:
        return action
    return "HOLD"


def _derive_action(
    grade: str,
    band: str,
    val_label: str,
    red_flag: bool,
    hard_fail: bool,
    metrics: StockMetrics,
    profile_id: Optional[str],
    composite_pctile: Optional[float] = None,
) -> str:
    del profile_id, composite_pctile
    book = _action_book()
    sell_rs = float(book.get("sell_rs", -10))
    avoid_rs = float(book.get("avoid_rs", -15))
    sb_fair_rs = float(book.get("strong_buy_fair_rs", 0))
    rs = _rs_nifty(metrics)
    focus = _focus(metrics)

    if hard_fail:
        return "SELL" if val_label == "Over" else "AVOID"

    if val_label == "Over":
        if grade in ("D", "F"):
            return "SELL"
        if rs is not None and rs <= sell_rs:
            return "SELL"
        if red_flag:
            return "SELL"
        if focus == "banking":
            bcfg = book.get("banking") or {}
            roe_min = float(bcfg.get("roe_soft_min", 8.0))
            gnpa_max = float(bcfg.get("gnpa_soft_max", 2.8))
            if metrics.roe_pct is not None and metrics.roe_pct < roe_min:
                return "SELL"
            if metrics.gnpa_pct is not None and metrics.gnpa_pct >= gnpa_max:
                return "SELL"
        if focus == "it":
            icfg = book.get("it") or {}
            margin_min = float(icfg.get("op_margin_soft_min", 12.0))
            if metrics.operating_margin_pct is not None and metrics.operating_margin_pct < margin_min:
                return "SELL"
        if grade == "C":
            return "AVOID"
        if grade == "A" and band in ("Top", "Upper-Mid") and rs is not None and rs > 0:
            return "BUY"

    if val_label == "Fair" and grade in ("D", "F"):
        return "AVOID"
    if red_flag and val_label != "Over":
        return "AVOID"
    if grade in ("C", "D", "F") and rs is not None and rs <= avoid_rs:
        return "AVOID"

    if grade == "A" and not red_flag and not hard_fail and val_label != "Over":
        if val_label == "Under":
            return "STRONG BUY"
        if val_label == "Fair" and (rs is None or rs >= sb_fair_rs):
            return "STRONG BUY"

    if grade in ("A", "B") and not hard_fail:
        if val_label == "Under" and _cyclical_ok_for_buy(metrics, val_label, rs):
            return "BUY"
        if val_label == "Fair":
            if band == "Top" and _cyclical_ok_for_buy(metrics, val_label, rs):
                return "BUY"
            if grade == "A" and rs is not None and rs >= 0 and _cyclical_ok_for_buy(metrics, val_label, rs):
                return "BUY"

    return "HOLD"


def _profile_adjust(
    action: str,
    grade: str,
    band: str,
    val_label: str,
    metrics: StockMetrics,
    profile_id: Optional[str],
) -> str:
    if profile_id == "conservative" and val_label == "Over":
        if action in ("STRONG BUY", "BUY"):
            return "HOLD"
        if action == "HOLD" and band == "Bottom":
            return "AVOID"

    if profile_id == "aggressive" and grade == "A" and band == "Bottom":
        rs = metrics.rs_vs_nifty_pct
        if rs is not None and rs > 0 and action in ("HOLD", "AVOID"):
            return "BUY"

    return action


def _confidence_downgrade(action: str, confidence: float, metrics: StockMetrics) -> str:
    if action not in ACTION_LADDER:
        return action
    idx = ACTION_LADDER.index(action)
    if confidence < 0.35:
        return ACTION_LADDER[max(0, idx - 1)]
    if (metrics.data_completeness or 0) < 0.5 and metrics.roe_pct is None:
        return ACTION_LADDER[max(0, idx - 1)]
    return action


def _annotate_data_quality(score: ScoreResult, metrics: StockMetrics) -> None:
    flags = list(score.data_quality_flags or [])
    if score.margin_distortion or metrics.margin_distortion:
        if "margin_distortion" not in flags:
            flags.append("margin_distortion")
    tier = _cap_tier(metrics.market_cap)
    if (
        score.hard_gate_fail
        and tier in ("mega", "large")
        and score.composite_score > 70
    ):
        if "hard_gate_large_cap" not in flags:
            flags.append("hard_gate_large_cap")
    score.data_quality_flags = flags


def _apply_index_anchor(
    action: str,
    metrics: StockMetrics,
    score: ScoreResult,
) -> str:
    """Nifty 50 index names: Grade A/B mega/large caps should not sit HOLD when fairly ranked."""
    if metrics.ticker not in nifty50_tickers():
        return action
    if score.hard_gate_fail or score.red_flag:
        return action
    if score.quality_grade not in ("A", "B"):
        return action
    if _cap_tier(metrics.market_cap) not in ("mega", "large"):
        return action
    if score.peer_band not in ("Top", "Upper-Mid", "Lower-Mid"):
        return action
    if score.peer_band == "Bottom":
        return action
    if action not in ACTION_LADDER:
        return action
    hold_idx = ACTION_LADDER.index("HOLD")
    buy_idx = ACTION_LADDER.index("BUY")
    if ACTION_LADDER.index(action) >= buy_idx:
        return action
    focus = sector_focus_for_ticker(metrics.ticker)
    if focus in CYCLICAL_SECTORS and score.valuation_label == "Over":
        return action
    if score.valuation_label == "Over" and score.quality_grade == "A":
        return "BUY"
    if score.valuation_label in ("Fair", "Under"):
        return "BUY"
    if ACTION_LADDER.index(action) < hold_idx:
        return "HOLD"
    return action


def assign_action(
    score: ScoreResult,
    metrics: StockMetrics,
    profile_id: Optional[str] = None,
) -> str:
    """Set quality fields and return final action label."""
    assign_quality_fields(score, metrics)
    _apply_large_cap_quality_floor(score, metrics)
    band = _resolve_peer_band(score, metrics)
    score.peer_band = band

    action = _derive_action(
        score.quality_grade,
        band,
        score.valuation_label,
        score.red_flag,
        score.hard_gate_fail,
        metrics,
        profile_id,
        score.composite_percentile,
    )
    action = _profile_adjust(action, score.quality_grade, band, score.valuation_label, metrics, profile_id)
    post_core = _apply_cap_floor(action, metrics, score)

    cal = _benchmark_calibration()
    action = post_core
    if cal.get("index_anchor", False):
        action = _apply_index_anchor(action, metrics, score)
    action = _confidence_downgrade(action, score.confidence, metrics)
    score.raw_recommendation = action

    final = action
    if cal.get("street_overlay", False):
        try:
            from screener.data.street_consensus import apply_street_overlay

            final = apply_street_overlay(action, metrics.ticker, score.quality_grade)
        except Exception:
            final = action

    score.calibration_applied = final != post_core
    score.recommendation = final
    _annotate_data_quality(score, metrics)
    return final
