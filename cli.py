#!/usr/bin/env python
"""CLI for Banking & IT screener."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from screener.interpret.questionnaire import profile_from_answers
from screener.models import RiskProfile
from screener.pipeline import STATE, run_evaluation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Banking & IT stock screener")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_screen = sub.add_parser("screen", help="Run sector screen")
    p_screen.add_argument("--sector", default="all", choices=["all", "both", "banking", "it", "fmcg", "pharma", "auto", "energy", "metals", "capital_goods", "defensive", "cyclical", "no_financials"])
    p_screen.add_argument("--workers", type=int, default=8)
    p_screen.add_argument("--refresh", action="store_true")
    p_screen.add_argument("--export", type=str, default="")
    p_screen.add_argument("--top", type=int, default=0)

    p_explain = sub.add_parser("explain", help="Interpret a ticker")
    p_explain.add_argument("ticker")
    p_explain.add_argument("--refresh", action="store_true")

    p_rec = sub.add_parser("recommend", help="Recommend for a risk profile")
    p_rec.add_argument("--profile", default="moderate", choices=["conservative", "moderate", "growth", "aggressive"])
    p_rec.add_argument("--sector", default="all", choices=["all", "both", "banking", "it", "fmcg", "pharma", "auto", "energy", "metals", "capital_goods", "defensive", "cyclical", "no_financials"])
    p_rec.add_argument("--refresh", action="store_true")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.cmd == "screen":
        df = run_evaluation(
            max_workers=args.workers,
            sector_filter=args.sector,
            refresh=args.refresh,
        )
        if args.sector in ("banking", "it"):
            df = df[df["sector_focus"] == args.sector]
        out = df.head(args.top) if args.top else df
        print(out.to_string(index=False))
        if args.export:
            if args.export.endswith(".json"):
                out.to_json(args.export, orient="records", indent=2)
            else:
                out.to_csv(args.export, index=False)
            print(f"\nExported → {args.export}")
        return 0

    if args.cmd == "explain":
        if args.refresh or not STATE.scores:
            run_evaluation(refresh=args.refresh)
        t = args.ticker.upper()
        if not t.endswith(".NS"):
            t += ".NS"
        interp = STATE.interps.get(t)
        if interp is None:
            print(f"No data for {t}", file=sys.stderr)
            return 1
        print(json.dumps(interp.to_dict(), indent=2, default=str))
        return 0

    if args.cmd == "recommend":
        if args.refresh or not STATE.scores:
            run_evaluation(sector_filter=args.sector, refresh=args.refresh)
        labels = {
            "conservative": "Capital Preservation",
            "moderate": "Balanced Growth",
            "growth": "Growth Oriented",
            "aggressive": "High Conviction",
        }
        profile = RiskProfile(id=args.profile, label=labels[args.profile], sector_filter=args.sector)
        result = STATE.recommend(profile)
        print(result.summary)
        print("\nPicks:")
        for p in result.picks[:10]:
            print(f"  {p.ticker}: fit={p.fit_score:.0f} ({p.fit_label}) rec={p.recommendation} risk={p.stock_risk_score:.0f}")
            for r in p.reasons[:3]:
                print(f"    - {r}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
