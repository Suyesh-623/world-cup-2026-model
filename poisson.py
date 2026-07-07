"""Bivariate-Poisson / Dixon-Coles match model.

Given expected goals for each side, build the full scoreline matrix (with the
Dixon-Coles low-score correction) and derive every betting market from one
coherent distribution: result (W/D/L), double chance, both-teams-to-score,
over/under totals, Asian/European handicaps, correct score, and first-half
markets.

The reason to lead with this over gradient-boosted trees: it encodes the
structure of football (goals are roughly Poisson, draws are slightly more
common than independence implies) so it stays well-calibrated on the tiny
2026-only sample, where a tree would overfit.
"""
from __future__ import annotations

import math

MAX_GOALS = 10                 # truncation point; mass beyond this is negligible
DEFAULT_RHO = -0.05            # Dixon-Coles low-score dependence (mild draw lift)
DEFAULT_FH_FRACTION = 0.45     # share of goals expected in the first half


# ── Scoreline distribution ──────────────────────────────────────────────────

def _poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _dc_tau(i: int, j: int, lam: float, mu: float, rho: float) -> float:
    """Dixon-Coles dependence adjustment on the four lowest scorelines."""
    if i == 0 and j == 0:
        return 1.0 - lam * mu * rho
    if i == 0 and j == 1:
        return 1.0 + lam * rho
    if i == 1 and j == 0:
        return 1.0 + mu * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def score_matrix(
    lam_home: float, lam_away: float, rho: float = DEFAULT_RHO, max_goals: int = MAX_GOALS
) -> list[list[float]]:
    """P(home = i, away = j) for i, j in 0..max_goals, renormalized to sum to 1."""
    m = [[0.0] * (max_goals + 1) for _ in range(max_goals + 1)]
    total = 0.0
    for i in range(max_goals + 1):
        ph = _poisson_pmf(i, lam_home)
        for j in range(max_goals + 1):
            p = ph * _poisson_pmf(j, lam_away) * _dc_tau(i, j, lam_home, lam_away, rho)
            p = max(p, 0.0)
            m[i][j] = p
            total += p
    # The DC correction + truncation perturb total mass; renormalize so every
    # derived market is a proper probability.
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            m[i][j] /= total
    return m


# ── Market derivations (operate on a scoreline matrix) ──────────────────────

def _result(m: list[list[float]]) -> tuple[float, float, float]:
    home = draw = away = 0.0
    for i, row in enumerate(m):
        for j, p in enumerate(row):
            if i > j:
                home += p
            elif i == j:
                draw += p
            else:
                away += p
    return home, draw, away


def _btts_yes(m: list[list[float]]) -> float:
    n = len(m)
    return sum(m[i][j] for i in range(1, n) for j in range(1, n))


def _over(m: list[list[float]], line: float) -> float:
    """P(total goals > line). For a .5 line, over = total >= floor(line) + 1."""
    need = math.floor(line) + 1
    n = len(m)
    return sum(m[i][j] for i in range(n) for j in range(n) if i + j >= need)


def _handicap_home(m: list[list[float]], line: float) -> float:
    """P(home covers handicap ``line``), e.g. -1.5 => home margin >= 2."""
    n = len(m)
    return sum(m[i][j] for i in range(n) for j in range(n) if (i - j) + line > 0)


def _handicap_away(m: list[list[float]], line: float) -> float:
    """P(away covers handicap ``line``), e.g. -1.5 => away margin >= 2.

    Needed because the favourite is often the nominal away side in a fixture
    (the official listing's order, not strength), so spreads run both ways.
    """
    n = len(m)
    return sum(m[i][j] for i in range(n) for j in range(n) if (j - i) + line > 0)


def _correct_scores(m: list[list[float]], top: int = 5) -> list[dict]:
    scores = [
        {"score": f"{i}-{j}", "prob": m[i][j]}
        for i in range(len(m))
        for j in range(len(m))
    ]
    scores.sort(key=lambda s: s["prob"], reverse=True)
    return scores[:top]


def _over_under(m: list[list[float]], line: float) -> dict:
    over = _over(m, line)
    return {"over": over, "under": 1.0 - over}


# ── Top-level: every market from one model ──────────────────────────────────

def match_markets(
    lam_home: float,
    lam_away: float,
    rho: float = DEFAULT_RHO,
    fh_fraction: float = DEFAULT_FH_FRACTION,
) -> dict:
    """All supported markets for a match with the given expected goals.

    First-half markets use a separate scoreline matrix built from the
    first-half share of each side's expected goals.
    """
    m = score_matrix(lam_home, lam_away, rho)
    home, draw, away = _result(m)
    btts_yes = _btts_yes(m)

    fh = score_matrix(lam_home * fh_fraction, lam_away * fh_fraction, rho)
    fh_home, fh_draw, fh_away = _result(fh)

    return {
        "expected_goals": {
            "home": round(lam_home, 3),
            "away": round(lam_away, 3),
            "total": round(lam_home + lam_away, 3),
        },
        "result": {"home": home, "draw": draw, "away": away},
        "double_chance": {
            "1X": home + draw,
            "12": home + away,
            "X2": draw + away,
        },
        "btts": {"yes": btts_yes, "no": 1.0 - btts_yes},
        "totals": {f"{ln}": _over_under(m, ln) for ln in (1.5, 2.5, 3.5)},
        "handicap": {
            "home_-0.5": _handicap_home(m, -0.5),
            "home_-1.5": _handicap_home(m, -1.5),
            "home_-2.5": _handicap_home(m, -2.5),
            "home_+0.5": _handicap_home(m, 0.5),
            "home_+1.5": _handicap_home(m, 1.5),
            "home_+2.5": _handicap_home(m, 2.5),
            "away_-0.5": _handicap_away(m, -0.5),
            "away_-1.5": _handicap_away(m, -1.5),
            "away_-2.5": _handicap_away(m, -2.5),
            "away_+0.5": _handicap_away(m, 0.5),
            "away_+1.5": _handicap_away(m, 1.5),
            "away_+2.5": _handicap_away(m, 2.5),
        },
        "first_half": {
            "result": {"home": fh_home, "draw": fh_draw, "away": fh_away},
            "totals": {f"{ln}": _over_under(fh, ln) for ln in (0.5, 1.5)},
        },
        "correct_score": _correct_scores(m, top=5),
    }


def lambdas_from_ratings(
    att_home: float,
    def_home: float,
    att_away: float,
    def_away: float,
    home_adv: float = 0.0,
    base: float = 1.35,
) -> tuple[float, float]:
    """Map team attack/defense ratings to expected goals.

    Ratings are log-scale multipliers around a league-average ``base`` rate;
    ``home_adv`` (log points) applies only when a side has true home advantage
    (a co-host playing at home). Kept simple and legible on purpose — the
    structure matters more than precision on this small a sample.
    """
    lam_home = base * math.exp(att_home - def_away + home_adv)
    lam_away = base * math.exp(att_away - def_home)
    return lam_home, lam_away
