from screener.interpret.questionnaire import (
    profile_from_answers,
    preview_from_answers,
    questionnaire_payload,
)


def _full_conservative_answers() -> dict:
    return {
        "horizon": "short",
        "objective": "preserve",
        "income_need": "high",
        "drawdown": "sell",
        "loss_tolerance": "low",
        "volatility": "very_low",
        "liquidity": "yes",
        "valuation_pref": "strict",
        "cyclical_pref": "avoid",
        "diversification": "high",
        "sector_restrictions": "avoid_fin",
    }


def test_questionnaire_has_eleven_questions():
    payload = questionnaire_payload()
    assert len(payload["questions"]) == 11
    assert payload["questions"][0]["id"] == "horizon"
    assert len(payload["chapters"]) == 4
    ids = {q["id"] for q in payload["questions"]}
    assert "experience" not in ids
    assert "leverage" not in ids
    assert "concentration" not in ids
    assert "objective" in ids
    assert "valuation_pref" in ids


def test_conservative_profile():
    p = profile_from_answers(_full_conservative_answers())
    assert p.id == "conservative"
    assert p.sector_filter == "no_financials"
    assert p.cyclical_ok is False
    assert p.max_stock_risk == 35.0
    assert p.max_beta == 1.0
    assert p.diversification_level == "high"
    assert p.valuation_pref == "strict"


def test_growth_medium_vol_does_not_override_beta():
    answers = {
        "horizon": "vlong",
        "objective": "max",
        "income_need": "none",
        "drawdown": "buy",
        "loss_tolerance": "high",
        "volatility": "moderate",
        "liquidity": "no",
        "valuation_pref": "growth",
        "cyclical_pref": "prefer",
        "diversification": "concentrated",
        "sector_restrictions": "none",
    }
    p = profile_from_answers(answers)
    assert p.id == "aggressive"
    assert p.max_beta == 2.0


def test_all_sectors_filter():
    answers = {
        "horizon": "long",
        "objective": "balanced",
        "income_need": "moderate",
        "drawdown": "hold",
        "loss_tolerance": "med",
        "volatility": "moderate",
        "liquidity": "no",
        "valuation_pref": "fair",
        "cyclical_pref": "some",
        "diversification": "moderate",
        "sector_restrictions": "none",
    }
    p = profile_from_answers(answers)
    assert p.sector_filter == "all"
    assert p.diversify_sectors is True
    assert p.diversification_level == "moderate"


def test_cyclical_pref_when_no_restrictions():
    answers = {
        "horizon": "long",
        "objective": "max",
        "income_need": "none",
        "drawdown": "buy",
        "loss_tolerance": "high",
        "volatility": "high",
        "liquidity": "no",
        "valuation_pref": "growth",
        "cyclical_pref": "prefer",
        "diversification": "moderate",
        "sector_restrictions": "none",
    }
    p = profile_from_answers(answers)
    assert p.sector_filter == "cyclical"


def test_preview_returns_scores():
    preview = preview_from_answers({"horizon": "short", "objective": "preserve"})
    assert preview["leading_profile_id"] == "conservative"
    assert preview["profile_scores"]["conservative"] > 0
    assert preview["answered_count"] == 2


def test_profile_summary_on_complete_answers():
    preview = preview_from_answers(_full_conservative_answers())
    assert any("Risk profile" in line for line in preview["profile_summary"])
    assert any("Beta comfort" in line for line in preview["profile_summary"])
    assert not any("concentration" in line.lower() for line in preview["profile_summary"])
