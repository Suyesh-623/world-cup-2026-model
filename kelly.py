"""Fee-aware Kelly / expected-value sizing for binary event contracts.

A binary (Kalshi / Robinhood-style) contract is bought at price ``c`` dollars
(0 < c < 1) and pays $1 if the event resolves YES. The price equals the
market's implied probability. We compare it against the model probability
``p`` to measure edge, then size the stake with the Kelly criterion —
half-Kelly by default, the standard discipline for high-variance sports
markets where model error is real.

The clean (no-fee) results reproduce my worked examples exactly, which
is why those cases are pinned as tests (see ``tests/test_kelly.py``):

  * Switzerland +155, model p = 0.41  -> full Kelly 2.94%  (half 1.47%)
  * Morocco -2.5 at 35c, model p = 0.445 -> full Kelly 14.62% (half 7.31%)

Keeping the sizing in one audited module (mirrored on the client in
``src/lib/betting/kelly.ts``) means the money math has a single source of
truth instead of being re-derived per call site.
"""

from __future__ import annotations

from dataclasses import dataclass

# ── Odds conversions ────────────────────────────────────────────────────────


def american_to_prob(odds: float) -> float:
    """Implied probability from American odds (+150, -130, ...)."""
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return -odds / (-odds + 100.0)


def american_to_decimal(odds: float) -> float:
    """Decimal odds from American odds."""
    if odds > 0:
        return odds / 100.0 + 1.0
    return 100.0 / -odds + 1.0


# ── Kelly primitives ────────────────────────────────────────────────────────


def kelly_from_b(p: float, b: float) -> float:
    """Full Kelly fraction for net decimal odds ``b`` (= decimal odds - 1).

    f* = (b*p - q) / b, clamped at 0 so a non-positive edge means "no bet".
    """
    if b <= 0:
        return 0.0
    q = 1.0 - p
    return max(0.0, (b * p - q) / b)


def kelly_american(p: float, odds: float) -> float:
    """Full Kelly fraction given model prob ``p`` and American odds."""
    return kelly_from_b(p, american_to_decimal(odds) - 1.0)


def kelly_binary(
    p: float, price: float, fee_buy: float = 0.0, fee_sell: float = 0.0
) -> float:
    """Full Kelly fraction for a binary contract bought at ``price``, paying $1.

    The cost basis includes the buy fee; the settlement payout is net of the
    sell fee. With zero fees this reduces to the clean form ``(p - price) / (1 - price)``.
    """
    cost = price + fee_buy
    net_win = 1.0 - fee_sell - cost  # profit per contract if YES
    if cost <= 0 or net_win <= 0:
        return 0.0
    return kelly_from_b(p, net_win / cost)


def ev_binary(
    p: float, price: float, fee_buy: float = 0.0, fee_sell: float = 0.0
) -> float:
    """Expected profit per contract (risking ``price + fee_buy`` dollars)."""
    cost = price + fee_buy
    net_win = 1.0 - fee_sell - cost
    return p * net_win - (1.0 - p) * cost


# ── High-level sizing decision ──────────────────────────────────────────────


@dataclass
class BetSizing:
    """One sized betting decision, ready to render or alert on."""

    model_prob: float
    market_price: float  # contract price == market-implied probability
    baseline_prob: float | None  # Opta/FIFA consensus, if available
    edge: float  # model_prob - market_price
    full_kelly: float
    kelly_fraction: float  # e.g. 0.5 for half-Kelly
    sized_fraction: float  # full_kelly * kelly_fraction, after the cap
    stake: float  # dollars on the bankroll
    ev_per_contract: float
    verdict: str  # 'pass' | 'lean' | 'bet'


def evaluate_bet(
    model_prob: float,
    market_price: float,
    bankroll: float,
    *,
    baseline_prob: float | None = None,
    kelly_fraction: float = 0.5,
    fee: float = 0.01,
    max_fraction: float = 0.10,
    min_edge: float = 0.02,
) -> BetSizing:
    """Turn a (model prob, market price) pair into a fee-aware, capped stake.

    ``fee`` is applied on both sides. ``max_fraction`` is a hard per-bet cap on
    bankroll (variance control beyond half-Kelly); ``min_edge`` filters noise.
    A non-positive Kelly or sub-threshold edge resolves to 'pass' with $0 stake.
    """
    full = kelly_binary(model_prob, market_price, fee_buy=fee, fee_sell=fee)
    edge = model_prob - market_price
    ev = ev_binary(model_prob, market_price, fee_buy=fee, fee_sell=fee)
    sized = min(full * kelly_fraction, max_fraction)

    if full <= 0.0 or edge < min_edge:
        verdict, sized, stake = "pass", 0.0, 0.0
    else:
        stake = round(sized * bankroll, 2)
        verdict = "bet" if sized >= 0.03 else "lean"

    return BetSizing(
        model_prob=round(model_prob, 4),
        market_price=round(market_price, 4),
        baseline_prob=None if baseline_prob is None else round(baseline_prob, 4),
        edge=round(edge, 4),
        full_kelly=round(full, 4),
        kelly_fraction=kelly_fraction,
        sized_fraction=round(sized, 4),
        stake=stake,
        ev_per_contract=round(ev, 4),
        verdict=verdict,
    )
