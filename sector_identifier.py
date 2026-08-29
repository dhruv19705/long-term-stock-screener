"""
Quick sector lookup using yfinance (demo script).

Prints:
  - per-ticker sector
  - unique sectors count
  - tickers grouped by sector
"""

from __future__ import annotations

from collections import defaultdict

import yfinance as yf

stocks = [
    # Technology
    "AAPL",
    "MSFT",
    # Healthcare
    "JNJ",
    "PFE",
    # Financial Services
    "JPM",
    "BAC",
    # Consumer Cyclical
    "AMZN",
    "TSLA",
    # Consumer Defensive
    "WMT",
    "PG",
    # Industrials
    "BA",
    "CAT",
    # Energy
    "XOM",
    "CVX",
    # Utilities
    "NEE",
    "DUK",
    # Real Estate
    "AMT",
    "PLD",
    # Basic Materials
    "LIN",
    "FCX",
    # Communication Services
    "GOOGL",
    "META",
]


def main() -> None:
    sectors: dict[str, str] = {}
    for stock in stocks:
        try:
            info = yf.Ticker(stock).info
            sector = info.get("sector", "Unknown")
            sectors[stock] = sector
            print(f"{stock}: {sector}")
        except Exception:
            print(f"{stock}: Error")

    sector_map: dict[str, list[str]] = defaultdict(list)
    for stock, sector in sectors.items():
        sector_map[sector].append(stock)

    unique_sectors = set(sectors.values())
    print("\nUnique sectors:")
    print(unique_sectors)
    print("\nNumber of sectors:")
    print(len(unique_sectors))

    print("\nStocks grouped by sector:")
    for sec in sorted(sector_map.keys()):
        tickers = sorted(sector_map[sec])
        print(f"{sec}: {tickers}")


if __name__ == "__main__":
    main()