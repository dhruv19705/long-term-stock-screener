from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import pandas as pd

from screener.features.fundamentals import safe_float

logger = logging.getLogger("screener.nse_fallback")

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://www.nseindia.com/",
}


def _nse_symbol(canonical: str) -> str:
    return canonical.replace(".NS", "").replace(".BO", "").replace("%26", "&")


def _chart_rows(data: dict) -> List[list]:
    return list(data.get("grapthData") or data.get("graphData") or [])


def history_from_nse_chart(data: dict) -> Optional[pd.Series]:
    """Parse NSE chart JSON into a dated close series."""
    rows = _chart_rows(data)
    if not rows:
        return None
    dates: List[Any] = []
    closes: List[float] = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            continue
        px = safe_float(row[1])
        if px is None:
            continue
        ts = row[0]
        dt = pd.to_datetime(ts, unit="ms", errors="coerce")
        if pd.isna(dt):
            dt = pd.to_datetime(ts, errors="coerce")
        dates.append(dt)
        closes.append(px)
    if not closes:
        return None
    s = pd.Series(closes, index=dates, dtype=float)
    if s.index.notna().any():
        s = s[s.index.notna()]
    return s if not s.empty else None


def parse_nse_quote(data: dict) -> Dict[str, Any]:
    """Extract quote fields from an NSE quote-equity payload."""
    info = data.get("info") or {}
    meta = data.get("metadata") or {}
    price = data.get("priceInfo") or {}
    traded = data.get("securityWiseDP") or {}
    intra = price.get("intraDayHighLow") or {}
    week = price.get("weekHighLow") or {}

    name = info.get("companyName") or meta.get("companyName") or info.get("symbol")
    volume = (
        safe_float(traded.get("quantityTraded"))
        or safe_float(price.get("totalTradedVolume"))
        or safe_float((data.get("preOpenMarket") or {}).get("totalTradedVolume"))
    )
    out: Dict[str, Any] = {
        "company_name": str(name).strip() if name else None,
        "current_price": safe_float(price.get("lastPrice") or price.get("close")),
        "previous_close": safe_float(price.get("previousClose")),
        "day_open": safe_float(price.get("open")),
        "day_high": safe_float(intra.get("max") or price.get("intraDayHigh")),
        "day_low": safe_float(intra.get("min") or price.get("intraDayLow")),
        "week_52_high": safe_float(week.get("max")),
        "week_52_low": safe_float(week.get("min")),
        "volume": volume,
    }
    return {k: v for k, v in out.items() if v is not None}


def fetch_nse_history(canonical: str, days: int = 1260) -> Optional[pd.Series]:
    """Best-effort NSE India historical close when yfinance has no data."""
    try:
        import requests
    except ImportError:
        return None

    sym = _nse_symbol(canonical)
    session = requests.Session()
    session.headers.update(_HEADERS)
    try:
        session.get("https://www.nseindia.com", timeout=10)
        time.sleep(0.3)
        chart_url = f"https://www.nseindia.com/api/chart-daily/equity?symbol={sym}&series=EQ&from=01-01-2020&to=31-12-2030"
        r = session.get(chart_url, timeout=15)
        if r.status_code != 200:
            return None
        closes = history_from_nse_chart(r.json())
        if closes is None or closes.empty:
            return None
        logger.info("NSE fallback OK for %s (%s rows)", canonical, len(closes))
        return closes
    except Exception as e:
        logger.debug("NSE fallback failed %s: %s", canonical, e)
        return None


def fetch_nse_quote(canonical: str) -> Dict[str, Any]:
    """Best-effort last price, ranges, volume, and name from NSE quote API."""
    try:
        import requests
    except ImportError:
        return {}

    sym = _nse_symbol(canonical)
    session = requests.Session()
    session.headers.update(_HEADERS)
    try:
        session.get("https://www.nseindia.com", timeout=10)
        time.sleep(0.25)
        url = f"https://www.nseindia.com/api/quote-equity?symbol={sym}"
        r = session.get(url, timeout=15)
        if r.status_code != 200:
            return {}
        parsed = parse_nse_quote(r.json())
        if parsed:
            logger.info("NSE quote OK for %s", canonical)
        return parsed
    except Exception as e:
        logger.debug("NSE quote failed %s: %s", canonical, e)
        return {}


def fetch_nse_fundamentals(canonical: str) -> dict:
    """Best-effort ROE/ROCE from NSE quote API when yfinance omits them."""
    try:
        import requests
    except ImportError:
        return {}

    sym = _nse_symbol(canonical)
    session = requests.Session()
    session.headers.update(_HEADERS)
    try:
        session.get("https://www.nseindia.com", timeout=10)
        time.sleep(0.25)
        url = f"https://www.nseindia.com/api/quote-equity?symbol={sym}"
        r = session.get(url, timeout=15)
        if r.status_code != 200:
            return {}
        data = r.json()
        meta = data.get("metadata") or {}
        out: dict = {}
        info = data.get("securityInfo") or {}
        roe_raw = info.get("returnOnEquity") or meta.get("returnOnEquity")
        if roe_raw is not None:
            try:
                val = float(roe_raw)
                out["roe_pct"] = val * 100.0 if abs(val) <= 1.5 else val
            except (TypeError, ValueError):
                pass
        return out
    except Exception as e:
        logger.debug("NSE fundamentals failed %s: %s", canonical, e)
        return {}
