from __future__ import annotations

from typing import Any, Dict, List, Tuple

from screener.config_loader import load_user_questionnaire
from screener.interpret.narrative import build_profile_summary
from screener.models import RiskProfile

PROFILE_DEFAULTS = {
    "conservative": {"max_stock_risk": 40, "max_beta": 1.15, "cyclical_ok": False},
    "moderate": {"max_stock_risk": 55, "max_beta": 1.35, "cyclical_ok": True},
    "growth": {"max_stock_risk": 65, "max_beta": 1.6, "cyclical_ok": True},
    "aggressive": {"max_stock_risk": 80, "max_beta": 2.0, "cyclical_ok": True},
}

# Question id -> chapter for UI stepper
QUESTION_CHAPTERS: Dict[str, str] = {
    "horizon": "goals",
    "goal": "goals",
    "income_need": "goals",
    "experience": "goals",
    "drawdown": "risk",
    "loss_tolerance": "risk",
    "volatility": "risk",
    "valuation": "risk",
    "leverage": "risk",
    "liquidity": "risk",
    "cyclical_pref": "portfolio",
    "concentration": "portfolio",
    "diversification": "portfolio",
    "sector_exposure": "portfolio",
}

CHAPTER_META = [
    {"id": "goals", "label": "Your goals", "description": "What you're investing for"},
    {"id": "risk", "label": "Risk tolerance", "description": "Limits we enforce when matching stocks"},
    {"id": "portfolio", "label": "Portfolio rules", "description": "Sector filters and diversification"},
]

RESTRICTIVE_SECTOR_FILTERS = {"no_financials", "both"}


def questionnaire_payload() -> Dict[str, Any]:
    cfg = load_user_questionnaire()
    questions = []
    for q in cfg["questions"]:
        questions.append(
            {
                "id": q["id"],
                "text": q["text"],
                "chapter": QUESTION_CHAPTERS.get(q["id"], "goals"),
                "options": [{"id": o["id"], "label": o["label"]} for o in q["options"]],
            }
        )
    return {"profiles": cfg["profiles"], "chapters": CHAPTER_META, "questions": questions}


def _resolve_sector_filter(cyclical_filter: str, exposure_filter: str | None) -> str:
    """
    cyclical_pref sets a broad sector preference; sector_exposure overrides only when
    the user picks a restrictive universe (no financials or financials+IT only).
    """
    if exposure_filter in RESTRICTIVE_SECTOR_FILTERS:
        return exposure_filter
    if exposure_filter == "all":
        return cyclical_filter
    return cyclical_filter


def _parse_answers(answers: Dict[str, str]) -> Tuple[Dict[str, int], Dict[str, Any]]:
    cfg = load_user_questionnaire()
    totals = {p["id"]: 0 for p in cfg["profiles"]}
    cyclical_sector_filter = "all"
    exposure_sector_filter: str | None = None
    max_stock_risk = 55.0
    max_beta = 1.35
    cyclical_ok = True
    diversify_sectors = True
    needs_liquidity = False
    max_concentration_pct = 20.0
    user_set_risk = False
    user_set_beta = False

    for q in cfg["questions"]:
        qid = q["id"]
        oid = answers.get(qid)
        if not oid:
            continue
        opt = next((o for o in q["options"] if o["id"] == oid), None)
        if not opt:
            continue

        if qid == "cyclical_pref" and "sector_filter" in opt:
            cyclical_sector_filter = opt["sector_filter"]
        if qid == "sector_exposure" and "sector_filter" in opt:
            exposure_sector_filter = opt["sector_filter"]

        if "max_stock_risk" in opt:
            max_stock_risk = float(opt["max_stock_risk"])
            user_set_risk = True
        if "max_beta" in opt:
            max_beta = float(opt["max_beta"])
            user_set_beta = True
        if "cyclical_ok" in opt:
            cyclical_ok = bool(opt["cyclical_ok"])
        if "diversify_sectors" in opt:
            diversify_sectors = bool(opt["diversify_sectors"])
        if "needs_liquidity" in opt:
            needs_liquidity = bool(opt["needs_liquidity"])
        if "max_concentration_pct" in opt:
            max_concentration_pct = float(opt["max_concentration_pct"])

        scores = opt.get("scores") or {}
        for pid, pts in scores.items():
            if pid in totals:
                totals[pid] += int(pts)

    sector_filter = _resolve_sector_filter(cyclical_sector_filter, exposure_sector_filter)

    constraints = {
        "sector_filter": sector_filter,
        "max_stock_risk": max_stock_risk,
        "max_beta": max_beta,
        "cyclical_ok": cyclical_ok,
        "diversify_sectors": diversify_sectors,
        "needs_liquidity": needs_liquidity,
        "max_concentration_pct": max_concentration_pct,
        "user_set_risk": user_set_risk,
        "user_set_beta": user_set_beta,
    }
    return totals, constraints


def profile_from_answers(answers: Dict[str, str]) -> RiskProfile:
    cfg = load_user_questionnaire()
    totals, c = _parse_answers(answers)
    best_id = max(totals, key=lambda k: totals[k])
    defaults = PROFILE_DEFAULTS.get(best_id, PROFILE_DEFAULTS["moderate"])
    label = next(p["label"] for p in cfg["profiles"] if p["id"] == best_id)

    max_stock_risk = c["max_stock_risk"] if c["user_set_risk"] else defaults["max_stock_risk"]
    max_beta = c["max_beta"] if c["user_set_beta"] else defaults["max_beta"]

    return RiskProfile(
        id=best_id,
        label=label,
        sector_filter=c["sector_filter"],
        scores=totals,
        max_stock_risk=max_stock_risk,
        max_beta=max_beta,
        cyclical_ok=c["cyclical_ok"],
        diversify_sectors=c["diversify_sectors"],
        needs_liquidity=c["needs_liquidity"],
        max_concentration_pct=c["max_concentration_pct"],
    )


def preview_from_answers(answers: Dict[str, str]) -> Dict[str, Any]:
    """Partial or complete answers → profile scores and projected profile."""
    cfg = load_user_questionnaire()
    totals, _c = _parse_answers(answers)
    best_id = max(totals, key=lambda k: totals[k]) if any(totals.values()) else "moderate"
    label = next((p["label"] for p in cfg["profiles"] if p["id"] == best_id), "Balanced Growth")
    profile = profile_from_answers(answers) if len(answers) >= len(cfg["questions"]) else None
    if profile is None:
        # Build partial profile for preview with best-effort constraints
        _totals, constraints = _parse_answers(answers)
        defaults = PROFILE_DEFAULTS.get(best_id, PROFILE_DEFAULTS["moderate"])
        profile = RiskProfile(
            id=best_id,
            label=label,
            sector_filter=constraints["sector_filter"],
            scores=totals,
            max_stock_risk=constraints["max_stock_risk"] if constraints["user_set_risk"] else defaults["max_stock_risk"],
            max_beta=constraints["max_beta"] if constraints["user_set_beta"] else defaults["max_beta"],
            cyclical_ok=constraints["cyclical_ok"],
            diversify_sectors=constraints["diversify_sectors"],
            needs_liquidity=constraints["needs_liquidity"],
            max_concentration_pct=constraints["max_concentration_pct"],
        )
    return {
        "profile_scores": totals,
        "leading_profile_id": best_id,
        "leading_profile_label": label,
        "profile_summary": build_profile_summary(profile),
        "answered_count": len(answers),
        "total_questions": len(cfg["questions"]),
    }
