from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
from fastapi.testclient import TestClient

from screener.data.nse_fallback import history_from_nse_chart, parse_nse_quote
from screener.data.quote import (
    finalize_quote,
    history_points,
    merge_quote,
    quote_from_history,
    quote_from_yf_info,
    snapshot_from_metrics,
)
from screener.models import StockInterpretation, StockMetrics


def test_quote_from_yf_info():
    q = quote_from_yf_info(
        {
            "shortName": "TCS",
            "longName": "Tata Consultancy Services Limited",
            "currentPrice": 3890.5,
            "previousClose": 3872.0,
            "open": 3875.0,
            "dayHigh": 3912.0,
            "dayLow": 3868.0,
            "fiftyTwoWeekHigh": 4592.0,
            "fiftyTwoWeekLow": 3056.0,
            "regularMarketVolume": 2_100_000,
            "averageVolume": 1_800_000,
            "marketCap": 14.1e12,
            "trailingPE": 29.4,
            "priceToBook": 12.1,
            "dividendYield": 0.014,
            "currency": "INR",
        }
    )
    assert q["company_name"] == "TCS"
    assert q["current_price"] == 3890.5
    assert q["previous_close"] == 3872.0
    assert q["day_high"] == 3912.0
    assert q["week_52_low"] == 3056.0
    assert q["volume"] == 2_100_000
    assert abs(q["dividend_yield_pct"] - 1.4) < 1e-9
    assert q["currency"] == "INR"


def test_quote_from_history_dataframe():
    idx = pd.date_range("2025-08-01", periods=5, freq="D")
    hist = pd.DataFrame(
        {
            "Open": [100, 101, 102, 103, 104],
            "High": [105, 106, 107, 108, 110],
            "Low": [99, 98, 100, 101, 102],
            "Close": [101, 102, 103, 104, 108],
            "Volume": [1_000, 1_100, 1_200, 1_300, 1_400],
        },
        index=idx,
    )
    q = quote_from_history(hist)
    assert q["current_price"] == 108
    assert q["previous_close"] == 104
    assert q["day_high"] == 110
    assert q["day_low"] == 102
    assert q["week_52_high"] == 110
    assert q["week_52_low"] == 98
    assert q["volume"] == 1400


def test_quote_from_history_series_and_points():
    idx = pd.date_range("2026-01-01", periods=4, freq="D")
    close = pd.Series([10.0, 11.0, 9.5, 12.0], index=idx)
    q = quote_from_history(close)
    assert q["current_price"] == 12.0
    assert q["week_52_high"] == 12.0
    assert q["week_52_low"] == 9.5
    points = history_points(close)
    assert points[0] == {"date": "2026-01-01", "close": 10.0}
    assert points[-1] == {"date": "2026-01-04", "close": 12.0}


def test_parse_nse_quote_and_chart():
    payload = {
        "info": {"companyName": "Tata Consultancy Services Limited", "symbol": "TCS"},
        "priceInfo": {
            "lastPrice": 3890.5,
            "previousClose": 3872.0,
            "open": 3875.0,
            "intraDayHighLow": {"min": 3868.0, "max": 3912.0},
            "weekHighLow": {"min": 3056.0, "max": 4592.0},
        },
        "securityWiseDP": {"quantityTraded": 2100000},
    }
    q = parse_nse_quote(payload)
    assert q["company_name"] == "Tata Consultancy Services Limited"
    assert q["current_price"] == 3890.5
    assert q["day_high"] == 3912.0
    assert q["week_52_high"] == 4592.0
    assert q["volume"] == 2100000

    ts = int(pd.Timestamp("2026-02-28").timestamp() * 1000)
    series = history_from_nse_chart({"grapthData": [[ts, 3810.0]]})
    assert series is not None
    assert float(series.iloc[0]) == 3810.0


def test_merge_and_finalize_change():
    live = {"current_price": 110.0}
    cached = {"current_price": 100.0, "previous_close": 100.0, "pe": 20.0}
    merged = merge_quote(live, cached)
    assert merged["current_price"] == 110.0
    assert merged["previous_close"] == 100.0
    out = finalize_quote("TCS.NS", merged, history=[{"date": "2026-02-28", "close": 110.0}])
    assert out["change"] == 10.0
    assert abs(out["change_pct"] - 10.0) < 1e-9
    assert out["currency"] == "INR"
    assert out["history"][0]["close"] == 110.0


def test_snapshot_from_metrics():
    m = StockMetrics(
        "TCS.NS",
        "Technology",
        current_price=3890.5,
        previous_close=3872.0,
        day_high=3912.0,
        week_52_low=3056.0,
        volume=2_100_000,
        pe=29.4,
        roe_pct=45.0,
        company_name="TCS",
    )
    snap = snapshot_from_metrics(m)
    assert snap["ticker"] == "TCS.NS"
    assert snap["company_name"] == "TCS"
    assert snap["current_price"] == 3890.5
    assert snap["change"] is not None
    assert "history" not in snap


def test_quote_endpoint_shape(monkeypatch):
    from api.main import app

    fake = {
        "ticker": "TCS.NS",
        "company_name": "Tata Consultancy Services",
        "currency": "INR",
        "current_price": 3890.5,
        "previous_close": 3872.0,
        "change": 18.5,
        "change_pct": 0.48,
        "day_open": 3875.0,
        "day_high": 3912.0,
        "day_low": 3868.0,
        "week_52_high": 4592.0,
        "week_52_low": 3056.0,
        "volume": 2_100_000,
        "avg_volume": 1_800_000,
        "market_cap": 14.1e12,
        "pe": 29.4,
        "pb": 12.1,
        "dividend_yield_pct": 1.4,
        "roe_pct": 45.0,
        "return_1y_pct": 12.0,
        "history": [{"date": "2026-02-28", "close": 3810.0}],
    }
    monkeypatch.setattr("api.main._ensure_screen", lambda **_k: None)
    monkeypatch.setattr("api.main.fetch_quote", lambda ticker, metrics=None: fake)
    monkeypatch.setattr(
        "api.main.STATE",
        SimpleNamespace(
            metrics={"TCS.NS": StockMetrics("TCS.NS", "Technology")},
            interps={"TCS.NS": StockInterpretation("TCS.NS", "Technology", "it")},
        ),
    )
    client = TestClient(app)
    r = client.get("/api/quote", params={"t": "TCS.NS"})
    assert r.status_code == 200
    body = r.json()
    assert body["current_price"] == 3890.5

    r = client.get("/api/stock/TCS.NS/quote")
    assert r.status_code == 200
    body = r.json()
    for key in (
        "ticker",
        "company_name",
        "current_price",
        "day_high",
        "day_low",
        "week_52_high",
        "week_52_low",
        "volume",
        "history",
    ):
        assert key in body
    assert body["current_price"] == 3890.5
    assert body["history"][0]["date"] == "2026-02-28"

    missing = client.get("/api/stock/NOTREAL.NS/quote")
    assert missing.status_code == 404


def test_interpret_attaches_quote_snapshot(monkeypatch):
    from api.main import app

    m = StockMetrics(
        "TCS.NS",
        "Technology",
        current_price=3890.5,
        previous_close=3872.0,
        volume=2_100_000,
    )
    interp = StockInterpretation(
        ticker="TCS.NS",
        sector="Technology",
        sector_focus="it",
        headline="Quality compounder",
        recommendation="BUY",
        composite_score=70.0,
        stock_risk_score=30.0,
        confidence=0.8,
        valuation_label="Fair",
    )
    monkeypatch.setattr("api.main._ensure_screen", lambda **_k: None)
    monkeypatch.setattr(
        "api.main.fetch_quote",
        lambda ticker, metrics=None: snapshot_from_metrics(metrics) | {"history": []},
    )
    monkeypatch.setattr(
        "api.main.STATE",
        SimpleNamespace(metrics={"TCS.NS": m}, interps={"TCS.NS": interp}),
    )
    client = TestClient(app)
    r = client.get("/api/stock/TCS/interpret")
    assert r.status_code == 200
    body = r.json()
    assert body["quote"]["current_price"] == 3890.5
    assert body["quote"]["volume"] == 2_100_000
