"""API end-to-end smoke test."""
from __future__ import annotations

import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8000"


def get(path: str, timeout: int = 600):
    return json.loads(urllib.request.urlopen(BASE + path, timeout=timeout).read())


def post(path: str, body: dict, timeout: int = 600):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read())


def main() -> int:
    print("health", get("/api/health", timeout=10))
    sectors = get("/api/sectors", timeout=10)
    print("sectors", len(sectors["sectors"]), "buckets")

    q = get("/api/questionnaire", timeout=10)
    print("questions", len(q["questions"]))

    answers = {
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
    profile = post("/api/questionnaire/submit", {"answers": answers}, timeout=30)
    print("profile", profile["id"], profile["sector_filter"])

    print("Fetching full screen...")
    t0 = time.time()
    screen = get("/api/screen?sector=all", timeout=900)
    print(
        f"screen in {time.time() - t0:.0f}s: kept={screen['count']} "
        f"dropped={len(screen['dropped'])} universe={screen.get('total_universe')}"
    )

    by_sector: dict[str, int] = {}
    for row in screen["rows"]:
        sf = str(row.get("sector_focus", "?"))
        by_sector[sf] = by_sector.get(sf, 0) + 1
    print("by_sector", dict(sorted(by_sector.items(), key=lambda x: -x[1])))

    rec = post(
        "/api/recommend",
        {
            "risk_profile_id": profile["id"],
            "sector_filter": "all",
            "label": profile["label"],
            "max_stock_risk": profile.get("max_stock_risk"),
            "max_beta": profile.get("max_beta"),
            "cyclical_ok": profile.get("cyclical_ok"),
            "diversify_sectors": profile.get("diversify_sectors"),
        },
        timeout=900,
    )
    print("picks", len(rec["picks"]))
    print("pick_sectors", list((rec.get("picks_by_sector") or {}).keys()))

    if rec["picks"]:
        t = rec["picks"][0]["ticker"]
        interp = get(f"/api/stock/{t}/interpret", timeout=60)
        print(
            "interpret",
            t,
            interp["analysis_depth"],
            len(interp["questions"]),
            "Qs",
            interp["recommendation"],
        )

    return 0 if screen["count"] >= 80 else 1


if __name__ == "__main__":
    raise SystemExit(main())
