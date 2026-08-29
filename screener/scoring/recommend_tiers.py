from __future__ import annotations

from typing import Optional


def recommend_from_percentile(
    composite_pctile: Optional[float],
    val_label: str,
    red_flag: bool,
    hard_fail: bool,
    confidence: float = 0.5,
) -> str:
    p = composite_pctile if composite_pctile is not None else 50.0

    if hard_fail:
        if val_label == "Over":
            return "SELL"
        return "AVOID" if p < 40 else "HOLD"

    if red_flag:
        if val_label == "Over":
            return "SELL"
        if p < 25:
            return "AVOID"
        if p >= 55:
            return "HOLD"

    if p >= 70 and val_label in ("Under", "Fair"):
        rec = "STRONG BUY"
    elif p >= 55 and val_label in ("Under", "Fair"):
        rec = "BUY"
    elif p >= 50 and val_label == "Under":
        rec = "BUY"
    elif p >= 35:
        rec = "HOLD"
    elif p >= 20:
        rec = "AVOID"
    else:
        rec = "SELL" if val_label == "Over" else "AVOID"

    if confidence < 0.35:
        ladder = ["SELL", "AVOID", "HOLD", "BUY", "STRONG BUY"]
        if rec in ladder:
            rec = ladder[max(0, ladder.index(rec) - 1)]
    return rec
