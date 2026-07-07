"""Coherence tests for the Poisson market engine.

We can't assert "correct" probabilities without ground truth, but every market
derived from one distribution must be internally consistent — those invariants
catch real bugs (off-by-one totals, handicap sign errors, un-normalized mass).
"""
from model.poisson import (
    lambdas_from_ratings,
    match_markets,
    score_matrix,
)


def approx(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) <= tol


def test_matrix_normalized():
    m = score_matrix(1.8, 1.1)
    total = sum(p for row in m for p in row)
    assert approx(total, 1.0, 1e-9)


def test_result_sums_to_one():
    mk = match_markets(1.9, 1.0)
    r = mk["result"]
    assert approx(r["home"] + r["draw"] + r["away"], 1.0, 1e-9)


def test_btts_complementary():
    mk = match_markets(1.4, 1.2)
    assert approx(mk["btts"]["yes"] + mk["btts"]["no"], 1.0, 1e-9)


def test_totals_complementary():
    mk = match_markets(1.6, 1.3)
    for line, ou in mk["totals"].items():
        assert approx(ou["over"] + ou["under"], 1.0, 1e-9), line


def test_handicap_mirror():
    mk = match_markets(2.1, 0.7)
    h = mk["handicap"]
    assert approx(h["home_-1.5"] + h["away_+1.5"], 1.0, 1e-9)
    assert approx(h["home_-2.5"] + h["away_+2.5"], 1.0, 1e-9)


def test_favorite_more_likely_to_win():
    mk = match_markets(2.2, 0.6)
    r = mk["result"]
    assert r["home"] > r["away"]
    # home -0.5 handicap is exactly the home win probability
    assert approx(mk["handicap"]["home_-0.5"], r["home"], 1e-9)


def test_more_goals_raise_over():
    low = match_markets(0.8, 0.7)["totals"]["2.5"]["over"]
    high = match_markets(2.4, 1.9)["totals"]["2.5"]["over"]
    assert high > low


def test_correct_score_sorted_and_positive():
    cs = match_markets(1.7, 1.1)["correct_score"]
    probs = [s["prob"] for s in cs]
    assert all(p > 0 for p in probs)
    assert probs == sorted(probs, reverse=True)


def test_first_half_fewer_goals_than_full():
    mk = match_markets(2.0, 1.4)
    # First-half over 1.5 should be less likely than full-match over 1.5
    assert mk["first_half"]["totals"]["1.5"]["over"] < mk["totals"]["1.5"]["over"]


def test_ratings_to_lambdas_favor_stronger_side():
    lam_h, lam_a = lambdas_from_ratings(att_home=0.4, def_home=0.3,
                                        att_away=-0.2, def_away=-0.1)
    assert lam_h > lam_a
