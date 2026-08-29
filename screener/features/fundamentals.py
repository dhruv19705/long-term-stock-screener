from __future__ import annotations

import math
from typing import Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd


def safe_float(x: object) -> Optional[float]:
    try:
        if x is None:
            return None
        val = float(x)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    except Exception:
        return None


def to_percent_if_fraction(x: Optional[float], upper: float) -> Optional[float]:
    if x is None:
        return None
    if abs(x) <= 1.0 and upper <= 100:
        return x * 100.0
    return x


def growth_pct(latest: Optional[float], prev: Optional[float]) -> Optional[float]:
    if latest is None or prev is None or prev == 0:
        return None
    return ((latest - prev) / abs(prev)) * 100.0


def is_date_like(labels: Iterable[object]) -> bool:
    try:
        parsed = pd.to_datetime(list(labels), errors="coerce", format="mixed")
    except TypeError:
        parsed = pd.to_datetime(list(labels), errors="coerce")
    if len(parsed) == 0:
        return False
    return float(pd.Series(parsed).notna().mean()) >= 0.5


def extract_latest_period_values(
    df: pd.DataFrame, line_item_regexes: List[str]
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if df is None or df.empty:
        return None, None, None
    cols_are_dates = is_date_like(df.columns)
    idx_are_dates = is_date_like(df.index)

    def match_label(labels: Iterable[object]) -> Optional[str]:
        for lab in labels:
            s = str(lab).strip().lower()
            for rx in line_item_regexes:
                if rx.lower() in s:
                    return str(lab)
        return None

    if cols_are_dates and not idx_are_dates:
        item_label = match_label(df.index)
        if item_label is None:
            return None, None, None
        date_cols = list(df.columns)
        parsed = pd.to_datetime(date_cols, errors="coerce")
        order = np.argsort(parsed.values)
        sorted_cols = [date_cols[i] for i in order]
        last_cols = sorted_cols[-3:][::-1]
        values = [safe_float(df.loc[item_label, c]) for c in last_cols]
        latest, prev1, prev2 = (values + [None, None, None])[:3]
        return latest, prev1, prev2

    if idx_are_dates and not cols_are_dates:
        item_label = match_label(df.columns)
        if item_label is None:
            return None, None, None
        date_idx = list(df.index)
        parsed = pd.to_datetime(date_idx, errors="coerce")
        order = np.argsort(parsed.values)
        sorted_idx = [date_idx[i] for i in order]
        last_rows = sorted_idx[-3:][::-1]
        values = [safe_float(df.loc[r, item_label]) for r in last_rows]
        latest, prev1, prev2 = (values + [None, None, None])[:3]
        return latest, prev1, prev2

    return None, None, None


def extract_latest_single(df: pd.DataFrame, regexes: List[str]) -> Optional[float]:
    latest, _, _ = extract_latest_period_values(df, regexes)
    return latest


def annual_series_ascending(df: pd.DataFrame, regexes: List[str]) -> List[float]:
    if df is None or df.empty:
        return []
    item_label = None
    for lab in df.index:
        s = str(lab).strip().lower()
        for rx in regexes:
            if rx.lower() in s:
                item_label = str(lab)
                break
        if item_label:
            break
    if item_label is None:
        return []
    parsed = pd.to_datetime(df.columns, errors="coerce")
    order = np.argsort(parsed.values)
    out: List[float] = []
    for i in order:
        v = safe_float(df.loc[item_label, df.columns[i]])
        if v is not None:
            out.append(v)
    return out


def cagr_3y_pct(values_asc: List[float]) -> Optional[float]:
    if len(values_asc) < 4:
        return None
    v0, v3 = values_asc[-4], values_asc[-1]
    if v0 <= 0 or v3 <= 0:
        return None
    try:
        return ((v3 / v0) ** (1.0 / 3.0) - 1.0) * 100.0
    except Exception:
        return None


def margin_trend_3y_pct(income_stmt: pd.DataFrame) -> Optional[float]:
    if income_stmt is None or income_stmt.empty:
        return None

    def match(labels: Iterable[object], regexes: List[str]) -> Optional[str]:
        for lab in labels:
            s = str(lab).strip().lower()
            for rx in regexes:
                if rx.lower() in s:
                    return str(lab)
        return None

    oi_lab = match(income_stmt.index, ["Operating Income", "EBIT", "OperatingIncome"])
    rev_lab = match(income_stmt.index, ["Total Revenue", "TotalRevenue", "Revenue"])
    if oi_lab is None or rev_lab is None:
        return None
    parsed = pd.to_datetime(income_stmt.columns, errors="coerce")
    order = np.argsort(parsed.values)
    margins: List[float] = []
    for i in order:
        c = income_stmt.columns[i]
        oi = safe_float(income_stmt.loc[oi_lab, c])
        rv = safe_float(income_stmt.loc[rev_lab, c])
        if oi is None or rv is None or rv == 0:
            continue
        margins.append((oi / abs(rv)) * 100.0)
    if len(margins) < 4:
        return None
    return margins[-1] - margins[-4]


def credit_growth_yoy(balance_sheet: pd.DataFrame) -> Optional[float]:
    if balance_sheet is None or balance_sheet.empty:
        return None
    for patterns in (["Total Loans", "Loans And Advances", "Loans", "Net Loans", "Loan"],):
        series = annual_series_ascending(balance_sheet, patterns)
        if len(series) >= 2:
            return growth_pct(series[-1], series[-2])
    return None
