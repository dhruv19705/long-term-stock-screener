from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

import numpy as np

from screener.config_loader import load_settings


def winsorize(values: Sequence[Optional[float]], low: float = 0.05, high: float = 0.95) -> List[Optional[float]]:
    arr = [v for v in values if v is not None and np.isfinite(v)]
    if len(arr) < 3:
        return list(values)
    lo = float(np.quantile(arr, low))
    hi = float(np.quantile(arr, high))
    out: List[Optional[float]] = []
    for v in values:
        if v is None or not np.isfinite(v):
            out.append(None)
        else:
            out.append(float(min(max(v, lo), hi)))
    return out


def zscore_map(tickers: List[str], values: List[Optional[float]], invert: bool = False) -> Dict[str, Optional[float]]:
    settings = load_settings()
    w = winsorize(values, settings.get("winsor_low", 0.05), settings.get("winsor_high", 0.95))
    valid = [v for v in w if v is not None]
    if len(valid) < 2:
        return {t: None for t in tickers}
    mu = float(np.mean(valid))
    sd = float(np.std(valid, ddof=0))
    if sd < 1e-9:
        return {t: 0.0 for t in tickers}
    out: Dict[str, Optional[float]] = {}
    for t, v in zip(tickers, w):
        if v is None:
            out[t] = None
        else:
            z = (v - mu) / sd
            out[t] = float(-z if invert else z)
    return out


def percentile_rank(
    tickers: List[str],
    values: List[Optional[float]],
    higher_better: bool = True,
    winsor: bool = True,
) -> Dict[str, Optional[float]]:
    """Return percentile 0-100 within peer set; optional winsorization reduces outlier distortion."""
    if winsor and len([v for v in values if v is not None]) >= 5:
        settings = load_settings()
        values = winsorize(values, settings.get("winsor_low", 0.05), settings.get("winsor_high", 0.95))
    pairs = [(t, v) for t, v in zip(tickers, values) if v is not None and np.isfinite(v)]
    if len(pairs) < 2:
        return {t: None for t in tickers}
    vals = sorted(pairs, key=lambda x: x[1], reverse=not higher_better)
    n = len(vals)
    ranks = {t: (i / (n - 1)) * 100.0 for i, (t, _) in enumerate(vals)}
    return {t: ranks.get(t) for t in tickers}


def soft_score_higher(value: Optional[float], good: float, bad: float) -> Optional[float]:
    """Map value to 0..1 where higher is better; good/bad thresholds."""
    if value is None or not np.isfinite(value):
        return None
    if good == bad:
        return 1.0 if value >= good else 0.0
    # linear between bad and good
    if good > bad:
        return float(np.clip((value - bad) / (good - bad), 0.0, 1.0))
    return float(np.clip((bad - value) / (bad - good), 0.0, 1.0))


def soft_score_lower(value: Optional[float], good: float, bad: float) -> Optional[float]:
    """Lower is better."""
    return soft_score_higher(None if value is None else -value, -good, -bad)


def weighted_mean(parts: Dict[str, Optional[float]], weights: Dict[str, float]) -> tuple[float, Dict[str, float]]:
    used = {}
    num = 0.0
    den = 0.0
    for k, w in weights.items():
        v = parts.get(k)
        if v is None or not np.isfinite(v):
            continue
        num += w * float(v)
        den += w
        used[k] = float(v)
    if den <= 0:
        return 0.0, used
    return num / den, used


def median_or_none(vals: Iterable[Optional[float]]) -> Optional[float]:
    arr = [v for v in vals if v is not None and np.isfinite(v)]
    if not arr:
        return None
    return float(np.median(arr))
