from screener.scoring.factors import soft_score_higher, soft_score_lower, weighted_mean, winsorize


def test_winsorize():
    vals = [1.0, 2.0, 3.0, 4.0, 100.0]
    w = winsorize(vals, 0.0, 0.8)
    assert max(x for x in w if x is not None) < 100


def test_soft_scores():
    assert soft_score_higher(20, good=20, bad=10) == 1.0
    assert soft_score_higher(10, good=20, bad=10) == 0.0
    assert 0 < soft_score_higher(15, good=20, bad=10) < 1
    assert soft_score_lower(1.0, good=1.0, bad=3.0) == 1.0


def test_weighted_mean_renorm():
    score, used = weighted_mean({"a": 1.0, "b": None}, {"a": 0.5, "b": 0.5})
    assert score == 1.0
    assert "a" in used and "b" not in used
