"""Per-sector audit: coverage, drops, recommendation mix, composite stats."""
from __future__ import annotations

import json
import sys
from collections import Counter

from screener.config_loader import BUCKET_KEYS, all_tickers
from screener.pipeline import run_evaluation, STATE


def main() -> int:
    run_evaluation(sector_filter="all", use_cache=True)
    df = STATE.to_dataframe()
    dropped_by_sector: dict[str, list[str]] = {k: [] for k in BUCKET_KEYS}
    for t, reason in STATE.dropped:
        from screener.config_loader import sector_focus_for_ticker
        try:
            sec = sector_focus_for_ticker(t)
        except Exception:
            sec = "unknown"
        dropped_by_sector.setdefault(sec, []).append(f"{t} ({reason})")

    report = {}
    print("=== SECTOR AUDIT ===\n")
    for sector in BUCKET_KEYS:
        sub = df[df["sector_focus"] == sector]
        n_universe = len([t for t in all_tickers() if t in STATE.metrics or any(t == d[0] for d in STATE.dropped)])
        recs = Counter(sub["recommendation"].tolist()) if len(sub) else Counter()
        grades = Counter(
            STATE.scores[t].quality_grade for t in sub["stock"].tolist() if t in STATE.scores
        ) if len(sub) else Counter()
        comp = sub["composite_score"]
        entry = {
            "kept": int(len(sub)),
            "dropped": len(dropped_by_sector.get(sector, [])),
            "recommendations": dict(recs),
            "quality_grades": dict(grades),
            "composite_mean": round(float(comp.mean()), 1) if len(comp) else None,
            "composite_spread": round(float(comp.max() - comp.min()), 1) if len(comp) > 1 else None,
            "drops": dropped_by_sector.get(sector, [])[:5],
        }
        report[sector] = entry
        print(f"--- {sector.upper()} (kept {entry['kept']}, dropped {entry['dropped']}) ---")
        print(f"  Recs: {entry['recommendations']}")
        print(f"  Grades: {entry['quality_grades']}")
        if entry["composite_mean"] is not None:
            print(f"  Composite mean={entry['composite_mean']} spread={entry['composite_spread']}")
        if entry["drops"]:
            print(f"  Drops: {entry['drops']}")
        print()

    print("=== JSON ===")
    print(json.dumps(report, indent=2))
    total_kept = len(df)
    total_universe = len(all_tickers())
    return 0 if total_kept >= total_universe * 0.92 else 1


if __name__ == "__main__":
    raise SystemExit(main())
