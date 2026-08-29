"""Audit yfinance data quality across universe."""
from __future__ import annotations

import json
from collections import Counter, defaultdict

from screener.config_loader import all_tickers
from screener.data.fetcher import get_stock_data
from screener.pipeline import run_evaluation, STATE


def main() -> None:
    tickers = all_tickers()
    sources = Counter()
    missing = defaultdict(int)
    anomalies = []

    for t in tickers[:30]:  # sample for speed
        m = get_stock_data(t, use_cache=True)
        sources[m.data_source] += 1
        if m.banking_data_source:
            sources[f"banking:{m.banking_data_source}"] += 1
        for field in ("pe", "pb", "roe_pct", "operating_margin_pct", "debt_to_equity"):
            if getattr(m, field) is None:
                missing[field] += 1
        if m.roe_pct is not None and (m.roe_pct > 80 or m.roe_pct < -50):
            anomalies.append((t, "roe", m.roe_pct))
        if m.debt_to_equity is not None and m.debt_to_equity > 5:
            anomalies.append((t, "de", m.debt_to_equity))

    run_evaluation(sector_filter="all", use_cache=True)
    gq3 = Counter()
    for i in STATE.interps.values():
        for q in i.questions:
            if q.id == "GQ3":
                gq3[q.signal] += 1

    recs = Counter(r.recommendation for r in STATE.scores.values())
    out = {
        "sample_sources": dict(sources),
        "sample_missing": dict(missing),
        "anomalies": anomalies[:10],
        "gq3_signals": dict(gq3),
        "recommendations": dict(recs),
        "kept": len(STATE.metrics),
        "dropped": STATE.dropped,
    }
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
