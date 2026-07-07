"""Round-of-32 knockout engine: per-tie markets + advancement + full bracket sim.

Uses the fitted ratings (model/data/ratings.json). Knockouts are neutral-venue,
so home_adv=0. Advancement adds 30' extra time (Poisson at 1/3 rate) and a
50/50 shootout if still level, so P(advance) is a real knockout number, not
just the 90-minute win prob. Writes model/data/bracket.json for the visual and
prints a comprehensive per-tie prediction block.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from model.poisson import lambdas_from_ratings, score_matrix

REPO = Path(__file__).resolve().parents[1]
R = json.loads((REPO / "model" / "data" / "ratings.json").read_text())
T = R["teams"]
BASE = R["base"]

# Confirmed Round of 32 (match number: home, away) and the bracket flow.
R32 = [
    (73, "South Africa", "Canada"),
    (74, "Germany", "Paraguay"),
    (75, "Netherlands", "Morocco"),
    (76, "Brazil", "Japan"),
    (77, "France", "Sweden"),
    (78, "Ivory Coast", "Norway"),
    (79, "Mexico", "Ecuador"),
    (80, "England", "DR Congo"),
    (81, "United States", "Bosnia and Herzegovina"),
    (82, "Belgium", "Senegal"),
    (83, "Portugal", "Croatia"),
    (84, "Spain", "Austria"),
    (85, "Switzerland", "Algeria"),
    (86, "Argentina", "Cape Verde"),
    (87, "Colombia", "Ghana"),
    (88, "Australia", "Egypt"),
]
# Round of 16 pairings by R32 match-winner.
R16 = [(89, 74, 77), (90, 73, 75), (91, 76, 78), (92, 79, 80),
       (93, 83, 84), (94, 81, 82), (95, 86, 88), (96, 85, 87)]
# Official bracket: QF pairs consecutive R16 winners; SF1 = left half (97,98),
# SF2 = right half (99,100). (Matches the published 2026 bracket.)
QF = [(97, 89, 90), (98, 93, 94), (99, 91, 92), (100, 95, 96)]
SF = [("SF1", 97, 98), ("SF2", 99, 100)]


def lambdas(a: str, b: str) -> tuple[float, float]:
    ra, rb = T[a], T[b]
    return lambdas_from_ratings(ra["att"], ra["def"], rb["att"], rb["def"], 0.0, BASE)


def result_probs(m: list[list[float]]) -> tuple[float, float, float]:
    h = d = a = 0.0
    for i, row in enumerate(m):
        for j, p in enumerate(row):
            if i > j: h += p
            elif i == j: d += p
            else: a += p
    return h, d, a


def tie(a: str, b: str) -> dict:
    la, lb = lambdas(a, b)
    m = score_matrix(la, lb)
    h, d, aw = result_probs(m)
    # extra time: 30 min at 1/3 of the per-90 rate
    me = score_matrix(la / 3.0, lb / 3.0)
    eh, ed, ea = result_probs(me)
    adv_home = h + d * (eh + ed * 0.5)   # win in 90, or draw then win ET / pens
    n = len(m)
    over = lambda L: sum(m[i][j] for i in range(n) for j in range(n) if i + j > L)
    btts = sum(m[i][j] for i in range(1, n) for j in range(1, n))
    cs = max(((i, j, m[i][j]) for i in range(n) for j in range(n)), key=lambda x: x[2])
    return {
        "home": a, "away": b, "xg": (round(la, 2), round(lb, 2)),
        "win": round(h, 3), "draw": round(d, 3), "lose": round(aw, 3),
        "adv_home": round(adv_home, 3), "adv_away": round(1 - adv_home, 3),
        "o15": round(over(1.5), 3), "o25": round(over(2.5), 3), "o35": round(over(3.5), 3),
        "btts": round(btts, 3),
        "cs_home_cleansheet": round(sum(m[i][0] for i in range(n)), 3),
        "cs_away_cleansheet": round(sum(m[0][j] for j in range(n)), 3),
        "top_score": f"{cs[0]}-{cs[1]}", "top_score_p": round(cs[2], 3),
        "winner": a if adv_home >= 0.5 else b,
    }


def main() -> None:
    games = {n: tie(a, b) for n, a, b in R32}
    win = {n: games[n]["winner"] for n in games}  # R32 winners by match no.

    rounds = {"R32": games}
    # Round of 16
    r16 = {}
    for num, wa, wb in R16:
        t = tie(win[wa], win[wb]); r16[num] = t; win[num] = t["winner"]
    rounds["R16"] = r16
    # Quarter-finals
    qf = {}
    for name, wa, wb in QF:
        t = tie(win[wa], win[wb]); qf[name] = t; win[name] = t["winner"]
    rounds["QF"] = qf
    # Semi-finals
    sf = {}
    for name, wa, wb in SF:
        t = tie(win[wa], win[wb]); sf[name] = t; win[name] = t["winner"]
    rounds["SF"] = sf
    # Final
    final = tie(win["SF1"], win["SF2"])
    rounds["Final"] = {"FINAL": final}
    champion = final["winner"]

    (REPO / "model" / "data" / "bracket.json").write_text(
        json.dumps({"rounds": rounds, "champion": champion}, indent=2) + "\n"
    )

    print("=== ROUND OF 32 — comprehensive model predictions ===\n")
    for num, a, b in R32:
        g = games[num]
        print(f"[{num}] {a} vs {b}   xG {g['xg'][0]}-{g['xg'][1]}")
        print(f"     90': {a} {g['win']*100:.0f}% / draw {g['draw']*100:.0f}% / {b} {g['lose']*100:.0f}%"
              f"   |  ADVANCE: {a} {g['adv_home']*100:.0f}% / {b} {g['adv_away']*100:.0f}%  -> {g['winner'].upper()}")
        print(f"     O1.5 {g['o15']*100:.0f}% · O2.5 {g['o25']*100:.0f}% · O3.5 {g['o35']*100:.0f}%"
              f"  |  BTTS {g['btts']*100:.0f}%  |  likely score {g['top_score']} ({g['top_score_p']*100:.0f}%)")
    print("\n=== PREDICTED PATH ===")
    print("R16:", " | ".join(f"{r16[n]['home']} d. ...→ {r16[n]['winner']}" for n in sorted(r16)))
    print("R16 winners:", ", ".join(r16[n]["winner"] for n in sorted(r16)))
    print("QF winners:", ", ".join(qf[k]["winner"] for k, *_ in QF))
    print("SF:", " / ".join(f"{sf[s]['home']} vs {sf[s]['away']} -> {sf[s]['winner']}" for s, *_ in SF))
    print(f"FINAL: {final['home']} vs {final['away']}  ->  CHAMPION: {champion}")


if __name__ == "__main__":
    main()
