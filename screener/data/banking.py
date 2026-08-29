from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional, Tuple

from screener.config_loader import load_banking_metrics
from screener.features.fundamentals import safe_float, to_percent_if_fraction
from screener.models import StockMetrics


def banking_data_stale() -> bool:
    meta = load_banking_metrics().get("_meta") or {}
    as_of = meta.get("as_of")
    if not as_of:
        return True
    try:
        dt = datetime.strptime(str(as_of), "%Y-%m-%d")
        return (datetime.now(UTC) - dt.replace(tzinfo=UTC)).days > 120
    except Exception:
        return False


def enrich_banking_metrics(m: StockMetrics) -> StockMetrics:
    """
    Fill GNPA/NNPA/CAR/NIM from curated JSON when yfinance is missing.
    Sets banking_data_source and may bump data_source to mixed/curated.
    """
    if m.sector_focus != "banking":
        return m

    curated = load_banking_metrics().get(m.ticker) or {}
    sources = []

    def fill_curated(attr: str, keys: Tuple[str, ...]) -> Optional[float]:
        """Curated banking JSON stores ratios already in percent (e.g. 0.40 = 0.40%)."""
        nonlocal sources
        for k in keys:
            val = safe_float(curated.get(k))
            if val is not None:
                sources.append("curated")
                return val
        return None

    def fill(attr: str, keys: Tuple[str, ...], upper: float) -> Optional[float]:
        nonlocal sources
        curated_val = fill_curated(attr, keys)
        if curated_val is not None:
            return curated_val
        current = getattr(m, attr)
        if current is not None:
            sources.append("yfinance")
            return to_percent_if_fraction(current, upper)
        return None

    gnpa = fill("gnpa_pct", ("gnpa_pct",), 10)
    nnpa = fill("nnpa_pct", ("nnpa_pct",), 10)
    car = fill("car_pct", ("car_pct",), 100)
    nim = fill("nim_pct", ("nim_pct",), 10)

    used = set(sources)
    if "curated" in used and "yfinance" in used:
        banking_src = "mixed"
        data_source = "mixed"
    elif "curated" in used:
        banking_src = "curated"
        data_source = "curated" if m.data_source == "yfinance" else m.data_source
    elif "yfinance" in used:
        banking_src = "yfinance"
        data_source = m.data_source
    else:
        banking_src = "proxy"
        data_source = "proxy"

    return StockMetrics(
        **{
            **m.to_dict(),
            "gnpa_pct": gnpa,
            "nnpa_pct": nnpa,
            "car_pct": car,
            "nim_pct": nim,
            "banking_data_source": banking_src,
            "data_source": data_source,
        }
    )
