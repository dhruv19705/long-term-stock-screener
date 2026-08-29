from __future__ import annotations

from typing import List, Optional

from screener.models import QuestionAnswer, ScoreResult, StockMetrics

_DIMENSION_COPY: dict[tuple[str, str], str] = {
    ("leverage_risk", "good"): "Balance sheet leverage is within comfortable limits.",
    ("leverage_risk", "warn"): "Leverage is moderate — worth monitoring against sector norms.",
    ("leverage_risk", "bad"): "Balance sheet leverage is elevated relative to comfort levels.",
    ("credit_risk", "good"): "Asset quality and credit metrics look healthy.",
    ("credit_risk", "warn"): "Credit quality shows some pressure but remains manageable.",
    ("credit_risk", "bad"): "Asset quality metrics raise credit concerns.",
    ("solvency_risk", "good"): "Capital and solvency buffers appear adequate.",
    ("solvency_risk", "warn"): "Solvency metrics are acceptable but not strong.",
    ("solvency_risk", "bad"): "Solvency or capital buffers look thin.",
    ("valuation_risk", "good"): "Valuation appears reasonable on absolute and peer measures.",
    ("valuation_risk", "warn"): "Valuation is fair — limited margin of safety.",
    ("valuation_risk", "bad"): "Valuation looks stretched versus fundamentals.",
    ("earnings_risk", "good"): "Earnings quality and profitability support the thesis.",
    ("earnings_risk", "warn"): "Earnings trends are mixed or slowing.",
    ("earnings_risk", "bad"): "Earnings quality or profitability is weak.",
    ("growth_risk", "good"): "Growth profile is healthy and sustainable.",
    ("growth_risk", "warn"): "Growth is present but uneven or decelerating.",
    ("growth_risk", "bad"): "Growth metrics are weak or unreliable.",
    ("market_risk", "good"): "Price momentum and drawdown profile are acceptable.",
    ("market_risk", "warn"): "Recent price action shows caution flags.",
    ("market_risk", "bad"): "Momentum or drawdown risk is elevated.",
    ("data_risk", "good"): "Data coverage is sufficient to trust this score.",
    ("data_risk", "warn"): "Some metrics are missing — interpret with caution.",
    ("data_risk", "bad"): "Limited data reduces confidence in this assessment.",
    ("franchise_risk", "good"): "Franchise strength and returns profile look solid.",
    ("franchise_risk", "warn"): "Franchise metrics are average for the peer group.",
    ("franchise_risk", "bad"): "Franchise or return metrics lag peers.",
    ("margin_risk", "good"): "Margin quality supports the business model.",
    ("margin_risk", "warn"): "Margins are stable but not expanding.",
    ("margin_risk", "bad"): "Margin pressure is a concern.",
}

_SECTOR_LABEL = {
    "banking": "Bank",
    "insurance": "Insurer",
    "it": "IT",
    "fmcg": "FMCG",
    "pharma": "Pharma",
    "auto": "Auto",
    "energy": "Energy",
    "metals": "Metals",
    "capital_goods": "Industrials",
}

_SECTOR_FILTER_LABELS = {
    "all": "All sectors",
    "defensive": "Defensive sectors (FMCG, Pharma)",
    "cyclical": "Cyclical sectors",
    "no_financials": "Excluding financials",
    "both": "Financials & technology only",
}


def _dimension_line(q: QuestionAnswer) -> str:
    key = (q.dimension, q.signal)
    if key in _DIMENSION_COPY:
        return _DIMENSION_COPY[key]
    if q.signal == "good":
        return f"Positive read on {q.dimension.replace('_', ' ')}."
    if q.signal == "warn":
        return f"Mixed signals on {q.dimension.replace('_', ' ')}."
    if q.signal == "unknown":
        return f"Insufficient data to assess {q.dimension.replace('_', ' ')}."
    return f"Concern on {q.dimension.replace('_', ' ')}."


def answer_for(q: QuestionAnswer, metrics_snap: dict) -> str:
    line = _dimension_line(q)
    bits = []
    for k, v in metrics_snap.items():
        if v is None or k in ("valuation_label", "red_flag", "composite_score"):
            continue
        if isinstance(v, float):
            bits.append(f"{k}={v:.2f}")
        else:
            bits.append(f"{k}={v}")
    if bits:
        return f"{line} ({', '.join(bits[:3])})"
    return line


def headline(m: StockMetrics, score: ScoreResult, risk: float) -> str:
    focus = _SECTOR_LABEL.get(m.sector_focus, m.sector_focus.replace("_", " ").title())
    val = score.valuation_label.lower()
    hook = {
        "Under": "attractive on valuation",
        "Fair": "fairly valued",
        "Over": "priced for perfection",
    }.get(score.valuation_label, val)
    return (
        f"{focus} · {score.recommendation} · "
        f"{hook} · risk {risk:.0f}/100."
    )


def bull_bear(questions: List[QuestionAnswer]) -> tuple[list[str], list[str]]:
    bull = [_dimension_line(q) for q in questions if q.signal == "good"]
    bear = [_dimension_line(q) for q in questions if q.signal == "bad"]
    return bull[:5], bear[:5]


def verdict(score: ScoreResult, risk: float, profile_hint: str | None = None) -> str:
    base = (
        f"{score.recommendation} — composite {score.composite_score:.0f}/100, "
        f"{score.valuation_label.lower()} valuation, stock risk {risk:.0f}/100."
    )
    if score.hard_gate_fail:
        return base + " A hard risk gate failed — treat as high caution."
    if profile_hint:
        return base + f" {profile_hint}"
    return base


def key_risk(questions: List[QuestionAnswer], m: StockMetrics) -> str:
    bad = [q for q in questions if q.signal == "bad"]
    if bad:
        return _dimension_line(bad[0])
    warn = [q for q in questions if q.signal == "warn"]
    if warn:
        return _dimension_line(warn[0])
    if m.max_drawdown_1y_pct is not None and m.max_drawdown_1y_pct < -25:
        return f"Elevated drawdown risk ({m.max_drawdown_1y_pct:.1f}% max drawdown over 1 year)."
    return "No acute red flags in scored dimensions; monitor sector and macro trends."


def build_profile_summary(profile) -> List[str]:
    """Human-readable constraint bullets for questionnaire review."""
    lines = [f"Risk profile: {profile.label}"]
    lines.append(f"Max single-stock risk score: {profile.max_stock_risk:.0f}")
    lines.append(f"Max portfolio beta: {profile.max_beta:.2f}")
    if not profile.cyclical_ok:
        lines.append("Cyclical sectors: excluded from recommendations")
    else:
        lines.append("Cyclical sectors: allowed")
    universe = _SECTOR_FILTER_LABELS.get(profile.sector_filter, profile.sector_filter)
    lines.append(f"Stock universe: {universe}")
    if profile.diversify_sectors:
        lines.append("Recommendations spread across sectors")
    else:
        lines.append("Best ideas only — sector diversification off")
    if profile.needs_liquidity:
        lines.append("Prefers lower-volatility names (may need to sell soon)")
    lines.append(f"Max concentration per stock: {profile.max_concentration_pct:.0f}%")
    return lines
