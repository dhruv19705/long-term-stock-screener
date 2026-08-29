from screener.data.normalize import adjust_debt_for_finance_subsidiary, normalize_debt_to_equity, sanitize_metrics
from screener.models import StockMetrics
from screener.scoring.hard_gates import evaluate_generic_gates


def test_debt_to_equity_yfinance_percent():
    assert abs(normalize_debt_to_equity(9.541) - 0.09541) < 1e-6
    assert abs(normalize_debt_to_equity(954.1) - 9.541) < 1e-6
    assert normalize_debt_to_equity(0.45) == 0.45


def test_finance_subsidiary_de_cap():
    capped = adjust_debt_for_finance_subsidiary("HEROMOTOCO.NS", 3.57)
    assert capped == 1.5
    assert adjust_debt_for_finance_subsidiary("TCS.NS", 0.2) == 0.2


def test_sanitize_clamps_roe():
    m = StockMetrics("X.NS", "Tech", roe_pct=120.0, pe=800.0, debt_to_equity=9.5)
    out = sanitize_metrics(m)
    assert out.roe_pct == 80.0
    assert out.pe is None
    assert out.debt_to_equity == 0.095


def test_auto_sector_higher_de_limit():
    m = StockMetrics(
        "HEROMOTOCO.NS",
        "Auto",
        sector_focus="auto",
        debt_to_equity=3.2,
        roe_pct=15.0,
        operating_margin_pct=10.0,
    )
    hard, red, _ = evaluate_generic_gates(m, "auto")
    assert hard is False
    assert red is False


def test_energy_margin_distortion():
    m = StockMetrics(
        "BPCL.NS",
        "Energy",
        sector_focus="energy",
        operating_margin_pct=-4.0,
        market_cap=1_400_000_000_000,
        free_cash_flow_ttm=1e9,
    )
    hard, red, md = evaluate_generic_gates(m, "energy")
    assert hard is False
    assert md is True
