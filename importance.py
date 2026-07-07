"""Match-importance score (0-100): how much each side needs the result.

Higher stakes widen scoring intent and reduce park-the-bus dynamics, shifting
goal expectations — so importance is both a model feature and context shown on
the dashboard. Knockout games are inherently high; group games scale with
what is still mathematically at stake.
"""
from __future__ import annotations

KNOCKOUT_BASE = {
    "Round of 32": 85,
    "Round of 16": 90,
    "Quarter-final": 94,
    "Semi-final": 97,
    "Final": 100,
    "Third place": 70,
}


def knockout_importance(round_name: str) -> int:
    return KNOCKOUT_BASE.get(round_name, 85)


def group_importance(
    *,
    can_still_advance_home: bool,
    can_still_advance_away: bool,
    decides_top_spot: bool,
    win_or_out: bool,
) -> int:
    """Group-stage importance from the qualification scenario.

    ``win_or_out`` marks a true must-win for at least one side — the highest
    group-stage tension.
    """
    score = 30
    if can_still_advance_home:
        score += 20
    if can_still_advance_away:
        score += 20
    if decides_top_spot:
        score += 15
    if win_or_out:
        score += 15
    return min(100, score)
