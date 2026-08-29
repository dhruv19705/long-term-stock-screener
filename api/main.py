from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    AnswersRequest,
    QuestionnaireResponse,
    QuoteResponse,
    RecommendRequest,
    RecommendResponse,
    RiskProfileOut,
)
from screener.config_loader import FILTER_TO_BUCKETS, list_sector_buckets
from screener.data.quote import fetch_quote, snapshot_from_metrics
from screener.interpret.questionnaire import profile_from_answers, questionnaire_payload, preview_from_answers
from screener.models import RiskProfile
from screener.pipeline import STATE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

VALID_SECTORS = list(FILTER_TO_BUCKETS.keys())

app = FastAPI(title="Full Universe Stock Screener", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ensure_screen(sector_filter: str = "all", refresh: bool = False) -> None:
    if refresh or not STATE.scores or STATE.last_filter != sector_filter:
        STATE.run(sector_filter=sector_filter, refresh=refresh)


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "universe": "full"}


@app.get("/api/sectors")
def list_sectors() -> Dict[str, Any]:
    return {"sectors": list_sector_buckets(), "filters": VALID_SECTORS}


@app.get("/api/questionnaire", response_model=QuestionnaireResponse)
def get_questionnaire() -> Any:
    return questionnaire_payload()


@app.post("/api/questionnaire/submit", response_model=RiskProfileOut)
def submit_questionnaire(body: AnswersRequest) -> Any:
    profile = profile_from_answers(body.answers)
    from screener.interpret.narrative import build_profile_summary

    out = profile.to_dict()
    out["profile_summary"] = build_profile_summary(profile)
    out["profile_scores"] = dict(profile.scores)
    return out


@app.post("/api/questionnaire/preview")
def preview_questionnaire(body: AnswersRequest) -> Any:
    return preview_from_answers(body.answers)


@app.post("/api/recommend")
def recommend(body: RecommendRequest) -> Any:
    sector = body.sector_filter or "all"
    _ensure_screen(sector_filter=sector)
    labels = {
        "conservative": "Capital Preservation",
        "moderate": "Balanced Growth",
        "growth": "Growth Oriented",
        "aggressive": "High Conviction",
    }
    from screener.interpret.questionnaire import PROFILE_DEFAULTS

    defaults = PROFILE_DEFAULTS.get(body.risk_profile_id, PROFILE_DEFAULTS["moderate"])
    profile = RiskProfile(
        id=body.risk_profile_id,
        label=body.label or labels.get(body.risk_profile_id, body.risk_profile_id),
        sector_filter=sector,
        scores=body.scores or {},
        max_stock_risk=body.max_stock_risk if body.max_stock_risk is not None else defaults["max_stock_risk"],
        max_beta=body.max_beta if body.max_beta is not None else defaults["max_beta"],
        cyclical_ok=body.cyclical_ok if body.cyclical_ok is not None else defaults["cyclical_ok"],
        diversify_sectors=body.diversify_sectors if body.diversify_sectors is not None else True,
        needs_liquidity=body.needs_liquidity if body.needs_liquidity is not None else False,
        max_concentration_pct=body.max_concentration_pct if body.max_concentration_pct is not None else 20.0,
    )
    result = STATE.recommend(profile)
    return result.to_dict()


@app.get("/api/screen")
def screen(
    sector: str = Query("all"),
    refresh: bool = False,
) -> Dict[str, Any]:
    if sector not in VALID_SECTORS:
        raise HTTPException(400, f"sector must be one of {VALID_SECTORS}")
    _ensure_screen(sector_filter=sector, refresh=refresh)
    df = STATE.to_dataframe()
    if sector not in ("all", "both", "defensive", "cyclical", "no_financials"):
        df = df[df["sector_focus"] == sector]
    elif sector == "both":
        df = df[df["sector_focus"].isin(["banking", "it"])]
    elif sector == "defensive":
        df = df[df["sector_focus"].isin(["fmcg", "pharma"])]
    elif sector == "cyclical":
        df = df[df["sector_focus"].isin(["auto", "energy", "metals", "capital_goods"])]
    elif sector == "no_financials":
        df = df[df["sector_focus"] != "banking"]
    return {
        "rows": df.where(df.notna(), None).to_dict(orient="records"),
        "dropped": [{"ticker": t, "reason": r} for t, r in STATE.dropped],
        "count": int(len(df)),
        "total_universe": len(STATE.metrics) + len(STATE.dropped),
    }


@app.post("/api/screen/refresh")
def refresh_screen(sector: str = Query("all")) -> Dict[str, Any]:
    return screen(sector=sector, refresh=True)


def _canonical_ticker(ticker: str) -> str:
    t = ticker.upper()
    if not t.endswith(".NS") and not t.endswith(".BO"):
        t = t + ".NS"
    return t


def _resolve_universe_ticker(ticker: str) -> Optional[str]:
    t = _canonical_ticker(ticker)
    if t in STATE.interps or t in STATE.metrics:
        return t
    if ticker in STATE.interps or ticker in STATE.metrics:
        return ticker
    for key in list(STATE.interps.keys()) + list(STATE.metrics.keys()):
        if key.upper() == ticker.upper() or key.upper() == t:
            return key
    return None


def _quote_for(ticker: str) -> Dict[str, Any]:
    t = _resolve_universe_ticker(ticker)
    if t is None:
        raise HTTPException(404, f"Ticker {ticker} not in screened universe")
    try:
        return fetch_quote(t, metrics=STATE.metrics.get(t))
    except Exception as e:
        logger.warning("Live quote failed %s: %s", t, e)
        snap = snapshot_from_metrics(STATE.metrics.get(t))
        snap["history"] = snap.get("history") or []
        return snap


@app.get("/api/stock/{ticker}/interpret")
def interpret(ticker: str) -> Any:
    _ensure_screen(sector_filter="all")
    t = _resolve_universe_ticker(ticker)
    if t is None:
        raise HTTPException(404, f"Ticker {ticker} not in screened universe")
    interp = STATE.interps.get(t)
    if interp is None:
        raise HTTPException(404, f"Ticker {ticker} not in screened universe")
    payload = interp.to_dict()
    payload["quote"] = _quote_for(t)
    return payload


@app.get("/api/quote", response_model=QuoteResponse)
def stock_quote_query(t: str = Query(..., description="Ticker, e.g. TCS.NS")) -> Any:
    """Query-param quote route — avoids 404s on dotted tickers like KAYNES.NS."""
    _ensure_screen(sector_filter="all")
    return _quote_for(t)


@app.get("/api/stock/{ticker:path}/quote", response_model=QuoteResponse)
def stock_quote(ticker: str) -> Any:
    _ensure_screen(sector_filter="all")
    if ticker.endswith("/quote"):
        ticker = ticker[: -len("/quote")]
    return _quote_for(ticker)


@app.get("/api/sectors/{sector}/summary")
def sector_summary(sector: str) -> Dict[str, Any]:
    if sector not in VALID_SECTORS and sector not in [b["id"] for b in list_sector_buckets()]:
        raise HTTPException(400, "invalid sector")
    _ensure_screen(sector_filter=sector if sector in VALID_SECTORS else "all")
    df = STATE.to_dataframe()
    if sector in VALID_SECTORS and sector not in ("all", "both", "defensive", "cyclical", "no_financials"):
        sdf = df[df["sector_focus"] == sector]
    elif sector == "both":
        sdf = df[df["sector_focus"].isin(["banking", "it"])]
    else:
        sdf = df[df["sector_focus"] == sector] if sector in df["sector_focus"].values else df

    if sdf.empty:
        return {"sector": sector, "count": 0, "top": [], "avg_composite": None}

    pass_rates: Dict[str, float] = {}
    interps = [STATE.interps[t] for t in sdf["stock"] if t in STATE.interps]
    if interps:
        dims: Dict[str, List[str]] = {}
        for itp in interps:
            for q in itp.questions:
                dims.setdefault(q.id, []).append(q.signal)
        for qid, sigs in dims.items():
            pass_rates[qid] = sum(1 for s in sigs if s == "good") / len(sigs)

    top = sdf.head(5)[
        ["stock", "composite_score", "recommendation", "valuation", "stock_risk_score", "analysis_depth"]
    ].to_dict(orient="records")
    return {
        "sector": sector,
        "count": int(len(sdf)),
        "avg_composite": float(sdf["composite_score"].mean()),
        "deep_count": int((sdf["sector_focus"].isin(["banking", "it", "insurance"])).sum()) if "sector_focus" in sdf.columns else 0,
        "rec_counts": sdf["recommendation"].value_counts().to_dict(),
        "question_pass_rates": pass_rates,
        "top": top,
    }
