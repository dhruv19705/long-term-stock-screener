from __future__ import annotations

import logging
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence

import pandas as pd

from screener.config_loader import yfinance_symbols_for
from screener.data.nse_fallback import fetch_nse_history, fetch_nse_quote
from screener.features.fundamentals import safe_float
from screener.models import StockMetrics

logger = logging.getLogger("screener.quote")


def _retry(fn, tries: int = 3, delay: float = 0.5):
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            last = e
            time.sleep(delay * (2**i))
    if last:
        raise last


def _first_float(*values: object) -> Optional[float]:
    for v in values:
        parsed = safe_float(v)
        if parsed is not None:
            return parsed
    return None


def _first_str(*values: object) -> Optional[str]:
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return None


def quote_from_yf_info(info: Optional[dict]) -> Dict[str, Any]:
    info = info or {}
    dy = safe_float(info.get("dividendYield"))
    if dy is not None and abs(dy) <= 1.0:
        dy = dy * 100.0
    return _drop_none(
        {
            "company_name": _first_str(info.get("shortName"), info.get("longName")),
            "current_price": _first_float(
                info.get("currentPrice"),
                info.get("regularMarketPrice"),
                info.get("navPrice"),
            ),
            "previous_close": _first_float(
                info.get("previousClose"),
                info.get("regularMarketPreviousClose"),
            ),
            "day_open": _first_float(info.get("open"), info.get("regularMarketOpen")),
            "day_high": _first_float(info.get("dayHigh"), info.get("regularMarketDayHigh")),
            "day_low": _first_float(info.get("dayLow"), info.get("regularMarketDayLow")),
            "week_52_high": _first_float(info.get("fiftyTwoWeekHigh")),
            "week_52_low": _first_float(info.get("fiftyTwoWeekLow")),
            "volume": _first_float(info.get("regularMarketVolume"), info.get("volume")),
            "avg_volume": _first_float(
                info.get("averageVolume"),
                info.get("averageDailyVolume10Day"),
                info.get("averageVolume10days"),
            ),
            "market_cap": _first_float(info.get("marketCap")),
            "pe": _first_float(info.get("trailingPE"), info.get("forwardPE")),
            "pb": _first_float(info.get("priceToBook")),
            "dividend_yield_pct": dy,
            "currency": _first_str(info.get("currency")),
        }
    )


def quote_from_fast_info(fast: Any) -> Dict[str, Any]:
    if fast is None:
        return {}

    def get(*names: str) -> Optional[float]:
        for name in names:
            try:
                val = fast[name]
            except Exception:
                val = getattr(fast, name, None)
            parsed = safe_float(val)
            if parsed is not None:
                return parsed
        return None

    return _drop_none(
        {
            "current_price": get("last_price", "lastPrice"),
            "previous_close": get("previous_close", "previousClose"),
            "day_open": get("open"),
            "day_high": get("day_high", "dayHigh"),
            "day_low": get("day_low", "dayLow"),
            "week_52_high": get("year_high", "yearHigh"),
            "week_52_low": get("year_low", "yearLow"),
            "volume": get("last_volume", "lastVolume"),
            "avg_volume": get("ten_day_average_volume", "tenDayAverageVolume"),
            "market_cap": get("market_cap", "marketCap"),
        }
    )


def quote_from_history(hist: Any) -> Dict[str, Any]:
    if hist is None:
        return {}
    if isinstance(hist, pd.Series):
        close = hist.dropna().astype(float)
        if close.empty:
            return {}
        window = close.iloc[-min(len(close), 252) :]
        return _drop_none(
            {
                "current_price": float(close.iloc[-1]),
                "week_52_high": float(window.max()),
                "week_52_low": float(window.min()),
            }
        )
    if not isinstance(hist, pd.DataFrame) or hist.empty:
        return {}

    df = hist.copy()
    out: Dict[str, Any] = {}
    last = df.iloc[-1]
    out["current_price"] = _first_float(last.get("Close"), last.get("close"))
    out["day_open"] = _first_float(last.get("Open"), last.get("open"))
    out["day_high"] = _first_float(last.get("High"), last.get("high"))
    out["day_low"] = _first_float(last.get("Low"), last.get("low"))
    out["volume"] = _first_float(last.get("Volume"), last.get("volume"))
    if len(df) >= 2:
        prev = df.iloc[-2]
        out["previous_close"] = _first_float(prev.get("Close"), prev.get("close"))

    window = df.iloc[-min(len(df), 252) :]
    highs = window["High"] if "High" in window.columns else window.get("high")
    lows = window["Low"] if "Low" in window.columns else window.get("low")
    closes = window["Close"] if "Close" in window.columns else window.get("close")
    if highs is not None:
        out["week_52_high"] = safe_float(highs.max())
    elif closes is not None:
        out["week_52_high"] = safe_float(closes.max())
    if lows is not None:
        out["week_52_low"] = safe_float(lows.min())
    elif closes is not None:
        out["week_52_low"] = safe_float(closes.min())
    return _drop_none(out)


def history_points(hist: Any, days: int = 130) -> List[Dict[str, Any]]:
    """Last ~6 months of daily closes as {date, close}."""
    if hist is None:
        return []
    if isinstance(hist, pd.Series):
        close = hist.dropna().astype(float)
        idx = close.index
    elif isinstance(hist, pd.DataFrame) and not hist.empty:
        col = "Close" if "Close" in hist.columns else "close"
        if col not in hist.columns:
            return []
        close = hist[col].dropna().astype(float)
        idx = close.index
    else:
        return []
    if close.empty:
        return []
    close = close.iloc[-min(len(close), days) :]
    idx = close.index
    try:
        idx = pd.to_datetime(idx).tz_localize(None)
    except (TypeError, ValueError):
        try:
            idx = pd.to_datetime(idx).tz_convert(None)
        except Exception:
            pass
    points: List[Dict[str, Any]] = []
    for i, px in enumerate(close.tolist()):
        label = idx[i]
        try:
            date = pd.Timestamp(label).strftime("%Y-%m-%d")
        except Exception:
            date = str(label)
        points.append({"date": date, "close": float(px)})
    return points


def merge_quote(*parts: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Fill missing keys from later parts; earlier parts win."""
    out: Dict[str, Any] = {}
    for part in parts:
        if not part:
            continue
        for k, v in part.items():
            if k == "history":
                continue
            if v is None or v == "":
                continue
            if k not in out:
                out[k] = v
    return out


def snapshot_from_metrics(m: Optional[StockMetrics]) -> Dict[str, Any]:
    if m is None:
        return {}
    raw = {
        "ticker": m.ticker,
        "company_name": m.company_name,
        "current_price": m.current_price,
        "previous_close": m.previous_close,
        "day_open": m.day_open,
        "day_high": m.day_high,
        "day_low": m.day_low,
        "week_52_high": m.week_52_high,
        "week_52_low": m.week_52_low,
        "volume": m.volume,
        "avg_volume": m.avg_volume,
        "market_cap": m.market_cap,
        "pe": m.pe,
        "pb": m.pb,
        "dividend_yield_pct": m.dividend_yield_pct,
        "roe_pct": m.roe_pct,
        "return_1y_pct": m.return_1y_pct,
        "currency": "INR" if str(m.ticker).endswith(".NS") else None,
    }
    return finalize_quote(m.ticker, _drop_none(raw), history=None)


def finalize_quote(
    ticker: str,
    quote: Dict[str, Any],
    history: Optional[Sequence[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    price = safe_float(quote.get("current_price"))
    prev = safe_float(quote.get("previous_close"))
    change = None
    change_pct = None
    if price is not None and prev not in (None, 0):
        change = price - prev
        change_pct = (change / prev) * 100.0
    currency = quote.get("currency") or ("INR" if str(ticker).endswith(".NS") else None)
    out = {
        "ticker": ticker,
        "company_name": quote.get("company_name"),
        "currency": currency,
        "current_price": price,
        "previous_close": prev,
        "change": change,
        "change_pct": change_pct,
        "day_open": safe_float(quote.get("day_open")),
        "day_high": safe_float(quote.get("day_high")),
        "day_low": safe_float(quote.get("day_low")),
        "week_52_high": safe_float(quote.get("week_52_high")),
        "week_52_low": safe_float(quote.get("week_52_low")),
        "volume": safe_float(quote.get("volume")),
        "avg_volume": safe_float(quote.get("avg_volume")),
        "market_cap": safe_float(quote.get("market_cap")),
        "pe": safe_float(quote.get("pe")),
        "pb": safe_float(quote.get("pb")),
        "dividend_yield_pct": safe_float(quote.get("dividend_yield_pct")),
        "roe_pct": safe_float(quote.get("roe_pct")),
        "return_1y_pct": safe_float(quote.get("return_1y_pct")),
    }
    if history is not None:
        out["history"] = list(history)
    return out


def fetch_quote(ticker: str, metrics: Optional[StockMetrics] = None) -> Dict[str, Any]:
    """Live quote + 6m history, falling back to NSE then cached metrics.

    History / fast_info first — ``get_info`` is slow and often empty.
    """
    live: Dict[str, Any] = {}
    hist_points: List[Dict[str, Any]] = []

    try:
        import yfinance as yf
    except Exception:
        yf = None  # type: ignore

    symbols: Iterable[str] = yfinance_symbols_for(ticker) if ticker else [ticker]
    if yf is not None:
        for sym in symbols:
            try:
                t = yf.Ticker(sym)
                hist = None
                try:
                    hist = _retry(lambda: t.history(period="6mo", interval="1d"))
                except Exception as e:
                    logger.debug("Quote history failed %s (%s): %s", ticker, sym, e)
                fast = None
                try:
                    fast = t.fast_info
                except Exception:
                    fast = None
                live = merge_quote(quote_from_history(hist), quote_from_fast_info(fast))
                hist_points = history_points(hist)
                if live.get("company_name") is None or live.get("pe") is None:
                    try:
                        info = t.get_info() or {}
                    except Exception:
                        info = {}
                    live = merge_quote(live, quote_from_yf_info(info))
                if live.get("current_price") is not None or hist_points:
                    break
            except Exception as e:
                logger.debug("Quote fetch failed %s via %s: %s", ticker, sym, e)

    if live.get("current_price") is None or live.get("week_52_high") is None:
        live = merge_quote(live, fetch_nse_quote(ticker))
    if not hist_points:
        nse_hist = fetch_nse_history(ticker)
        hist_points = history_points(nse_hist)
        if live.get("current_price") is None:
            live = merge_quote(live, quote_from_history(nse_hist))

    live = merge_quote(live, snapshot_from_metrics(metrics))
    if not live.get("company_name"):
        live["company_name"] = str(ticker).replace(".NS", "").replace(".BO", "")
    return finalize_quote(ticker, live, history=hist_points)


def _drop_none(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}
