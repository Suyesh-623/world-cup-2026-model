"""Build src/data/world-cup/predictions.json from the engine + fixtures.

For each fixture: ratings -> expected goals -> every market (Poisson), then
fee-aware half-Kelly sizing against the market price. The best +EV selection
per match is flagged for the dashboard hero panel. Run with:

    PYTHONPATH=. python -m model.export_json
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from model.importance import knockout_importance
from model.kelly import evaluate_bet
from model.poisson import lambdas_from_ratings, match_markets

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "model" / "data" / "fixtures.json"
OUT = REPO / "src" / "data" / "world-cup" / "predictions.json"

BANKROLL = 10_000
KELLY_FRACTION = 0.5
FEE = 0.01

# Ratings fit from real 2026 matches (model/ratings.py). When present they
# replace the placeholder att/def carried inline in fixtures.json.
RATINGS_PATH = REPO / "model" / "data" / "ratings.json"
RATINGS = json.loads(RATINGS_PATH.read_text()) if RATINGS_PATH.exists() else None


def resolve(mk: dict, key: str) -> float:
    """Map a market key (e.g. 'total_over_2.5') to its model probability."""
    if key.startswith("result_"):
        return mk["result"][key.split("_", 1)[1]]
    if key.startswith("btts_"):
        return mk["btts"][key.split("_", 1)[1]]
    if key.startswith("total_"):
        _, side, line = key.split("_")
        return mk["totals"][line][side]
    if key.startswith("handicap_"):
        return mk["handicap"][key[len("handicap_"):]]
    if key.startswith("fh_over_"):
        return mk["first_half"]["totals"][key[len("fh_over_"):]]["over"]
    if key.startswith("fh_result_"):
        return mk["first_half"]["result"][key.split("_", 2)[2]]
    raise KeyError(f"Unknown market key: {key}")


def build_match(fx: dict, default_round: str, live_prices: bool) -> dict:
    home, away = fx["home"], fx["away"]
    rt = RATINGS["teams"] if RATINGS else None
    if rt and home["name"] in rt and away["name"] in rt:
        # Fitted 2026 ratings; WC venues are neutral, so no home advantage.
        rh, ra = rt[home["name"]], rt[away["name"]]
        lam_h, lam_a = lambdas_from_ratings(
            rh["att"], rh["def"], ra["att"], ra["def"], home_adv=0.0, base=RATINGS["base"]
        )
    else:
        lam_h, lam_a = lambdas_from_ratings(
            home["att"], home["def"], away["att"], away["def"], home.get("homeAdv", 0.0)
        )
    mk = match_markets(lam_h, lam_a)

    markets: list[dict] = []
    for spec in fx["markets"]:
        model_p = resolve(mk, spec["key"])
        # Until the Kalshi feed is wired, we carry NO market price — showing an
        # edge against a placeholder price would be fabricated. The model
        # probability is real; the edge is computed only against live odds.
        price = spec.get("market") if live_prices else None
        baseline = spec.get("baseline") if live_prices else None
        entry = {
            "key": spec["key"],
            "group": spec["group"],
            "label": spec["label"],
            "model": round(model_p, 4),
            "market": None if price is None else round(price, 4),
            "baseline": None if baseline is None else round(baseline, 4),
        }
        if price is not None:
            d = evaluate_bet(
                model_p, price, BANKROLL,
                baseline_prob=baseline, kelly_fraction=KELLY_FRACTION, fee=FEE,
            )
            entry.update(
                edge=d.edge, fullKelly=d.full_kelly, halfKelly=d.sized_fraction,
                stake=d.stake, ev=d.ev_per_contract, verdict=d.verdict,
            )
        else:
            entry.update(
                edge=None, fullKelly=None, halfKelly=None,
                stake=None, ev=None, verdict="no-market",
            )
        markets.append(entry)

    actionable = [m for m in markets if m["verdict"] in ("bet", "lean")]
    best = max(actionable, key=lambda m: m["halfKelly"], default=None)
    rnd = fx.get("round", default_round)

    res = mk["result"]
    fav_side = max(("home", "draw", "away"), key=lambda s: res[s])
    fav_team = home["name"] if fav_side == "home" else away["name"] if fav_side == "away" else "Draw"
    model_favorite = {"side": fav_side, "team": fav_team, "prob": round(res[fav_side], 4)}

    return {
        "id": fx["id"],
        "group": fx.get("group", rnd),
        "round": rnd,
        "kickoff": fx["kickoff"],
        "kickoffLabel": fx["kickoffLabel"],
        "importance": fx.get("importance", knockout_importance(rnd)),
        "venue": fx["venue"],
        "weather": fx["weather"],
        "home": {k: home[k] for k in ("code", "code3", "name", "fifaRank")},
        "away": {k: away[k] for k in ("code", "code3", "name", "fifaRank")},
        "expectedGoals": mk["expected_goals"],
        "modelFavorite": model_favorite,
        "markets": markets,
        "bestBetKey": None if best is None else best["key"],
    }


def main() -> None:
    data = json.loads(FIXTURES.read_text())
    default_round = data.get("round", "Round of 32")
    live_prices = data.get("pricesAreLive", False)
    matches = [build_match(fx, default_round, live_prices) for fx in data["fixtures"]]

    out = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataMode": data.get("dataMode", "sample"),
        "oddsConnected": live_prices,
        "round": default_round,
        "bankroll": BANKROLL,
        "kellyFraction": KELLY_FRACTION,
        "fee": FEE,
        "matches": matches,
        "modelCard": {
            "method": "Bivariate-Poisson / Dixon-Coles; ratings fit by regularized Poisson MLE.",
            "trainedOn": (
                "Fitted on 182 sourced 2026 matches (54 World Cup + 128 friendlies)."
                if RATINGS else "Prior-seeded ratings (no fit)."
            ),
            "markets": "Result, double chance, BTTS, totals, handicap, first half, correct score.",
            "note": data.get("note", ""),
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")

    print(f"Wrote {OUT.relative_to(REPO)} — {len(matches)} matches")
    for m in matches:
        best = next((x for x in m["markets"] if x["key"] == m["bestBetKey"]), None)
        tag = (
            "no +EV"
            if best is None
            else f'{best["label"]} (edge {best["edge"]:+.3f}, half {best["halfKelly"]:.3f}, ${best["stake"]:.0f})'
        )
        eg = m["expectedGoals"]
        print(
            f'  {m["home"]["name"]:<12} v {m["away"]["name"]:<10} '
            f'xg {eg["home"]:.2f}-{eg["away"]:.2f} | best: {tag}'
        )


if __name__ == "__main__":
    main()
