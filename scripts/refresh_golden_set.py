"""Quarterly refresh helper for golden_set.yaml street labels (manual review required)."""
from __future__ import annotations

import subprocess
import sys
from datetime import date

from screener.config_loader import load_golden_set


def main() -> None:
    gs = load_golden_set()
    version = gs.get("version", "unknown")
    n = len(gs.get("tickers") or {})
    print(f"Golden set version={version} tickers={n} as of {date.today().isoformat()}")
    print("Update street labels in screener/config/golden_set.yaml after earnings season.")
    print("Re-run: python scripts/build_golden_set.py  (if ticker list changed)")
    print("Validate: python scripts/golden_set_audit.py --large-cap")
    if "--rebuild" in sys.argv:
        subprocess.check_call([sys.executable, "scripts/build_golden_set.py"])


if __name__ == "__main__":
    main()
