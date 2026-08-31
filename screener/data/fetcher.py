from __future__ import annotations

import contextlib
import io
import logging
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except Exception as e:  # pragma: no cover
    raise RuntimeError("yfinance is required. pip install -r requirements.txt") from e

from screener.config_loader import (
    analysis_depth_for_ticker,
    bank_cohort,
    load_settings,
    model_sector_for_ticker,
    nifty50_tickers,
    peer_set,
    sector_focus_for_ticker,
    ticker_meta,
    tickers_for_filter,
    yfinance_symbols_for,
)
from screener.data.banking import enrich_banking_metrics
from screener.data.insurance import enrich_insurance_metrics
from screener.data.cache import get_cached_metrics, set_cached_metrics
from screener.data.nse_fallback import fetch_nse_history, fetch_nse_quote
from screener.data.normalize import adjust_debt_for_finance_subsidiary, normalize_debt_to_equity, sanitize_metrics
from screener.data.quote import merge_quote, quote_from_history, quote_from_yf_info
from screener.features.fundamentals import (
    annual_series_ascending,
    cagr_3y_pct,
    credit_growth_yoy,
    extract_latest_period_values,
    extract_latest_single,
    growth_pct,
    margin_trend_3y_pct,
    safe_float,
    to_percent_if_fraction,
)
from screener.models import StockMetrics

logger = logging.getLogger("screener.fetcher")

# yfinance prints "possibly delisted" to stderr for bad/stale symbols
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

_DISPLAY = {
    "banking": "Financial Services",
    "it": "Technology",
    "fmcg": "Consumer Defensive",
    "pharma": "Healthcare",
    "auto": "Consumer Cyclical",
    "energy": "Energy",
    "metals": "Basic Materials",
    "capital_goods": "Industrials",
    "unknown": "Unknown",
}


def _display_for_ticker(ticker: str) -> str:
    meta = ticker_meta(ticker)
    if meta:
        return meta["display_sector"]
    return "Unknown"


def _retry(fn, tries: int = 3, delay: float = 0.6):
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            last = e
            time.sleep(delay * (2**i))
    if last:
        raise last


@contextlib.contextmanager
def _quiet_yfinance():
    """Suppress yfinance stderr spam for missing/stale symbols."""
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        yield


def _returns_from_close(close: pd.Series) -> Dict[str, Optional[float]]:
    out = {
        "return_1m_pct": None,
        "return_3m_pct": None,
        "return_6m_pct": None,
        "return_1y_pct": None,
    }
    if close is None or close.empty:
        return out
    close = close.dropna().astype(float)
    if close.empty:
        return out
    latest = float(close.iloc[-1])

    def ret(days: int) -> Optional[float]:
        if len(close) < days + 1:
            return None
        prev = float(close.iloc[-(days + 1)])
        if prev == 0:
            return None
        return (latest / prev - 1.0) * 100.0

    out["return_1m_pct"] = ret(21)
    out["return_3m_pct"] = ret(63)
    out["return_6m_pct"] = ret(126)
    out["return_1y_pct"] = ret(252)
    return out


def _risk_from_close(
    close: pd.Series, bench_close: Optional[pd.Series]
) -> Dict[str, Optional[float]]:
    result = {
        "ann_volatility": None,
        "beta": None,
        "downside_deviation": None,
        "max_drawdown_1y_pct": None,
        "rs_vs_nifty_pct": None,
    }
    if close is None or len(close.dropna()) < 60:
        return result
    c = close.dropna().astype(float)
    rets = c.pct_change().dropna()
    if rets.empty:
        return result
    vol = float(rets.std() * math.sqrt(252.0))
    result["ann_volatility"] = vol if math.isfinite(vol) else None
    downside = rets[rets < 0]
    if len(downside) >= 20:
        dd = float(downside.std() * math.sqrt(252.0))
        result["downside_deviation"] = dd if math.isfinite(dd) else None
    # 1y max drawdown
    window = c.iloc[-min(len(c), 252) :]
    peak = window.cummax()
    dd_series = window / peak - 1.0
    result["max_drawdown_1y_pct"] = float(dd_series.min() * 100.0)

    if bench_close is not None and not bench_close.empty:
        b = bench_close.dropna().astype(float)
        aligned = pd.concat([c, b], axis=1, join="inner").dropna()
        if len(aligned) >= 60:
            aligned.columns = ["s", "b"]
            sr = aligned["s"].pct_change().dropna()
            br = aligned["b"].pct_change().dropna()
            joined = pd.concat([sr, br], axis=1, join="inner").dropna()
            if len(joined) >= 40:
                joined.columns = ["s", "b"]
                var_b = float(joined["b"].var())
                if var_b > 0:
                    cov = float(joined["s"].cov(joined["b"]))
                    result["beta"] = cov / var_b
                # RS: stock 6m return minus bench 6m
                if len(aligned) >= 127:
                    s_ret = float(aligned["s"].iloc[-1] / aligned["s"].iloc[-127] - 1) * 100
                    b_ret = float(aligned["b"].iloc[-1] / aligned["b"].iloc[-127] - 1) * 100
                    result["rs_vs_nifty_pct"] = s_ret - b_ret
    return result


def _pe_history(close_daily: pd.Series, q_inc: pd.DataFrame, shares: Optional[float]):
    if q_inc is None or q_inc.empty or close_daily is None or close_daily.empty:
        return None, None, None
    if shares is None or shares <= 0:
        return None, None, None
    net_label = None
    for lab in q_inc.index:
        s = str(lab).strip().lower()
        if "net income" in s and "minority" not in s:
            net_label = lab
            break
    if net_label is None:
        return None, None, None
    col_dates = pd.to_datetime(q_inc.columns, errors="coerce")
    ni = pd.Series(
        [safe_float(q_inc.loc[net_label, c]) for c in q_inc.columns], index=col_dates
    ).sort_index().dropna()
    if len(ni) < 4:
        return None, None, None
    ttm = ni.rolling(4, min_periods=4).sum().dropna()
    eps = (ttm / shares).astype(float)
    eps = eps[eps > 0]
    if eps.empty:
        return None, None, None
    # resample weekly
    close_w = close_daily.resample("W").last().dropna()
    if len(close_w) < 52:
        return None, None, None
    union = close_w.index.union(eps.index).sort_values()
    eps_ff = eps.reindex(union).ffill()
    eps_at = eps_ff.reindex(close_w.index, method="ffill")
    pe = (close_w / eps_at).replace([np.inf, -np.inf], np.nan).dropna()
    pe = pe[(pe > 0) & (pe < 800)]
    if len(pe) < 26:
        return None, None, None
    return float(pe.min()), float(pe.max()), float(pe.mean())


_BENCH_CACHE: Dict[str, Optional[pd.Series]] = {}


def _benchmark_close(symbol: str) -> Optional[pd.Series]:
    if symbol in _BENCH_CACHE:
        return _BENCH_CACHE[symbol]
    try:
        hist = _retry(lambda: yf.Ticker(symbol).history(period="5y", interval="1d"))
        if hist is None or hist.empty or "Close" not in hist.columns:
            _BENCH_CACHE[symbol] = None
            return None
        s = hist["Close"].astype(float).dropna()
        s.index = pd.to_datetime(s.index).tz_localize(None)
        _BENCH_CACHE[symbol] = s
        return s
    except Exception as e:
        logger.warning("Benchmark fetch failed %s: %s", symbol, e)
        _BENCH_CACHE[symbol] = None
        return None


def _fetch_inner(ticker: str, yf_symbol: Optional[str] = None) -> StockMetrics:
    meta = ticker_meta(ticker) or {}
    focus = meta.get("sector_focus", sector_focus_for_ticker(ticker))
    display = meta.get("display_sector", _display_for_ticker(ticker))
    model_sector = meta.get("model_sector", model_sector_for_ticker(ticker))
    depth = meta.get("analysis_depth", analysis_depth_for_ticker(ticker))
    cohort = meta.get("bank_cohort") or (bank_cohort(ticker) if focus == "banking" else None)
    cyclical = bool(meta.get("cyclical", False))
    settings = load_settings()
    bench_sym = settings.get("benchmark_nifty", "^NSEI")
    min_rows = int(settings.get("min_price_history_rows", 20))

    sym = yf_symbol or ticker
    t = yf.Ticker(sym)
    info: dict = {}
    try:
        with _quiet_yfinance():
            info = _retry(lambda: t.get_info() or {})
    except Exception:
        info = {}

    pe = safe_float(info.get("trailingPE") or info.get("forwardPE"))
    pb = safe_float(info.get("priceToBook"))
    peg = safe_float(info.get("pegRatio"))
    ev_to_ebitda = safe_float(info.get("enterpriseToEbitda"))
    market_cap = safe_float(info.get("marketCap"))

    roe_pct = to_percent_if_fraction(safe_float(info.get("returnOnEquity")), 100)
    roa_pct = to_percent_if_fraction(safe_float(info.get("returnOnAssets")), 50)
    profit_margin_pct = to_percent_if_fraction(safe_float(info.get("profitMargins")), 100)
    operating_margin_pct = to_percent_if_fraction(safe_float(info.get("operatingMargins")), 100)
    ebitda_margin_pct = to_percent_if_fraction(safe_float(info.get("ebitdaMargins")), 100)
    debt_to_equity = normalize_debt_to_equity(safe_float(info.get("debtToEquity")))
    debt_to_equity = adjust_debt_for_finance_subsidiary(ticker, debt_to_equity)
    interest_coverage = safe_float(info.get("interestCoverage"))

    try:
        income_stmt = t.income_stmt
    except Exception:
        income_stmt = pd.DataFrame()
    try:
        balance_sheet = t.balance_sheet
    except Exception:
        balance_sheet = pd.DataFrame()
    try:
        cashflow = t.cashflow
    except Exception:
        cashflow = pd.DataFrame()
    try:
        q_inc = t.quarterly_income_stmt
    except Exception:
        q_inc = pd.DataFrame()

    net_latest, net_prev, _ = extract_latest_period_values(
        income_stmt, ["Net Income", "NetIncome", "Net income"]
    )
    rev_latest, rev_prev, _ = extract_latest_period_values(
        income_stmt, ["Total Revenue", "TotalRevenue", "Revenue"]
    )
    profit_growth_pct = growth_pct(net_latest, net_prev)
    revenue_growth_pct = growth_pct(rev_latest, rev_prev)

    total_assets = extract_latest_single(balance_sheet, ["Total Assets", "TotalAssets"])
    asset_turnover = None
    if rev_latest is not None and total_assets not in (None, 0):
        asset_turnover = rev_latest / total_assets

    oi = extract_latest_single(income_stmt, ["Operating Income", "EBIT", "OperatingIncome"])
    equity = extract_latest_single(
        balance_sheet,
        ["Total Stockholder Equity", "TotalEquity", "Stockholders' equity"],
    )
    debt = extract_latest_single(
        balance_sheet, ["Total Debt", "totalDebt", "Long Term Debt"]
    )
    invested = None
    if equity is not None and debt is not None:
        invested = equity + debt
    elif total_assets is not None:
        invested = total_assets
    roce_pct = None
    if oi is not None and invested not in (None, 0):
        roce_pct = to_percent_if_fraction(oi / invested, 100)

    if roe_pct is None and net_latest is not None and equity not in (None, 0):
        roe_pct = to_percent_if_fraction(net_latest / equity, 100)

    from screener.data.nse_fallback import fetch_nse_fundamentals

    if roe_pct is None or (ticker in nifty50_tickers() and roce_pct is None):
        nse_fund = fetch_nse_fundamentals(ticker)
        if roe_pct is None and nse_fund.get("roe_pct") is not None:
            roe_pct = nse_fund["roe_pct"]
        if nse_fund.get("roce_pct") is not None and roce_pct is None:
            roce_pct = nse_fund["roce_pct"]

    gnpa = to_percent_if_fraction(
        safe_float(
            info.get("grossNonPerformingAssets")
            or info.get("grossNpa")
            or info.get("grossNPA")
        ),
        10,
    )
    nnpa = to_percent_if_fraction(
        safe_float(info.get("netNonPerformingAssets") or info.get("netNpa") or info.get("nnpa")),
        10,
    )
    nim = to_percent_if_fraction(
        safe_float(info.get("netInterestMargin") or info.get("NIM")), 10
    )
    car = to_percent_if_fraction(
        safe_float(info.get("capitalAdequacyRatio") or info.get("CAR") or info.get("capitalAdequacy")),
        100,
    )

    rev_series = annual_series_ascending(income_stmt, ["Total Revenue", "TotalRevenue", "Revenue"])
    ni_series = annual_series_ascending(income_stmt, ["Net Income", "NetIncome", "Net income"])
    revenue_cagr_3y_pct = cagr_3y_pct(rev_series)
    profit_cagr_3y_pct = cagr_3y_pct(ni_series)
    operating_margin_trend_pct = margin_trend_3y_pct(income_stmt)
    credit_growth_pct = credit_growth_yoy(balance_sheet)
    free_cash_flow_ttm = extract_latest_single(cashflow, ["Free Cash Flow", "FreeCashFlow"])
    dy = safe_float(info.get("dividendYield"))
    dividend_yield_pct = dy * 100.0 if dy is not None and abs(dy) <= 1.0 else dy

    fcf_yield_pct = None
    if free_cash_flow_ttm is not None and market_cap not in (None, 0):
        fcf_yield_pct = (free_cash_flow_ttm / market_cap) * 100.0

    # Single price history pull
    price_history_rows = 0
    close = pd.Series(dtype=float)
    hist = None
    try:
        with _quiet_yfinance():
            hist = _retry(lambda: t.history(period="5y", interval="1d"))
        if hist is not None and not hist.empty and "Close" in hist.columns:
            close = hist["Close"].astype(float).dropna()
            close.index = pd.to_datetime(close.index).tz_localize(None)
            price_history_rows = int(len(close))
    except Exception as e:
        logger.warning("History failed %s (%s): %s", ticker, sym, e)

    bench = _benchmark_close(bench_sym)
    data_source_hint = "yfinance"
    if price_history_rows < min_rows:
        nse_close = fetch_nse_history(ticker)
        if nse_close is not None and len(nse_close) >= min_rows:
            close = nse_close
            close.index = pd.to_datetime(close.index).tz_localize(None)
            price_history_rows = int(len(close))
            data_source_hint = "nse_fallback"

    quote = merge_quote(quote_from_yf_info(info), quote_from_history(hist if hist is not None else close))
    if quote.get("current_price") is None or quote.get("week_52_high") is None:
        quote = merge_quote(quote, fetch_nse_quote(ticker))

    rets = _returns_from_close(close)
    risk = _risk_from_close(close, bench)

    shares = safe_float(info.get("sharesOutstanding") or info.get("impliedSharesOutstanding"))
    pe_lo, pe_hi, pe_mean = _pe_history(close, q_inc, shares)

    m = StockMetrics(
        ticker=ticker,
        sector=display,
        sector_focus=focus,
        model_sector=model_sector,
        analysis_depth=depth,
        bank_cohort=cohort,
        cyclical=cyclical,
        pe=pe,
        pb=pb,
        peg=peg,
        ev_to_ebitda=ev_to_ebitda,
        market_cap=market_cap,
        company_name=quote.get("company_name"),
        current_price=quote.get("current_price"),
        previous_close=quote.get("previous_close"),
        day_open=quote.get("day_open"),
        day_high=quote.get("day_high"),
        day_low=quote.get("day_low"),
        week_52_high=quote.get("week_52_high"),
        week_52_low=quote.get("week_52_low"),
        volume=quote.get("volume"),
        avg_volume=quote.get("avg_volume"),
        roe_pct=roe_pct,
        roa_pct=roa_pct,
        profit_margin_pct=profit_margin_pct,
        operating_margin_pct=operating_margin_pct,
        ebitda_margin_pct=ebitda_margin_pct,
        debt_to_equity=debt_to_equity,
        interest_coverage=interest_coverage,
        profit_growth_pct=profit_growth_pct,
        revenue_growth_pct=revenue_growth_pct,
        return_1m_pct=rets["return_1m_pct"],
        return_3m_pct=rets["return_3m_pct"],
        return_6m_pct=rets["return_6m_pct"],
        return_1y_pct=rets["return_1y_pct"],
        pe_hist_low=pe_lo,
        pe_hist_high=pe_hi,
        pe_hist_mean=pe_mean,
        gnpa_pct=gnpa,
        nnpa_pct=nnpa,
        nim_pct=nim,
        car_pct=car,
        asset_turnover=asset_turnover,
        roce_pct=roce_pct,
        revenue_cagr_3y_pct=revenue_cagr_3y_pct,
        profit_cagr_3y_pct=profit_cagr_3y_pct,
        operating_margin_trend_pct=operating_margin_trend_pct,
        credit_growth_pct=credit_growth_pct,
        free_cash_flow_ttm=free_cash_flow_ttm,
        dividend_yield_pct=dividend_yield_pct,
        fcf_yield_pct=fcf_yield_pct,
        ann_volatility=risk["ann_volatility"],
        beta=risk["beta"],
        downside_deviation=risk["downside_deviation"],
        max_drawdown_1y_pct=risk["max_drawdown_1y_pct"],
        rs_vs_nifty_pct=risk["rs_vs_nifty_pct"],
        price_history_rows=price_history_rows,
        fetch_failed=price_history_rows < min_rows and pe is None and pb is None,
        data_source=data_source_hint if data_source_hint != "yfinance" else "yfinance",
    )
    if data_source_hint == "nse_fallback":
        m.data_source = "mixed"
    return sanitize_metrics(enrich_insurance_metrics(enrich_banking_metrics(m)))


def _fetch_best(ticker: str) -> StockMetrics:
    """Try alias symbols, then NSE fallback inside _fetch_inner."""
    best: Optional[StockMetrics] = None
    for yf_sym in yfinance_symbols_for(ticker):
        try:
            m = _fetch_inner(ticker, yf_sym)
            if best is None or m.price_history_rows > best.price_history_rows:
                best = m
            if m.price_history_rows >= int(load_settings().get("min_price_history_rows", 20)):
                return m
        except Exception as e:
            logger.warning("Fetch attempt failed %s via %s: %s", ticker, yf_sym, e)
    if best is not None:
        return best
    raise RuntimeError(f"All fetch attempts failed for {ticker}")


def _apply_ticker_meta(m: StockMetrics) -> StockMetrics:
    """Ensure universe metadata is current (fixes stale cache missing depth/model)."""
    meta = ticker_meta(m.ticker) or {}
    if not meta:
        return m
    d = m.to_dict()
    d["sector_focus"] = meta.get("sector_focus", d.get("sector_focus"))
    d["model_sector"] = meta.get("model_sector", d.get("model_sector", "UNKNOWN"))
    d["analysis_depth"] = meta.get("analysis_depth", d.get("analysis_depth", "standard"))
    d["cyclical"] = bool(meta.get("cyclical", d.get("cyclical", False)))
    if meta.get("display_sector"):
        d["sector"] = meta["display_sector"]
    if meta.get("bank_cohort"):
        d["bank_cohort"] = meta["bank_cohort"]
    m = StockMetrics(**d)
    if m.sector_focus == "banking":
        m = enrich_banking_metrics(m)
    elif m.sector_focus == "insurance":
        m = enrich_insurance_metrics(m)
    return sanitize_metrics(m)


def get_stock_data(ticker: str, use_cache: bool = True) -> StockMetrics:
    settings = load_settings()
    min_rows = int(settings.get("min_price_history_rows", 20))
    if use_cache:
        cached = get_cached_metrics(ticker)
        if cached:
            try:
                m = StockMetrics(
                    **{k: cached[k] for k in StockMetrics.__dataclass_fields__ if k in cached}
                )
                # Refetch if cache has empty/broken price history
                if m.fetch_failed or m.price_history_rows < min_rows:
                    logger.info("Cache stale for %s (%s rows), refetching", ticker, m.price_history_rows)
                else:
                    m = _apply_ticker_meta(m)
                    set_cached_metrics(ticker, m.to_dict())
                    return m
            except Exception:
                pass
    try:
        m = _apply_ticker_meta(_fetch_best(ticker))
        set_cached_metrics(ticker, m.to_dict())
        return m
    except Exception as e:
        logger.warning("Fetch failed %s: %s", ticker, e)
        focus = sector_focus_for_ticker(ticker)
        meta = ticker_meta(ticker) or {}
        return StockMetrics(
            ticker=ticker,
            sector=meta.get("display_sector", _DISPLAY.get(focus, "Unknown")),
            sector_focus=focus,
            model_sector=meta.get("model_sector", "UNKNOWN"),
            analysis_depth=meta.get("analysis_depth", "standard"),
            bank_cohort=bank_cohort(ticker) if focus == "banking" else None,
            fetch_failed=True,
        )


def fetch_all_metrics(
    sector_filter: str = "all",
    max_workers: Optional[int] = None,
    use_cache: bool = True,
) -> Dict[str, StockMetrics]:
    settings = load_settings()
    workers = max_workers or int(settings.get("max_workers", 8))
    tickers = tickers_for_filter(sector_filter)
    results: Dict[str, StockMetrics] = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(get_stock_data, t, use_cache): t for t in tickers}
        for fut in as_completed(futs):
            t = futs[fut]
            try:
                results[t] = fut.result()
                logger.info("Fetched %s (%s)", t, results[t].sector_focus)
            except Exception as e:
                logger.warning("Worker failed %s: %s", t, e)
                focus = sector_focus_for_ticker(t)
                meta = ticker_meta(t) or {}
                results[t] = StockMetrics(
                    ticker=t,
                    sector=meta.get("display_sector", _DISPLAY.get(focus, "Unknown")),
                    sector_focus=focus,
                    model_sector=meta.get("model_sector", "UNKNOWN"),
                    fetch_failed=True,
                )
    return results
