from __future__ import annotations

from typing import Any, Dict, Optional


def _compare(val: Any, rule: Dict[str, Any]) -> bool:
    op = rule.get("op")
    if op == "<":
        return val is not None and float(val) < float(rule["value"])
    if op == ">":
        return val is not None and float(val) > float(rule["value"])
    if op == "<=":
        return val is not None and float(val) <= float(rule["value"])
    if op == ">=":
        return val is not None and float(val) >= float(rule["value"])
    if op == "==":
        return val == rule["value"]
    if op == "in":
        return val in rule.get("values", [])
    if op == "between":
        if val is None:
            return False
        return float(rule["low"]) <= float(val) <= float(rule["high"])
    return False


def _rules_pass(context: Dict[str, Any], rules: Dict[str, Any]) -> bool:
    if not rules:
        return True
    return all(_compare(context.get(k), rule) for k, rule in rules.items())


def evaluate_signal(context: Dict[str, Any], signals: Dict[str, Any]) -> str:
    """
    Evaluate good → warn → else bad.
    Missing required metrics for good/warn → unknown if all metrics missing.
    """
    metric_keys = set()
    for band in signals.values():
        metric_keys.update(band.keys())
    present = [k for k in metric_keys if context.get(k) is not None]
    if metric_keys and not present:
        return "unknown"

    if _rules_pass(context, signals.get("good") or {}):
        return "good"
    if _rules_pass(context, signals.get("warn") or {}):
        return "warn"
    return "bad"
