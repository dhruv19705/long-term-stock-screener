from screener.interpret.questionnaire import (
    profile_from_answers,
    preview_from_answers,
    questionnaire_payload,
)


def test_questionnaire_has_fourteen_questions():
    payload = questionnaire_payload()
    assert len(payload["questions"]) == 14
    assert payload["questions"][0]["id"] == "horizon"
    assert len(payload["chapters"]) == 3
    ids = {q["id"] for q in payload["questions"]}
    assert "bank_familiar" not in ids
    assert "it_familiar" not in ids


def test_conservative_profile():
    answers = {
        "horizon": "short",
        "goal": "preserve",
        "drawdown": "sell",
        "income_need": "critical",
        "experience": "beginner",
        "loss_tolerance": "low",
        "volatility": "low",
        "valuation": "strict",
        "leverage": "low",
        "cyclical_pref": "defensive",
        "liquidity": "yes",
        "concentration": "low",
        "diversification": "yes",
        "sector_exposure": "no_fin",
    }
    p = profile_from_answers(answers)
    assert p.id == "conservative"
    assert p.sector_filter == "no_financials"
    assert p.cyclical_ok is False
    assert p.max_stock_risk == 35.0


def test_all_sectors_filter():
    answers = {
        "horizon": "long",
        "goal": "grow",
        "drawdown": "hold",
        "income_need": "nice",
        "experience": "intermediate",
        "loss_tolerance": "med",
        "volatility": "med",
        "valuation": "fair",
        "leverage": "mod",
        "cyclical_pref": "all",
        "liquidity": "no",
        "concentration": "med",
        "diversification": "yes",
        "sector_exposure": "all",
    }
    p = profile_from_answers(answers)
    assert p.sector_filter == "all"
    assert p.diversify_sectors is True


def test_sector_filter_cyclical_pref_kept_when_exposure_all():
    answers = {
        "horizon": "long",
        "goal": "grow",
        "drawdown": "hold",
        "income_need": "none",
        "experience": "experienced",
        "loss_tolerance": "high",
        "volatility": "high",
        "valuation": "pay",
        "leverage": "sector",
        "cyclical_pref": "cyclical",
        "liquidity": "no",
        "concentration": "med",
        "diversification": "yes",
        "sector_exposure": "all",
    }
    p = profile_from_answers(answers)
    assert p.sector_filter == "cyclical"


def test_preview_returns_scores():
    preview = preview_from_answers({"horizon": "short", "goal": "preserve"})
    assert preview["leading_profile_id"] == "conservative"
    assert preview["profile_scores"]["conservative"] > 0
    assert preview["answered_count"] == 2


def test_profile_summary_on_complete_answers():
    answers = {
        "horizon": "short",
        "goal": "preserve",
        "drawdown": "sell",
        "income_need": "critical",
        "experience": "beginner",
        "loss_tolerance": "low",
        "volatility": "low",
        "valuation": "strict",
        "leverage": "low",
        "cyclical_pref": "defensive",
        "liquidity": "yes",
        "concentration": "low",
        "diversification": "yes",
        "sector_exposure": "no_fin",
    }
    preview = preview_from_answers(answers)
    assert any("Risk profile" in line for line in preview["profile_summary"])
    assert any("financials" in line.lower() for line in preview["profile_summary"])
