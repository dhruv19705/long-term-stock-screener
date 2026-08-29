"""End-to-end audit: screen full universe, recommend, sample interpretations."""
from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict

from screener.config_loader import all_tickers, list_sector_buckets
from screener.interpret.questionnaire import profile_from_answers
from screener.models import RiskProfile
from screener.pipeline import run_evaluation, STATE


def main() -> int:
    universe = all_tickers()
    print(f"=== UNIVERSE: {len(universe)} tickers, {len(list_sector_buckets())} buckets ===\n")

    t0 = time.perf_counter()
    df = run_evaluation(sector_filter="all", max_workers=8, refresh=False)
    elapsed = time.perf_counter() - t0

    kept = len(df)
    dropped = len(STATE.dropped)
    print(f"=== SCREEN ({elapsed:.1f}s): kept {kept}, dropped {dropped} ===\n")

    by_sector = Counter(df["sector_focus"].tolist())
    print("Kept by sector:")
    for s, n in sorted(by_sector.items(), key=lambda x: -x[1]):
        print(f"  {s}: {n}")

    depth = Counter(df["analysis_depth"].tolist())
    print(f"\nAnalysis depth: {dict(depth)}")

    recs = Counter(df["recommendation"].tolist())
    print(f"Recommendations: {dict(recs)}")

    comp = df["composite_score"].dropna()
    print(f"\nComposite: min={comp.min():.1f} max={comp.max():.1f} mean={comp.mean():.1f} median={comp.median():.1f}")

    drop_reasons = Counter(r for _, r in STATE.dropped)
    print(f"\nDrop reasons ({len(drop_reasons)} types):")
    for r, n in drop_reasons.most_common(10):
        print(f"  {n}x {r}")

    # Recommendations for moderate profile
    profile = profile_from_answers(
        {
            "horizon": "long",
            "goal": "grow",
            "drawdown": "hold",
            "income_need": "nice",
            "experience": "intermediate",
            "loss_tolerance": "med",
            "volatility": "med",
            "valuation": "fair",
            "leverage": "mod",
            "cyclical_pref": "balanced",
            "liquidity": "no",
            "concentration": "med",
            "diversification": "yes",
            "sector_exposure": "all",
        }
    )
    print(f"\n=== RECOMMEND ({profile.label}, sector={profile.sector_filter}) ===")
    result = STATE.recommend(profile)
    print(result.summary)
    print(f"Picks: {len(result.picks)}, sectors in picks_by_sector: {list(result.picks_by_sector.keys())}")
    for sector, picks in sorted(result.picks_by_sector.items()):
        print(f"  {sector}: {[p.ticker for p in picks]}")

    # Sample deep vs standard interpret
    samples = []
    for focus in ("banking", "fmcg", "metals"):
        sub = df[df["sector_focus"] == focus]
        if len(sub):
            samples.append(str(sub.iloc[0]["stock"]))
    print("\n=== SAMPLE INTERPRETATIONS ===")
    for t in samples[:3]:
        interp = STATE.interps.get(t)
        if not interp:
            continue
        print(f"\n{t} ({interp.analysis_depth}, rec={interp.recommendation}, risk={interp.stock_risk_score:.0f})")
        print(f"  Qs: {len(interp.questions)} | {interp.headline[:80]}...")
        bad = [q.id for q in interp.questions if q.signal == "bad"]
        if bad:
            print(f"  Bad signals: {bad}")

    audit = {
        "universe": len(universe),
        "kept": kept,
        "dropped": dropped,
        "elapsed_s": round(elapsed, 1),
        "by_sector": dict(by_sector),
        "recommendations": dict(recs),
        "pick_sectors": list(result.picks_by_sector.keys()),
        "n_picks": len(result.picks),
    }
    print("\n=== AUDIT JSON ===")
    print(json.dumps(audit, indent=2))
    return 0 if kept >= 80 else 1


if __name__ == "__main__":
    raise SystemExit(main())
