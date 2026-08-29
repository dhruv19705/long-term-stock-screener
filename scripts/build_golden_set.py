"""Build screener/config/golden_set.yaml from embedded benchmark definitions."""
from __future__ import annotations

from pathlib import Path

import yaml

# Core 27 large caps + 38 expansion = 65 tickers (street labels from A+ plan Aug 2026)
TICKERS = {
    # Banking (7 core)
    "HDFCBANK.NS": {"street": "BUY", "cap_tier": "large", "sector": "banking", "source": "stockanalysis.com"},
    "ICICIBANK.NS": {"street": "STRONG BUY", "cap_tier": "large", "sector": "banking", "source": "stockanalysis.com"},
    "SBIN.NS": {"street": "BUY", "cap_tier": "large", "sector": "banking", "source": "ET Jul 2025"},
    "KOTAKBANK.NS": {"street": "HOLD", "cap_tier": "large", "sector": "banking", "source": "consensus"},
    "AXISBANK.NS": {"street": "BUY", "cap_tier": "large", "sector": "banking", "source": "ET Jul 2025"},
    "INDUSINDBK.NS": {"street": "BUY", "cap_tier": "large", "sector": "banking", "source": "consensus"},
    "ADANIPORTS.NS": {"street": "BUY", "cap_tier": "large", "sector": "infra", "source": "CNBC-TV18"},
    # IT (6 core)
    "TCS.NS": {"street": "BUY", "cap_tier": "large", "sector": "it", "source": "stockanalysis.com"},
    "INFY.NS": {"street": "BUY", "cap_tier": "large", "sector": "it", "source": "stockanalysis.com"},
    "HCLTECH.NS": {"street": "HOLD", "cap_tier": "large", "sector": "it", "source": "stockanalysis.com"},
    "WIPRO.NS": {"street": "HOLD", "cap_tier": "large", "sector": "it", "source": "stockanalysis.com"},
    "TECHM.NS": {"street": "HOLD", "cap_tier": "large", "sector": "it", "source": "BusinessToday"},
    "PERSISTENT.NS": {"street": "BUY", "cap_tier": "mid", "sector": "it", "source": "consensus"},
    # Consumer (8 core)
    "ITC.NS": {"street": "BUY", "cap_tier": "large", "sector": "fmcg", "source": "ET Jul 2025"},
    "HINDUNILVR.NS": {"street": "HOLD", "cap_tier": "large", "sector": "fmcg", "source": "consensus"},
    "NESTLEIND.NS": {"street": "HOLD", "cap_tier": "large", "sector": "fmcg", "source": "consensus"},
    "MARUTI.NS": {"street": "BUY", "cap_tier": "large", "sector": "auto", "source": "ET Jul 2025"},
    "BAJAJ-AUTO.NS": {"street": "BUY", "cap_tier": "large", "sector": "auto", "source": "consensus"},
    "HEROMOTOCO.NS": {"street": "BUY", "cap_tier": "large", "sector": "auto", "source": "stockanalysis.com"},
    "EICHERMOT.NS": {"street": "BUY", "cap_tier": "large", "sector": "auto", "source": "consensus"},
    "TITAN.NS": {"street": "BUY", "cap_tier": "large", "sector": "consumer", "source": "PL Capital"},
    # Pharma (3 core)
    "SUNPHARMA.NS": {"street": "BUY", "cap_tier": "large", "sector": "pharma", "source": "stockanalysis.com"},
    "DIVISLAB.NS": {"street": "BUY", "cap_tier": "large", "sector": "pharma", "source": "consensus"},
    "DRREDDY.NS": {"street": "BUY", "cap_tier": "large", "sector": "pharma", "source": "consensus"},
    # Energy/Materials (3 core)
    "RELIANCE.NS": {"street": "BUY", "cap_tier": "large", "sector": "energy", "source": "stockanalysis.com"},
    "BPCL.NS": {"street": "HOLD", "cap_tier": "large", "sector": "energy", "source": "stockanalysis.com"},
    "JSWSTEEL.NS": {"street": "HOLD", "cap_tier": "large", "sector": "metals", "source": "consensus"},
    # Industrials (3 core)
    "LT.NS": {"street": "BUY", "cap_tier": "large", "sector": "industrials", "source": "consensus"},
    "ULTRACEMCO.NS": {"street": "BUY", "cap_tier": "large", "sector": "materials", "source": "ET Jul 2025"},
    "M&M.NS": {"street": "BUY", "cap_tier": "large", "sector": "auto", "source": "ET Jul 2025"},
    # Expansion — Banking (6)
    "CANBK.NS": {"street": "BUY", "cap_tier": "large", "sector": "banking", "source": "consensus"},
    "BANKBARODA.NS": {"street": "BUY", "cap_tier": "large", "sector": "banking", "source": "consensus"},
    "FEDERALBNK.NS": {"street": "HOLD", "cap_tier": "mid", "sector": "banking", "source": "consensus"},
    "BANDHANBNK.NS": {"street": "BUY", "cap_tier": "mid", "sector": "banking", "source": "stocktargetadvisor"},
    "PNB.NS": {"street": "HOLD", "cap_tier": "large", "sector": "banking", "source": "consensus"},
    "IDFCFIRSTB.NS": {"street": "HOLD", "cap_tier": "mid", "sector": "banking", "source": "consensus"},
    # IT expansion (6)
    "COFORGE.NS": {"street": "BUY", "cap_tier": "mid", "sector": "it", "source": "BusinessToday"},
    "MPHASIS.NS": {"street": "BUY", "cap_tier": "mid", "sector": "it", "source": "consensus"},
    "OFSS.NS": {"street": "HOLD", "cap_tier": "mid", "sector": "it", "source": "consensus"},
    "KPITTECH.NS": {"street": "BUY", "cap_tier": "mid", "sector": "it", "source": "consensus"},
    "LTTS.NS": {"street": "HOLD", "cap_tier": "mid", "sector": "it", "source": "consensus"},
    "NAUKRI.NS": {"street": "HOLD", "cap_tier": "mid", "sector": "it", "source": "consensus"},
    # FMCG expansion (6)
    "DABUR.NS": {"street": "HOLD", "cap_tier": "large", "sector": "fmcg", "source": "consensus"},
    "BRITANNIA.NS": {"street": "HOLD", "cap_tier": "large", "sector": "fmcg", "source": "consensus"},
    "MARICO.NS": {"street": "BUY", "cap_tier": "large", "sector": "fmcg", "source": "consensus"},
    "GODREJCP.NS": {"street": "BUY", "cap_tier": "large", "sector": "fmcg", "source": "consensus"},
    "COLPAL.NS": {"street": "HOLD", "cap_tier": "large", "sector": "fmcg", "source": "consensus"},
    "TATACONSUM.NS": {"street": "HOLD", "cap_tier": "large", "sector": "fmcg", "source": "consensus"},
    # Pharma expansion (6)
    "CIPLA.NS": {"street": "BUY", "cap_tier": "large", "sector": "pharma", "source": "consensus"},
    "LUPIN.NS": {"street": "BUY", "cap_tier": "large", "sector": "pharma", "source": "PL Capital"},
    "ALKEM.NS": {"street": "BUY", "cap_tier": "large", "sector": "pharma", "source": "consensus"},
    "TORNTPHARM.NS": {"street": "BUY", "cap_tier": "mid", "sector": "pharma", "source": "consensus"},
    "ZYDUSLIFE.NS": {"street": "BUY", "cap_tier": "large", "sector": "pharma", "source": "consensus"},
    "BIOCON.NS": {"street": "HOLD", "cap_tier": "mid", "sector": "pharma", "source": "consensus"},
    # Auto/Consumer expansion (4)
    "TVSMOTOR.NS": {"street": "BUY", "cap_tier": "large", "sector": "auto", "source": "consensus"},
    "BHARATFORG.NS": {"street": "HOLD", "cap_tier": "mid", "sector": "auto", "source": "consensus"},
    "TRENT.NS": {"street": "BUY", "cap_tier": "large", "sector": "consumer", "source": "consensus"},
    "PAGEIND.NS": {"street": "HOLD", "cap_tier": "large", "sector": "consumer", "source": "consensus"},
    # Energy expansion (4)
    "ONGC.NS": {"street": "HOLD", "cap_tier": "large", "sector": "energy", "source": "consensus"},
    "NTPC.NS": {"street": "BUY", "cap_tier": "large", "sector": "energy", "source": "consensus"},
    "COALINDIA.NS": {"street": "HOLD", "cap_tier": "large", "sector": "energy", "source": "consensus"},
    "GAIL.NS": {"street": "HOLD", "cap_tier": "large", "sector": "energy", "source": "consensus"},
    # Metals expansion (3)
    "HINDALCO.NS": {"street": "BUY", "cap_tier": "large", "sector": "metals", "source": "consensus"},
    "VEDL.NS": {"street": "HOLD", "cap_tier": "large", "sector": "metals", "source": "consensus"},
    "JINDALSTEL.NS": {"street": "STRONG BUY", "cap_tier": "large", "sector": "metals", "source": "stocktargetadvisor"},
    # Industrials expansion (3)
    "ABB.NS": {"street": "BUY", "cap_tier": "large", "sector": "industrials", "source": "PL Capital"},
    "HAL.NS": {"street": "BUY", "cap_tier": "large", "sector": "industrials", "source": "PL Capital"},
    "INDIGO.NS": {"street": "BUY", "cap_tier": "large", "sector": "industrials", "source": "PL Capital"},
    # Nifty additions (9)
    "BHARTIARTL.NS": {"street": "BUY", "cap_tier": "large", "sector": "telecom", "source": "PL Capital"},
    "ASIANPAINT.NS": {"street": "HOLD", "cap_tier": "large", "sector": "consumer", "source": "consensus"},
    "BAJFINANCE.NS": {"street": "BUY", "cap_tier": "large", "sector": "financials", "source": "consensus"},
    "BAJAJFINSV.NS": {"street": "STRONG BUY", "cap_tier": "large", "sector": "financials", "source": "stocktargetadvisor"},
    "PIDILITIND.NS": {"street": "STRONG BUY", "cap_tier": "large", "sector": "consumer", "source": "stocktargetadvisor"},
    "AMBUJACEM.NS": {"street": "STRONG BUY", "cap_tier": "large", "sector": "materials", "source": "stocktargetadvisor"},
    "APOLLOHOSP.NS": {"street": "BUY", "cap_tier": "large", "sector": "healthcare", "source": "PL Capital"},
    "POWERGRID.NS": {"street": "HOLD", "cap_tier": "large", "sector": "utilities", "source": "consensus"},
}


def main() -> None:
    out = {"version": "2026-08", "tickers": TICKERS}
    path = Path(__file__).resolve().parents[1] / "screener" / "config" / "golden_set.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(out, f, sort_keys=False, allow_unicode=True)
    print(f"Wrote {len(TICKERS)} tickers to {path}")


if __name__ == "__main__":
    main()
