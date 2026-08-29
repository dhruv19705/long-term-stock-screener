from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional, Tuple

from screener.config_loader import load_insurance_metrics
from screener.features.fundamentals import safe_float
from screener.models import StockMetrics


def insurance_data_stale() -> bool:
    meta = load_insurance_metrics().get("_meta") or {}
    as_of = meta.get("as_of")
    if not as_of:
        return True
    try:
        dt = datetime.strptime(str(as_of), "%Y-%m-%d")
        return (datetime.now(UTC) - dt.replace(tzinfo=UTC)).days > 120
    except Exception:
        return True


def enrich_insurance_metrics(m: StockMetrics) -> StockMetrics:
    """Fill solvency/VNB/persistency from curated JSON for life insurers."""
    if m.sector_focus != "insurance":
        return m

    curated = load_insurance_metrics().get(m.ticker) or {}
    if not curated:
        return m

    def pick(*keys: str) -> Optional[float]:
        for k in keys:
            val = safe_float(curated.get(k))
            if val is not None:
                return val
        return None

    solvency = pick("solvency_ratio_pct", "solvency_pct")
    vnb = pick("vnb_margin_pct", "vnb_margin")
    persistency = pick("persistency_13m_pct", "persistency_13m")
    aum_growth = pick("aum_growth_pct", "aum_growth")

    data_source = "curated" if any(x is not None for x in (solvency, vnb, persistency, aum_growth)) else m.data_source

    return StockMetrics(
        **{
            **m.to_dict(),
            "solvency_ratio_pct": solvency,
            "vnb_margin_pct": vnb,
            "persistency_13m_pct": persistency,
            "aum_growth_pct": aum_growth,
            "data_source": data_source if data_source != "yfinance" else m.data_source,
        }
    )
