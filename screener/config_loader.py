from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

CONFIG_DIR = Path(__file__).resolve().parent / "config"

# Maps bucket key -> sector_focus id
BUCKET_KEYS = [
    "banking",
    "insurance",
    "it",
    "fmcg",
    "pharma",
    "auto",
    "energy",
    "metals",
    "capital_goods",
]

# Maps sector_filter API values to bucket keys
FILTER_TO_BUCKETS: Dict[str, List[str]] = {
    "all": BUCKET_KEYS,
    "both": ["banking", "it"],
    "banking": ["banking"],
    "insurance": ["insurance"],
    "it": ["it"],
    "fmcg": ["fmcg"],
    "pharma": ["pharma"],
    "auto": ["auto"],
    "energy": ["energy"],
    "metals": ["metals"],
    "capital_goods": ["capital_goods"],
    "defensive": ["fmcg", "pharma"],
    "cyclical": ["auto", "energy", "metals", "capital_goods"],
    "no_financials": ["it", "fmcg", "pharma", "auto", "energy", "metals", "capital_goods"],
}


def _load_yaml(name: str) -> Any:
    path = CONFIG_DIR / name
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_json(name: str) -> Any:
    path = CONFIG_DIR / name
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_settings() -> Dict[str, Any]:
    return _load_yaml("settings.yaml")


@lru_cache(maxsize=1)
def load_universe() -> Dict[str, Any]:
    return _load_yaml("universe.yaml")


@lru_cache(maxsize=1)
def load_banking_metrics() -> Dict[str, Any]:
    return _load_json("banking_metrics.json")


@lru_cache(maxsize=1)
def load_user_questionnaire() -> Dict[str, Any]:
    return _load_yaml("user_questionnaire.yaml")


@lru_cache(maxsize=1)
def load_risk_profile_matrix() -> Dict[str, Any]:
    return _load_yaml("risk_profile_matrix.yaml")


@lru_cache(maxsize=1)
def load_banking_risk_questions() -> Dict[str, Any]:
    return _load_yaml("banking_risk_questions.yaml")


@lru_cache(maxsize=1)
def load_it_risk_questions() -> Dict[str, Any]:
    return _load_yaml("it_risk_questions.yaml")


@lru_cache(maxsize=1)
def load_insurance_risk_questions() -> Dict[str, Any]:
    return _load_yaml("insurance_risk_questions.yaml")


@lru_cache(maxsize=1)
def load_generic_risk_questions() -> Dict[str, Any]:
    return _load_yaml("generic_risk_questions.yaml")


@lru_cache(maxsize=1)
def load_sector_weights() -> Dict[str, Any]:
    return _load_yaml("sector_weights.yaml")


@lru_cache(maxsize=1)
def load_sector_risk_overrides() -> Dict[str, Any]:
    return _load_yaml("sector_risk_overrides.yaml")


@lru_cache(maxsize=1)
def load_debt_adjustments() -> Dict[str, Any]:
    return _load_yaml("debt_adjustments.yaml")


@lru_cache(maxsize=1)
def load_hard_gates() -> Dict[str, Any]:
    return _load_yaml("hard_gates.yaml")


@lru_cache(maxsize=1)
def load_valuation_bands() -> Dict[str, Any]:
    return _load_yaml("valuation_bands.yaml")


@lru_cache(maxsize=1)
def load_insurance_metrics() -> Dict[str, Any]:
    return _load_json("insurance_metrics.json")


@lru_cache(maxsize=1)
def load_golden_set() -> Dict[str, Any]:
    return _load_yaml("golden_set.yaml")


@lru_cache(maxsize=1)
def load_nifty50_benchmark() -> Dict[str, Any]:
    try:
        return _load_yaml("nifty50_benchmark.yaml")
    except Exception:
        return {"tickers": {}}


@lru_cache(maxsize=1)
def load_nifty_next50_benchmark() -> Dict[str, Any]:
    try:
        return _load_yaml("nifty_next50_benchmark.yaml")
    except Exception:
        return {"tickers": {}}


@lru_cache(maxsize=1)
def nifty50_tickers() -> frozenset:
    return frozenset((load_nifty50_benchmark().get("tickers") or {}).keys())


def load_benchmark_suite(suite: str) -> Dict[str, dict]:
    """Return tickers dict for suite: nifty50, nifty_next50, golden, all."""
    if suite == "nifty50":
        return load_nifty50_benchmark().get("tickers") or {}
    if suite == "nifty_next50":
        return load_nifty_next50_benchmark().get("tickers") or {}
    if suite == "golden":
        return load_golden_set().get("tickers") or {}
    if suite == "all":
        merged: Dict[str, dict] = {}
        for loader in (load_golden_set, load_nifty50_benchmark, load_nifty_next50_benchmark):
            merged.update(loader().get("tickers") or {})
        return merged
    return load_nifty50_benchmark().get("tickers") or {}


@lru_cache(maxsize=1)
def load_ticker_aliases() -> Dict[str, Any]:
    try:
        return _load_yaml("ticker_aliases.yaml")
    except Exception:
        return {"aliases": {}, "fallbacks": {}}


def yfinance_symbols_for(ticker: str) -> List[str]:
    """Return ordered yfinance symbols to try for a canonical universe ticker."""
    cfg = load_ticker_aliases()
    aliases = cfg.get("aliases") or {}
    fallbacks = cfg.get("fallbacks") or {}
    if ticker in fallbacks:
        syms = list(fallbacks[ticker])
    elif ticker in aliases:
        syms = [aliases[ticker]]
    else:
        syms = [ticker]
    out: List[str] = []
    for s in [ticker] + syms:
        if s and s not in out:
            out.append(s)
    return out


def _build_ticker_index() -> Dict[str, Dict[str, Any]]:
    """ticker -> {bucket, model_sector, display_sector, analysis_depth, cyclical, bank_cohort?}"""
    u = load_universe()
    idx: Dict[str, Dict[str, Any]] = {}

    # banking
    b = u["banking"]
    meta = {
        "bucket": "banking",
        "sector_focus": "banking",
        "model_sector": b["model_sector"],
        "display_sector": b["display_sector"],
        "analysis_depth": b["analysis_depth"],
        "cyclical": b.get("cyclical", False),
    }
    for t in b.get("private", []):
        idx[t] = {**meta, "bank_cohort": "private"}
    for t in b.get("psu", []):
        idx[t] = {**meta, "bank_cohort": "psu"}

    for bucket in BUCKET_KEYS:
        if bucket == "banking":
            continue
        block = u.get(bucket, {})
        if not block:
            continue
        meta = {
            "bucket": bucket,
            "sector_focus": bucket,
            "model_sector": block.get("model_sector", bucket.upper()),
            "display_sector": block.get("display_sector", "Unknown"),
            "analysis_depth": block.get("analysis_depth", "standard"),
            "cyclical": block.get("cyclical", False),
            "bank_cohort": None,
        }
        for t in block.get("tickers", []):
            idx[t] = dict(meta)

    return idx


@lru_cache(maxsize=1)
def ticker_index() -> Dict[str, Dict[str, Any]]:
    return _build_ticker_index()


def banking_tickers() -> List[str]:
    idx = ticker_index()
    return [t for t, m in idx.items() if m["sector_focus"] == "banking"]


def it_tickers() -> List[str]:
    idx = ticker_index()
    return [t for t, m in idx.items() if m["sector_focus"] == "it"]


def insurance_tickers() -> List[str]:
    idx = ticker_index()
    return [t for t, m in idx.items() if m["sector_focus"] == "insurance"]


def _bucket_tickers(sector_focus: str) -> List[str]:
    idx = ticker_index()
    return [t for t, m in idx.items() if m["sector_focus"] == sector_focus]


def _cap_split_peer_set(
    ticker: str,
    all_peers: List[str],
    metrics_by_ticker: Optional[Dict[str, Any]],
    cohort_large: str,
    cohort_mid: str,
    min_large_peers: int,
) -> Tuple[str, List[str]]:
    """Split a sector bucket into large-cap and mid-cap peer cohorts."""
    if not metrics_by_ticker:
        return cohort_mid.replace("_large", "").replace("_mid", ""), all_peers
    large_cap = float(load_settings().get("cap_tiers", {}).get("large", 500_000_000_000))
    meta_m = metrics_by_ticker.get(ticker)
    is_large = (
        meta_m is not None
        and getattr(meta_m, "market_cap", None) is not None
        and float(meta_m.market_cap) >= large_cap
    )
    if is_large:
        large_peers = [
            t
            for t in all_peers
            if t in metrics_by_ticker
            and getattr(metrics_by_ticker[t], "market_cap", None) is not None
            and float(metrics_by_ticker[t].market_cap) >= large_cap
        ]
        if len(large_peers) >= min_large_peers:
            return cohort_large, large_peers
    else:
        mid_peers = [
            t
            for t in all_peers
            if t in metrics_by_ticker
            and (
                getattr(metrics_by_ticker[t], "market_cap", None) is None
                or float(metrics_by_ticker[t].market_cap) < large_cap
            )
        ]
        if len(mid_peers) >= min_large_peers:
            return cohort_mid, mid_peers
    return cohort_mid.replace("_large", "").replace("_mid", ""), all_peers


def all_tickers() -> List[str]:
    return list(ticker_index().keys())


def ticker_meta(ticker: str) -> Optional[Dict[str, Any]]:
    return ticker_index().get(ticker)


def sector_focus_for_ticker(ticker: str) -> str:
    m = ticker_meta(ticker)
    return m["sector_focus"] if m else "unknown"


def model_sector_for_ticker(ticker: str) -> str:
    m = ticker_meta(ticker)
    return m["model_sector"] if m else "UNKNOWN"


def analysis_depth_for_ticker(ticker: str) -> str:
    m = ticker_meta(ticker)
    return m["analysis_depth"] if m else "standard"


def is_cyclical_ticker(ticker: str) -> bool:
    m = ticker_meta(ticker)
    return bool(m and m.get("cyclical"))


def bank_cohort(ticker: str) -> str | None:
    m = ticker_meta(ticker)
    if not m:
        return None
    return m.get("bank_cohort")


def tickers_for_filter(sector_filter: str = "all") -> List[str]:
    buckets = FILTER_TO_BUCKETS.get(sector_filter, FILTER_TO_BUCKETS["all"])
    idx = ticker_index()
    out: List[str] = []
    for t, m in idx.items():
        if m["bucket"] in buckets:
            out.append(t)
    return out


def list_sector_buckets() -> List[Dict[str, Any]]:
    u = load_universe()
    result = []
    for bucket in BUCKET_KEYS:
        if bucket == "banking":
            block = u["banking"]
            count = len(block.get("private", [])) + len(block.get("psu", []))
        else:
            block = u.get(bucket, {})
            count = len(block.get("tickers", []))
        result.append(
            {
                "id": bucket,
                "model_sector": block.get("model_sector"),
                "display_sector": block.get("display_sector"),
                "cyclical": block.get("cyclical", False),
                "ticker_count": count,
            }
        )
    return result


def peer_set(ticker: str, metrics_by_ticker: Optional[Dict[str, Any]] = None) -> Tuple[str, List[str]]:
    """
    Return (cohort_key, peer tickers) for percentile ranking.
    Banking: private vs psu sub-cohort.
    Others: same bucket; fallback to same display_sector among known tickers.
    """
    m = ticker_meta(ticker)
    if not m:
        return "unknown", [ticker]

    focus = m["sector_focus"]
    if focus == "banking":
        cohort = m.get("bank_cohort") or "private"
        u = load_universe()
        peers = list(u["banking"].get(cohort, []))
        return f"banking_{cohort}", peers

    if focus == "it":
        all_it = it_tickers()
        it_min = int(load_settings().get("it_large_min_peers", 5))
        key, peers = _cap_split_peer_set(ticker, all_it, metrics_by_ticker, "it_large", "it_mid", it_min)
        return key, peers

    if focus in ("pharma", "capital_goods"):
        all_peers = _bucket_tickers(focus)
        min_peers = int(load_settings().get("it_large_min_peers", 5))
        key, peers = _cap_split_peer_set(
            ticker,
            all_peers,
            metrics_by_ticker,
            f"{focus}_large",
            f"{focus}_mid",
            min_peers,
        )
        if len(peers) >= 3:
            return key, peers
        return focus, all_peers

    if focus == "insurance":
        peers = insurance_tickers()
        return "insurance", peers if peers else [ticker]

    # Standard sectors: peers in same bucket
    bucket = m["bucket"]
    u = load_universe()
    block = u.get(bucket, {})
    peers = list(block.get("tickers", []))
    if len(peers) >= 3:
        return bucket, peers

    # Fallback: same display_sector among all tickers
    display = m["display_sector"]
    idx = ticker_index()
    fallback = [t for t, meta in idx.items() if meta["display_sector"] == display]
    if len(fallback) >= 3:
        return f"display_{display}", fallback

    return bucket or "unknown", peers if peers else [ticker]
