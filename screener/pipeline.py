from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd

from screener.config_loader import load_settings, tickers_for_filter
from screener.data.cache import clear_cache
from screener.data.fetcher import fetch_all_metrics
from screener.interpret.engine import interpret_universe, recommend_for_profile
from screener.models import (
    RecommendationResult,
    RiskProfile,
    ScoreResult,
    StockInterpretation,
    StockMetrics,
)
from screener.scoring.composite import score_universe
from screener.scoring.growth import effective_revenue_cagr
from screener.scoring.peer_stats import enrich_sector_relative_momentum

logger = logging.getLogger("screener.pipeline")

OUTPUT_COLUMNS = [
    "stock",
    "sector",
    "sector_focus",
    "model_sector",
    "analysis_depth",
    "pe",
    "pb",
    "roe_pct",
    "revenue_growth_pct",
    "return_1y_pct",
    "composite_score",
    "composite_percentile",
    "fundamental_strength",
    "valuation",
    "confidence",
    "stock_risk_score",
    "recommendation",
    "quality_grade",
    "peer_band",
    "peer_rank",
    "data_source",
]


def _completeness_ratio(m: StockMetrics, fields: List[str]) -> float:
    if not fields:
        return 0.0
    ok = sum(1 for f in fields if getattr(m, f, None) is not None)
    return ok / len(fields)


def _qc(m: StockMetrics) -> Tuple[bool, str]:
    settings = load_settings()
    min_rows = int(settings.get("min_price_history_rows", 50))
    min_comp = float(settings.get("min_completeness", 0.35))
    if m.fetch_failed:
        return False, "fetch failed"
    if m.sector_focus == "unknown":
        return False, "unknown bucket"
    if m.price_history_rows < min_rows:
        return False, f"short history ({m.price_history_rows})"
    if m.pe is None and m.pb is None:
        return False, "missing pe and pb"

    if (
        m.operating_margin_pct is not None
        and m.operating_margin_pct < -20.0
        and m.sector_focus != "banking"
    ):
        if m.sector_focus == "energy":
            large = float(load_settings().get("cap_tiers", {}).get("large", 500_000_000_000))
            if (m.roe_pct or 0) < 8.0 and (m.market_cap or 0) < large:
                return False, f"implausible margin ({m.operating_margin_pct:.0f}%)"
        else:
            return False, f"implausible margin ({m.operating_margin_pct:.0f}%)"

    if m.analysis_depth == "deep" and m.sector_focus == "banking":
        fields = ["pb", "roe_pct", "roa_pct", "return_1y_pct"]
        extra = ["gnpa_pct", "car_pct"]
        cr = _completeness_ratio(m, fields)
        if cr < min_comp:
            return False, f"low completeness {cr:.0%}"
        m.data_completeness = _completeness_ratio(m, fields + extra)
        return True, ""

    if m.analysis_depth == "deep" and m.sector_focus == "it":
        fields = ["pe", "roe_pct", "operating_margin_pct", "return_1y_pct"]
        cr = _completeness_ratio(m, fields)
        if effective_revenue_cagr(m) is not None:
            cr = min(1.0, cr + 0.2)
        if cr < min_comp:
            return False, f"low completeness {cr:.0%}"
        m.data_completeness = cr
        return True, ""

    if m.analysis_depth == "deep" and m.sector_focus == "insurance":
        fields = ["pb", "roe_pct", "return_1y_pct"]
        extra = ["solvency_ratio_pct", "vnb_margin_pct"]
        cr = _completeness_ratio(m, fields)
        if cr < min_comp:
            return False, f"low completeness {cr:.0%}"
        m.data_completeness = _completeness_ratio(m, fields + extra)
        return True, ""

    fields = ["pe", "pb", "roe_pct", "operating_margin_pct", "revenue_growth_pct", "return_1y_pct"]
    cr = _completeness_ratio(m, fields)
    if cr < min_comp:
        return False, f"low completeness {cr:.0%}"
    m.data_completeness = cr
    return True, ""


class ScreenState:
    def __init__(self) -> None:
        self.metrics: Dict[str, StockMetrics] = {}
        self.scores: Dict[str, ScoreResult] = {}
        self.interps: Dict[str, StockInterpretation] = {}
        self.dropped: List[Tuple[str, str]] = []
        self.last_filter: str = "all"

    def run(
        self,
        sector_filter: str = "all",
        max_workers: Optional[int] = None,
        use_cache: bool = True,
        refresh: bool = False,
    ) -> pd.DataFrame:
        if refresh:
            clear_cache()
            use_cache = False
        self.last_filter = sector_filter
        raw = fetch_all_metrics(sector_filter=sector_filter, max_workers=max_workers, use_cache=use_cache)
        self.dropped = []
        valid: Dict[str, StockMetrics] = {}
        for t, m in sorted(raw.items()):
            ok, reason = _qc(m)
            if ok:
                valid[t] = m
            else:
                self.dropped.append((t, reason))
                logger.info("Dropped %s → %s", t, reason)

        self.metrics = valid
        enrich_sector_relative_momentum(valid)
        self.scores = score_universe(valid)
        self.interps = interpret_universe(valid, self.scores)
        return self.to_dataframe()

    def to_dataframe(self) -> pd.DataFrame:
        rows = []
        for t, m in sorted(self.metrics.items()):
            s = self.scores.get(t)
            interp = self.interps.get(t)
            if s is None:
                continue
            rows.append(
                {
                    "stock": t,
                    "sector": m.sector,
                    "sector_focus": m.sector_focus,
                    "model_sector": m.model_sector,
                    "analysis_depth": s.analysis_depth or m.analysis_depth,
                    "pe": m.pe,
                    "pb": m.pb,
                    "roe_pct": m.roe_pct,
                    "revenue_growth_pct": m.revenue_growth_pct,
                    "return_1y_pct": m.return_1y_pct,
                    "composite_score": round(s.composite_score, 2),
                    "composite_percentile": round(s.composite_percentile, 1) if s.composite_percentile is not None else None,
                    "fundamental_strength": round(s.fundamental_strength, 3),
                    "valuation": s.valuation_label,
                    "confidence": round(s.confidence, 3),
                    "stock_risk_score": round(interp.stock_risk_score, 1) if interp else None,
                    "recommendation": s.recommendation,
                    "quality_grade": s.quality_grade,
                    "peer_band": s.peer_band,
                    "peer_rank": s.peer_rank,
                    "data_source": m.data_source,
                }
            )
        if not rows:
            return pd.DataFrame(columns=OUTPUT_COLUMNS)
        df = pd.DataFrame(rows)
        rec_rank = {"STRONG BUY": 5, "BUY": 4, "HOLD": 3, "AVOID": 2, "SELL": 1}
        df["_r"] = df["recommendation"].map(rec_rank).fillna(0)
        df = df.sort_values(["_r", "composite_score", "confidence"], ascending=[False, False, False])
        return df.drop(columns=["_r"]).reset_index(drop=True)

    def recommend(self, profile: RiskProfile) -> RecommendationResult:
        needed = tickers_for_filter(profile.sector_filter)
        if not self.scores or self.last_filter != profile.sector_filter:
            self.run(sector_filter=profile.sector_filter)
        # Filter state to profile sector filter
        filtered_metrics = {t: m for t, m in self.metrics.items() if t in set(needed)}
        filtered_scores = {t: s for t, s in self.scores.items() if t in filtered_metrics}
        filtered_interps = {t: i for t, i in self.interps.items() if t in filtered_metrics}
        return recommend_for_profile(profile, filtered_metrics, filtered_scores, filtered_interps)


STATE = ScreenState()


def run_evaluation(
    max_workers: int = 8,
    sector_filter: str = "all",
    use_cache: bool = True,
    refresh: bool = False,
) -> pd.DataFrame:
    return STATE.run(
        sector_filter=sector_filter,
        max_workers=max_workers,
        use_cache=use_cache,
        refresh=refresh,
    )
