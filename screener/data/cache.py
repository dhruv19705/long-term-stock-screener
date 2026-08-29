from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from screener.config_loader import load_settings

logger = logging.getLogger("screener.cache")


def _cache_root() -> Path:
    settings = load_settings()
    root = Path(settings.get("cache_dir", ".cache/screener"))
    if not root.is_absolute():
        root = Path.cwd() / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path_for(ticker: str) -> Path:
    safe = ticker.replace("/", "_").replace("\\", "_")
    return _cache_root() / f"{safe}.json"


def get_cached_metrics(ticker: str) -> Optional[Dict[str, Any]]:
    settings = load_settings()
    ttl_h = float(settings.get("cache_ttl_hours", 24))
    path = _path_for(ticker)
    if not path.exists():
        return None
    age_h = (time.time() - path.stat().st_mtime) / 3600.0
    if age_h > ttl_h:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Cache read failed for %s: %s", ticker, e)
        return None


def set_cached_metrics(ticker: str, data: Dict[str, Any]) -> None:
    path = _path_for(ticker)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        logger.warning("Cache write failed for %s: %s", ticker, e)


def clear_cache() -> int:
    root = _cache_root()
    n = 0
    for p in root.glob("*.json"):
        p.unlink(missing_ok=True)
        n += 1
    return n
