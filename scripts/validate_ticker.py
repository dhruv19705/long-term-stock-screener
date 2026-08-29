"""Validate yfinance data availability for universe candidates."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from screener.config_loader import yfinance_symbols_for  # noqa: E402


def validate_ticker(ticker: str, min_rows: int = 20) -> dict:
    last_err = "no data"
    for sym in yfinance_symbols_for(ticker):
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="6mo")
            info = t.info or {}
            rows = len(hist)
            pe = info.get("trailingPE") or info.get("forwardPE")
            pb = info.get("priceToBook")
            mcap = info.get("marketCap")
            ok = rows >= min_rows and (pe is not None or pb is not None or mcap is not None)
            return {
                "ticker": ticker,
                "symbol": sym,
                "ok": ok,
                "rows": rows,
                "pe": pe,
                "pb": pb,
                "mcap": mcap,
            }
        except Exception as exc:
            last_err = str(exc)
            continue
    return {"ticker": ticker, "symbol": None, "ok": False, "error": last_err}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", type=str, help="File with one ticker per line")
    parser.add_argument("tickers", nargs="*", help="Tickers to validate")
    args = parser.parse_args()

    tickers: list[str] = list(args.tickers)
    if args.list:
        path = Path(args.list)
        tickers.extend(line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip())

    passed, failed = [], []
    for t in tickers:
        r = validate_ticker(t)
        status = "PASS" if r["ok"] else "FAIL"
        print(f"{status} {t}: {r}")
        (passed if r["ok"] else failed).append(t)

    print(f"\nSummary: {len(passed)} passed, {len(failed)} failed")
    if failed:
        print("Failed:", ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
