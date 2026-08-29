from screener.interpret.signals import evaluate_signal


def test_good_signal():
    ctx = {"gnpa_pct": 1.0, "nnpa_pct": 0.3}
    signals = {
        "good": {"gnpa_pct": {"op": "<", "value": 1.5}, "nnpa_pct": {"op": "<", "value": 0.5}},
        "warn": {"gnpa_pct": {"op": "<", "value": 2.5}},
        "bad": {},
    }
    assert evaluate_signal(ctx, signals) == "good"


def test_warn_signal():
    ctx = {"gnpa_pct": 2.0, "nnpa_pct": 0.8}
    signals = {
        "good": {"gnpa_pct": {"op": "<", "value": 1.5}, "nnpa_pct": {"op": "<", "value": 0.5}},
        "warn": {"gnpa_pct": {"op": "<", "value": 2.5}},
        "bad": {},
    }
    assert evaluate_signal(ctx, signals) == "warn"


def test_bad_signal():
    ctx = {"gnpa_pct": 4.0}
    signals = {
        "good": {"gnpa_pct": {"op": "<", "value": 1.5}},
        "warn": {"gnpa_pct": {"op": "<", "value": 2.5}},
        "bad": {},
    }
    assert evaluate_signal(ctx, signals) == "bad"


def test_unknown_when_missing():
    ctx = {}
    signals = {"good": {"car_pct": {"op": ">", "value": 16}}, "warn": {}, "bad": {}}
    assert evaluate_signal(ctx, signals) == "unknown"
