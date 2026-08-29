from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QuestionnaireOption(BaseModel):
    id: str
    label: str


class QuestionnaireQuestion(BaseModel):
    id: str
    text: str
    options: List[QuestionnaireOption]


class QuestionnaireResponse(BaseModel):
    profiles: List[Dict[str, str]]
    questions: List[QuestionnaireQuestion]


class AnswersRequest(BaseModel):
    answers: Dict[str, str] = Field(..., description="question_id -> option_id")


class RiskProfileOut(BaseModel):
    id: str
    label: str
    sector_filter: str
    scores: Dict[str, int] = {}
    max_stock_risk: float = 55.0
    max_beta: float = 1.35
    cyclical_ok: bool = True
    diversify_sectors: bool = True
    needs_liquidity: bool = False
    max_concentration_pct: float = 20.0
    profile_summary: List[str] = Field(default_factory=list)
    profile_scores: Dict[str, int] = Field(default_factory=dict)


class QuestionnairePreviewResponse(BaseModel):
    profile_scores: Dict[str, int]
    leading_profile_id: str
    leading_profile_label: str
    profile_summary: List[str]
    answered_count: int
    total_questions: int


class RecommendRequest(BaseModel):
    risk_profile_id: str = "moderate"
    sector_filter: str = "all"
    label: Optional[str] = None
    max_stock_risk: Optional[float] = None
    max_beta: Optional[float] = None
    cyclical_ok: Optional[bool] = None
    diversify_sectors: Optional[bool] = None
    needs_liquidity: Optional[bool] = None
    max_concentration_pct: Optional[float] = None
    scores: Optional[Dict[str, int]] = None


class FitOut(BaseModel):
    ticker: str
    fit_score: float
    fit_label: str
    exclude: bool
    reasons: List[str]
    recommendation: str
    action_label: str = "HOLD"
    headline: str
    composite_score: float
    stock_risk_score: float
    quality_grade: str = "C"
    peer_percentile: Optional[float] = None
    peer_band: str = "Lower-Mid"
    sector_focus: str
    analysis_depth: str = "standard"
    data_quality_flags: List[str] = Field(default_factory=list)


class RecommendResponse(BaseModel):
    risk_profile: RiskProfileOut
    picks: List[FitOut]
    avoid: List[FitOut]
    summary: str


class QuestionAnswerOut(BaseModel):
    id: str
    question: str
    dimension: str
    signal: str
    metrics: Dict[str, Any]
    peer_rank: Optional[str] = None
    answer: str = ""


class QuoteSnapshot(BaseModel):
    ticker: Optional[str] = None
    company_name: Optional[str] = None
    currency: Optional[str] = None
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None
    day_open: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    volume: Optional[float] = None
    avg_volume: Optional[float] = None
    market_cap: Optional[float] = None
    pe: Optional[float] = None
    pb: Optional[float] = None
    dividend_yield_pct: Optional[float] = None
    roe_pct: Optional[float] = None
    return_1y_pct: Optional[float] = None


class HistoryPoint(BaseModel):
    date: str
    close: float


class QuoteResponse(QuoteSnapshot):
    ticker: str
    history: List[HistoryPoint] = Field(default_factory=list)


class InterpretResponse(BaseModel):
    ticker: str
    sector: str
    sector_focus: str
    model_sector: str = "UNKNOWN"
    analysis_depth: str = "standard"
    recommendation: str
    composite_score: float
    composite_percentile: Optional[float] = None
    quality_grade: str = "C"
    peer_band: str = "Lower-Mid"
    stock_risk_score: float
    confidence: float
    valuation_label: str
    headline: str
    questions: List[QuestionAnswerOut]
    bull_case: List[str]
    bear_case: List[str]
    key_risk: str
    verdict: str
    score_breakdown: Dict[str, float] = {}
    peer_rank: Optional[int] = None
    peer_count: Optional[int] = None
    red_flag: bool = False
    hard_gate_fail: bool = False
    risk_flags: List[str] = []
    quote: Optional[QuoteSnapshot] = None
