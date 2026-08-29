"""Optional street-consensus safety overlay for mega/large caps."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

import yaml

from screener.config_loader import nifty50_tickers

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "street_consensus.yaml"

BEARISH = {"SELL", "AVOID"}
BULLISH = {"BUY", "STRONG BUY"}


@lru_cache(maxsize=1)
def _load_consensus() -> Dict[str, dict]:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("tickers") or {}


def street_consensus_for(ticker: str) -> Optional[dict]:
    return _load_consensus().get(ticker)


NEUTRAL = {"HOLD"}


def apply_street_overlay(action: str, ticker: str, quality_grade: str | None = None) -> str:
    """
    Street consensus overlay for well-covered Nifty 50 names.
    Downgrades false bearish calls; calibrates bullish/neutral vs street.
    Never auto-upgrades to STRONG BUY.
    """
    entry = street_consensus_for(ticker)
    if not entry:
        return action
    street = str(entry.get("street", "")).upper()
    analysts = int(entry.get("analyst_count") or 0)
    if analysts < 20:
        return action

    in_index = ticker in nifty50_tickers()

    # Downgrade path: screener bearish vs street bullish
    if street in BULLISH and action in BEARISH:
        if action == "SELL":
            return "AVOID"
        return "HOLD"

    if not in_index:
        return action

    # Calibrate over-promoted index names vs street HOLD
    if street in NEUTRAL and action in BULLISH and analysts >= 20:
        if action == "STRONG BUY":
            return "HOLD"
        return "HOLD"

    # Upgrade path: HOLD vs street BUY/STRONG BUY for quality names
    if (
        action == "HOLD"
        and street in BULLISH
        and quality_grade in ("A", "B")
        and analysts >= 20
    ):
        return "BUY"

    return action
