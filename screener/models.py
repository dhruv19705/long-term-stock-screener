from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StockMetrics:
    ticker: str
    sector: str  # yfinance / display label
    sector_focus: str = "unknown"  # bucket id: banking, it, fmcg, ...
    model_sector: str = "UNKNOWN"
    analysis_depth: str = "standard"  # deep | standard
    bank_cohort: Optional[str] = None  # private | psu
    cyclical: bool = False

    pe: Optional[float] = None
    pb: Optional[float] = None
    peg: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    market_cap: Optional[float] = None

    company_name: Optional[str] = None
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    day_open: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    volume: Optional[float] = None
    avg_volume: Optional[float] = None

    roe_pct: Optional[float] = None
    roa_pct: Optional[float] = None
    profit_margin_pct: Optional[float] = None
    operating_margin_pct: Optional[float] = None
    ebitda_margin_pct: Optional[float] = None
    debt_to_equity: Optional[float] = None
    interest_coverage: Optional[float] = None

    profit_growth_pct: Optional[float] = None
    revenue_growth_pct: Optional[float] = None
    return_1m_pct: Optional[float] = None
    return_3m_pct: Optional[float] = None
    return_6m_pct: Optional[float] = None
    return_1y_pct: Optional[float] = None

    pe_hist_low: Optional[float] = None
    pe_hist_high: Optional[float] = None
    pe_hist_mean: Optional[float] = None

    gnpa_pct: Optional[float] = None
    nnpa_pct: Optional[float] = None
    nim_pct: Optional[float] = None
    car_pct: Optional[float] = None

    solvency_ratio_pct: Optional[float] = None
    vnb_margin_pct: Optional[float] = None
    persistency_13m_pct: Optional[float] = None
    aum_growth_pct: Optional[float] = None

    asset_turnover: Optional[float] = None
    roce_pct: Optional[float] = None
    revenue_cagr_3y_pct: Optional[float] = None
    profit_cagr_3y_pct: Optional[float] = None
    operating_margin_trend_pct: Optional[float] = None
    credit_growth_pct: Optional[float] = None
    free_cash_flow_ttm: Optional[float] = None
    dividend_yield_pct: Optional[float] = None
    fcf_yield_pct: Optional[float] = None

    ann_volatility: Optional[float] = None
    beta: Optional[float] = None
    downside_deviation: Optional[float] = None
    max_drawdown_1y_pct: Optional[float] = None
    rs_vs_nifty_pct: Optional[float] = None
    rs_vs_sector_pct: Optional[float] = None

    price_history_rows: int = 0
    fetch_failed: bool = False
    data_source: str = "yfinance"
    banking_data_source: Optional[str] = None
    data_completeness: float = 0.0
    margin_distortion: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SectorAverages:
    avg_pe: Optional[float]
    avg_pb: Optional[float] = None
    n_stocks_pe: int = 0
    n_stocks_pb: int = 0
    median_pe: Optional[float] = None
    median_pb: Optional[float] = None


@dataclass
class ScoreResult:
    sector: str
    sector_focus: str
    model_sector: str = "UNKNOWN"
    analysis_depth: str = "standard"
    fundamental_pass: bool = False
    fundamental_strength: float = 0.0
    composite_score: float = 0.0
    composite_percentile: Optional[float] = None
    valuation_label: str = "Unknown"
    red_flag: bool = False
    hard_gate_fail: bool = False
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    recommendation: str = "HOLD"
    quality_score: float = 0.0
    quality_grade: str = "C"
    peer_band: str = "Lower-Mid"
    pb_roe_residual: Optional[float] = None
    peer_rank: Optional[int] = None
    peer_count: Optional[int] = None
    risk_flags: List[str] = field(default_factory=list)
    margin_distortion: bool = False
    data_quality_flags: List[str] = field(default_factory=list)
    valuation_method: str = "absolute"
    intrinsic_gap_pct: Optional[float] = None
    valuation_peer_pctile: Optional[float] = None

    @property
    def action_label(self) -> str:
        return self.recommendation


@dataclass
class QuestionAnswer:
    id: str
    question: str
    dimension: str
    signal: str
    metrics: Dict[str, Any]
    peer_rank: Optional[str] = None
    answer: str = ""
    weight: float = 1.0


@dataclass
class StockInterpretation:
    ticker: str
    sector: str
    sector_focus: str
    model_sector: str = "UNKNOWN"
    analysis_depth: str = "standard"
    recommendation: str = "HOLD"
    composite_score: float = 0.0
    composite_percentile: Optional[float] = None
    quality_grade: str = "C"
    peer_band: str = "Lower-Mid"
    stock_risk_score: float = 50.0
    confidence: float = 0.0
    valuation_label: str = "Unknown"
    headline: str = ""
    questions: List[QuestionAnswer] = field(default_factory=list)
    bull_case: List[str] = field(default_factory=list)
    bear_case: List[str] = field(default_factory=list)
    key_risk: str = ""
    verdict: str = ""
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    peer_rank: Optional[int] = None
    peer_count: Optional[int] = None
    red_flag: bool = False
    hard_gate_fail: bool = False
    risk_flags: List[str] = field(default_factory=list)
    data_quality_flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskProfile:
    id: str
    label: str
    sector_filter: str = "all"
    scores: Dict[str, int] = field(default_factory=dict)
    max_stock_risk: float = 55.0
    max_beta: float = 1.3
    cyclical_ok: bool = True
    diversify_sectors: bool = True
    diversification_level: str = "moderate"
    needs_liquidity: bool = False
    valuation_pref: str = "fair"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FitResult:
    ticker: str
    fit_score: float
    fit_label: str
    exclude: bool
    reasons: List[str]
    recommendation: str = "HOLD"
    action_label: str = "HOLD"
    headline: str = ""
    composite_score: float = 0.0
    stock_risk_score: float = 0.0
    quality_grade: str = "C"
    peer_percentile: Optional[float] = None
    peer_band: str = "Lower-Mid"
    sector_focus: str = ""
    analysis_depth: str = "standard"
    data_quality_flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RecommendationResult:
    risk_profile: RiskProfile
    picks: List[FitResult]
    avoid: List[FitResult]
    summary: str
    picks_by_sector: Dict[str, List[FitResult]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_profile": self.risk_profile.to_dict(),
            "picks": [p.to_dict() for p in self.picks],
            "avoid": [a.to_dict() for a in self.avoid],
            "summary": self.summary,
            "picks_by_sector": {
                k: [p.to_dict() for p in v] for k, v in self.picks_by_sector.items()
            },
        }
