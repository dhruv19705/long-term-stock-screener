"""Expand street_consensus.yaml from nifty50 benchmark."""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "screener" / "config"

nifty50 = yaml.safe_load((CONFIG / "nifty50_benchmark.yaml").read_text(encoding="utf-8"))
tickers = {}
for t, spec in (nifty50.get("tickers") or {}).items():
    if int(spec.get("analyst_count") or 0) >= 20:
        tickers[t] = {
            "street": spec["street"],
            "analyst_count": spec["analyst_count"],
            "source": spec.get("source", "consensus"),
        }

out = {"version": "2026-08", "tickers": tickers}
path = CONFIG / "street_consensus.yaml"
with open(path, "w", encoding="utf-8") as f:
    yaml.safe_dump(out, f, sort_keys=False, allow_unicode=True)
print(f"Wrote {len(tickers)} tickers to {path}")
