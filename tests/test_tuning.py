from screener.interpret.stock_analyst import _merge_question_signals
from screener.models import StockMetrics
from screener.scoring.recommend_tiers import recommend_from_percentile


def test_softer_recommendation_tiers():
    assert recommend_from_percentile(65, "Fair", False, False) == "BUY"
    assert recommend_from_percentile(45, "Fair", False, False) == "HOLD"
    assert recommend_from_percentile(55, "Fair", True, False) == "HOLD"
    assert recommend_from_percentile(70, "Fair", False, False) == "STRONG BUY"


def test_cyclical_gq3_relaxed():
    base = {
        "good": {"roe_pct": {"op": ">", "value": 10.0}, "operating_margin_pct": {"op": ">", "value": 6.0}},
        "warn": {"roe_pct": {"op": ">", "value": 5.0}},
        "bad": {},
    }
    merged = _merge_question_signals("GQ3", "metals", True, base)
    assert merged["good"]["roe_pct"]["value"] == 6.0
    assert "operating_margin_pct" not in merged["good"]


def test_gq3_bad_rate_lower_for_cyclical():
    from screener.interpret.signals import evaluate_signal

    ctx = {"roe_pct": 8.0, "operating_margin_pct": 4.0}
    base = {
        "good": {"roe_pct": {"op": ">", "value": 10.0}, "operating_margin_pct": {"op": ">", "value": 6.0}},
        "warn": {"roe_pct": {"op": ">", "value": 5.0}},
        "bad": {},
    }
    cyclical = _merge_question_signals("GQ3", "auto", True, base)
    assert evaluate_signal(ctx, cyclical) == "good"
