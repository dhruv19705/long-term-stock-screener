from __future__ import annotations

from typing import Any, Dict, List, Tuple

from screener.config_loader import load_user_questionnaire
from screener.interpret.narrative import build_profile_summary
from screener.models import RiskProfile

# max_beta = comfort knot (first beta with zero penalty) for display
PROFILE_DEFAULTS = {
    "conservative": {"max_stock_risk": 40, "max_beta": 1.0, "cyclical_ok": False},
    "moderate": {"max_stock_risk": 55, "max_beta": 1.3, "cyclical_ok": True},
    "growth": {"max_stock_risk": 65, "max_beta": 1.5, "cyclical_ok": True},
    "aggressive": {"max_stock_risk": 80, "max_beta": 2.0, "cyclical_ok": True},
}

QUESTION_CHAPTERS: Dict[str, str] = {
    "horizon": "objective",
    "objective": "objective",
    "income_need": "objective",
    "drawdown": "risk",
    "loss_tolerance": "risk",
    "volatility": "risk",
    "liquidity": "risk",
    "valuation_pref": "preferences",
    "cyclical_pref": "preferences",
    "diversification": "portfolio",
    "sector_restrictions": "portfolio",
}

CHAPTER_META = [
    {"id": "objective", "label": "Investment objective", "description": "Horizon and goals"},
    {"id": "risk", "label": "Risk tolerance", "description": "How you handle losses and volatility"},
    {"id": "preferences", "label": "Investment preferences", "description": "Valuation and sector tilt"},
    {"id": "portfolio", "label": "Portfolio construction", "description": "Diversification and sector filters"},
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
                "chapter": QUESTION_CHAPTERS.get(q["id"], "objective"),
                "options": [{"id": o["id"], "label": o["label"]} for o in q["options"]],
            }
        )
    return {"profiles": cfg["profiles"], "chapters": CHAPTER_META, "questions": questions}


def _resolve_sector_filter(cyclical_filter: str, restrictions_filter: str | None) -> str:
    if restrictions_filter in RESTRICTIVE_SECTOR_FILTERS:
        return restrictions_filter
    if restrictions_filter == "all":
        return cyclical_filter
    return cyclical_filter


def _parse_answers(answers: Dict[str, str]) -> Tuple[Dict[str, int], Dict[str, Any]]:
    cfg = load_user_questionnaire()
    totals = {p["id"]: 0 for p in cfg["profiles"]}
    cyclical_sector_filter = "all"
    restrictions_filter: str | None = None
    max_stock_risk = 55.0
    cyclical_ok = True
    diversification_level = "moderate"
    needs_liquidity = False
    valuation_pref = "fair"
    user_set_risk = False

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
        if qid == "sector_restrictions" and "sector_filter" in opt:
            restrictions_filter = opt["sector_filter"]

        if "max_stock_risk" in opt:
            max_stock_risk = float(opt["max_stock_risk"])
            user_set_risk = True
        if "cyclical_ok" in opt:
            cyclical_ok = bool(opt["cyclical_ok"])
        if "diversification_level" in opt:
            diversification_level = str(opt["diversification_level"])
        if "needs_liquidity" in opt:
            needs_liquidity = bool(opt["needs_liquidity"])
        if "valuation_pref" in opt:
            valuation_pref = str(opt["valuation_pref"])

        scores = opt.get("scores") or {}
        for pid, pts in scores.items():
            if pid in totals:
                totals[pid] += int(pts)

    sector_filter = _resolve_sector_filter(cyclical_sector_filter, restrictions_filter)
    diversify_sectors = diversification_level != "concentrated"

    constraints = {
        "sector_filter": sector_filter,
        "max_stock_risk": max_stock_risk,
        "cyclical_ok": cyclical_ok,
        "diversify_sectors": diversify_sectors,
        "diversification_level": diversification_level,
        "needs_liquidity": needs_liquidity,
        "valuation_pref": valuation_pref,
        "user_set_risk": user_set_risk,
    }
    return totals, constraints


def profile_from_answers(answers: Dict[str, str]) -> RiskProfile:
    cfg = load_user_questionnaire()
    totals, c = _parse_answers(answers)
    best_id = max(totals, key=lambda k: totals[k])
    defaults = PROFILE_DEFAULTS.get(best_id, PROFILE_DEFAULTS["moderate"])
    label = next(p["label"] for p in cfg["profiles"] if p["id"] == best_id)

    max_stock_risk = c["max_stock_risk"] if c["user_set_risk"] else defaults["max_stock_risk"]

    return RiskProfile(
        id=best_id,
        label=label,
        sector_filter=c["sector_filter"],
        scores=totals,
        max_stock_risk=max_stock_risk,
        max_beta=defaults["max_beta"],
        cyclical_ok=c["cyclical_ok"],
        diversify_sectors=c["diversify_sectors"],
        diversification_level=c["diversification_level"],
        needs_liquidity=c["needs_liquidity"],
        valuation_pref=c["valuation_pref"],
    )


def preview_from_answers(answers: Dict[str, str]) -> Dict[str, Any]:
    cfg = load_user_questionnaire()
    totals, _c = _parse_answers(answers)
    best_id = max(totals, key=lambda k: totals[k]) if any(totals.values()) else "moderate"
    label = next((p["label"] for p in cfg["profiles"] if p["id"] == best_id), "Balanced Growth")
    profile = profile_from_answers(answers) if len(answers) >= len(cfg["questions"]) else None
    if profile is None:
        _totals, constraints = _parse_answers(answers)
        defaults = PROFILE_DEFAULTS.get(best_id, PROFILE_DEFAULTS["moderate"])
        profile = RiskProfile(
            id=best_id,
            label=label,
            sector_filter=constraints["sector_filter"],
            scores=totals,
            max_stock_risk=constraints["max_stock_risk"] if constraints["user_set_risk"] else defaults["max_stock_risk"],
            max_beta=defaults["max_beta"],
            cyclical_ok=constraints["cyclical_ok"],
            diversify_sectors=constraints["diversify_sectors"],
            diversification_level=constraints["diversification_level"],
            needs_liquidity=constraints["needs_liquidity"],
            valuation_pref=constraints["valuation_pref"],
        )
    return {
        "profile_scores": totals,
        "leading_profile_id": best_id,
        "leading_profile_label": label,
        "profile_summary": build_profile_summary(profile),
        "answered_count": len(answers),
        "total_questions": len(cfg["questions"]),
    }
