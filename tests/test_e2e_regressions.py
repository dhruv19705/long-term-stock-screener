"""P0 regression tests from E2E audit."""
from __future__ import annotations

from screener.data.banking import enrich_banking_metrics
from screener.data.fetcher import _apply_ticker_meta, get_stock_data
from screener.interpret.narrative import headline
from screener.interpret.questionnaire import questionnaire_payload
from screener.models import RiskProfile, ScoreResult, StockMetrics
from screener.pipeline import run_evaluation, STATE


def test_curated_nnpa_not_multiplied():
    m = StockMetrics(
        ticker="HDFCBANK.NS",
        sector="Financial Services",
        sector_focus="banking",
        analysis_depth="deep",
        nnpa_pct=40.0,  # stale cache bug value
    )
    out = enrich_banking_metrics(m)
    assert out.nnpa_pct == 0.40
    assert out.gnpa_pct == 1.35


def test_apply_ticker_meta_from_stale_cache():
    m = StockMetrics(ticker="TCS.NS", sector="Technology", sector_focus="it")
    out = _apply_ticker_meta(m)
    assert out.analysis_depth == "deep"
    assert out.model_sector == "IT"


def test_questionnaire_option_ids_are_strings():
    payload = questionnaire_payload()
    for q in payload["questions"]:
        for opt in q["options"]:
            assert isinstance(opt["id"], str), f"{q['id']} has non-string option id {opt['id']!r}"


def test_headline_sector_labels():
    m = StockMetrics("RADICO.NS", "Consumer Defensive", sector_focus="fmcg", analysis_depth="standard")
    s = ScoreResult("Consumer Defensive", "fmcg", composite_score=68, valuation_label="Under", quality_grade="B", recommendation="BUY")
    h = headline(m, s, 33)
    assert "FMCG" in h
    assert "IT" not in h.split("·")[0]
    assert "deep" not in h.lower()


def test_e2e_banking_and_it_in_recommendations():
    run_evaluation(sector_filter="all", use_cache=True)
    assert STATE.metrics["HDFCBANK.NS"].nnpa_pct == 0.40
    assert STATE.metrics["HDFCBANK.NS"].analysis_depth == "deep"
    assert len(STATE.interps["HDFCBANK.NS"].questions) == 7

    profile = RiskProfile(id="moderate", label="Balanced", sector_filter="all", diversify_sectors=True)
    result = STATE.recommend(profile)
    sectors = {p.sector_focus for p in result.picks}
    assert "banking" in sectors
    assert "it" in sectors
    fin_tech_picks = [p for p in result.picks if p.sector_focus in ("banking", "it")]
    assert len(fin_tech_picks) >= 4
