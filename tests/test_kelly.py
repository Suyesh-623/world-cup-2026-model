"""Pin the money math to my worked examples.

These exact-number tests are the guardrail: if a refactor changes the sizing,
the suite breaks before any real money is at stake.
"""

from model.kelly import (
    american_to_prob,
    american_to_decimal,
    ev_binary,
    evaluate_bet,
    kelly_american,
    kelly_binary,
)


def approx(a: float, b: float, tol: float = 1e-3) -> bool:
    return abs(a - b) <= tol


def test_american_implied_prob():
    assert approx(american_to_prob(155), 0.3922)
    assert approx(american_to_prob(-130), 0.5652)
    assert approx(american_to_decimal(155), 2.55, 1e-2)


def test_switzerland_moneyline():
    # +155, model p = 0.41 -> full Kelly ~2.94%, half ~1.47%
    full = kelly_american(0.41, 155)
    assert approx(full, 0.0294)
    assert approx(full / 2, 0.0147)


def test_morocco_spread_binary():
    # Buy YES at 35c, model p = 0.445 -> full 14.62%, half 7.31%
    full = kelly_binary(0.445, 0.35)
    assert approx(full, 0.14615, 1e-4)
    assert approx(full / 2, 0.07308, 1e-4)


def test_morocco_at_entry_price():
    # Same model prob, bought earlier at 39c -> full 9.02%
    assert approx(kelly_binary(0.445, 0.39), 0.09016, 1e-4)


def test_clean_form_matches_closed_form():
    # kelly_binary with no fees == (p - c) / (1 - c)
    p, c = 0.58, 0.52
    assert approx(kelly_binary(p, c), (p - c) / (1 - c), 1e-9)


def test_fee_reduces_size_and_ev():
    no_fee = kelly_binary(0.445, 0.35, 0.0, 0.0)
    with_fee = kelly_binary(0.445, 0.35, 0.01, 0.01)
    assert with_fee < no_fee
    assert ev_binary(0.445, 0.35, 0.01, 0.01) < ev_binary(0.445, 0.35, 0.0, 0.0)


def test_no_bet_on_non_positive_edge():
    assert kelly_binary(0.40, 0.45) == 0.0
    decision = evaluate_bet(0.40, 0.45, 10_000)
    assert decision.verdict == "pass"
    assert decision.stake == 0.0


def test_evaluate_bet_morocco_half_kelly_stake():
    # Half-Kelly on $10k, no fee, cap lifted -> 7.31% -> ~$731
    decision = evaluate_bet(
        0.445, 0.35, 10_000, kelly_fraction=0.5, fee=0.0, max_fraction=1.0
    )
    assert approx(decision.sized_fraction, 0.07308, 1e-3)
    assert approx(decision.stake, 730.8, 1.0)
    assert decision.verdict == "bet"


def test_max_fraction_cap_binds():
    # A huge edge is capped at max_fraction (variance control).
    decision = evaluate_bet(0.90, 0.30, 10_000, kelly_fraction=0.5, max_fraction=0.10)
    assert decision.sized_fraction == 0.10
