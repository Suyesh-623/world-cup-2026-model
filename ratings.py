"""Fit team attack/defense ratings from the 2026 matches via Poisson MLE.

Model (one coherent goal process, same family as poisson.py):

    log E[home goals] = mu + att[home] - def[away] + gamma
    log E[away goals] = mu + att[away] - def[home]

Fit by gradient ascent on the L2-regularized Poisson log-likelihood. The
ridge penalty is what makes this trustworthy on a tiny 2026-only sample: a
team with one lopsided friendly is shrunk toward average instead of being
treated as world-class. ``att`` and ``def`` come out centered near 0, so they
drop straight into ``lambdas_from_ratings`` with ``base = exp(mu)``.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CSV_PATH = REPO / "model" / "data" / "matches_2026.csv"
OUT = REPO / "model" / "data" / "ratings.json"

REG = 3.0        # ridge strength on att/def (higher = more shrinkage)
LR = 0.6
ITERS = 4000


WC_WEIGHT = 2.5  # World Cup games count more than friendlies (soft-opponent inflation)


def load_matches() -> list[tuple]:
    with CSV_PATH.open(encoding="utf-8") as f:
        return [
            (r["home"], r["away"], int(r["hg"]), int(r["ag"]),
             WC_WEIGHT if r["competition"] == "WC" else 1.0)
            for r in csv.DictReader(f)
        ]


def fit(matches: list[tuple[str, str, int, int]]) -> dict:
    teams = sorted({t for h, a, *_ in matches for t in (h, a)})
    idx = {t: i for i, t in enumerate(teams)}
    n, m = len(teams), len(matches)

    att = [0.0] * n
    def_ = [0.0] * n
    total_goals = sum(hg + ag for _, _, hg, ag, _ in matches)
    mu = math.log(max(total_goals / (2 * m), 0.1))
    gamma = 0.20

    pre = [(idx[h], idx[a], hg, ag, w) for h, a, hg, ag, w in matches]
    wsum = sum(w for *_, w in pre)

    for _ in range(ITERS):
        g_att = [0.0] * n
        g_def = [0.0] * n
        g_mu = 0.0
        g_gamma = 0.0
        for h, a, hg, ag, w in pre:
            lh = math.exp(mu + att[h] - def_[a] + gamma)
            la = math.exp(mu + att[a] - def_[h])
            eh, ea = (hg - lh) * w, (ag - la) * w
            g_att[h] += eh
            g_def[a] -= eh
            g_att[a] += ea
            g_def[h] -= ea
            g_mu += eh + ea
            g_gamma += eh
        for t in range(n):
            g_att[t] -= REG * att[t]
            g_def[t] -= REG * def_[t]
            att[t] += LR * g_att[t] / wsum
            def_[t] += LR * g_def[t] / wsum
        mu += LR * g_mu / wsum
        gamma += LR * g_gamma / wsum

    # Recenter att/def to mean 0, folding the shift into mu (keeps lambdas
    # identical but makes the ratings comparable across teams).
    a_bar = sum(att) / n
    d_bar = sum(def_) / n
    att = [x - a_bar for x in att]
    def_ = [x - d_bar for x in def_]
    mu = mu + a_bar - d_bar

    games = {t: 0 for t in teams}
    for h, a, *_ in matches:
        games[h] += 1
        games[a] += 1

    return {
        "base": round(math.exp(mu), 4),
        "homeAdv": round(gamma, 4),
        "teams": {
            t: {"att": round(att[idx[t]], 4), "def": round(def_[idx[t]], 4), "games": games[t]}
            for t in teams
        },
    }


def main() -> None:
    matches = load_matches()
    fitted = fit(matches)
    fitted["fittedFrom"] = f"{len(matches)} matches (2026 only), regularized Poisson MLE"
    OUT.write_text(json.dumps(fitted, indent=2) + "\n")

    print(f"Fit {len(fitted['teams'])} teams from {len(matches)} matches | "
          f"base={fitted['base']} homeAdv={fitted['homeAdv']}")
    # Net rating = att + def (overall strength) for a quick eyeball.
    wc = {t: v for t, v in fitted["teams"].items()}
    ranked = sorted(wc.items(), key=lambda kv: -(kv[1]["att"] + kv[1]["def"]))
    print("strongest (att+def):")
    for t, v in ranked[:12]:
        print(f"  {v['att']+v['def']:+.2f}  att {v['att']:+.2f} def {v['def']:+.2f}  {t} ({v['games']}g)")
    print("weakest:")
    for t, v in ranked[-8:]:
        print(f"  {v['att']+v['def']:+.2f}  att {v['att']:+.2f} def {v['def']:+.2f}  {t} ({v['games']}g)")


if __name__ == "__main__":
    main()
