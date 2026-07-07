"""Export the Round of 32 ties to src/data/world-cup/predictions.json for the
light knockout dashboard cards. Reads model/data/bracket.json (R32 round)."""
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
B = json.loads((REPO / "model" / "data" / "bracket.json").read_text())
OUT = REPO / "src" / "data" / "world-cup" / "predictions.json"

CODE3 = {
    "South Africa": "RSA", "Canada": "CAN", "Germany": "GER", "Paraguay": "PAR",
    "Netherlands": "NED", "Morocco": "MAR", "Brazil": "BRA", "Japan": "JPN",
    "France": "FRA", "Sweden": "SWE", "Ivory Coast": "CIV", "Norway": "NOR",
    "Mexico": "MEX", "Ecuador": "ECU", "England": "ENG", "DR Congo": "COD",
    "United States": "USA", "Bosnia and Herzegovina": "BIH", "Belgium": "BEL",
    "Senegal": "SEN", "Portugal": "POR", "Croatia": "CRO", "Spain": "ESP",
    "Austria": "AUT", "Switzerland": "SUI", "Algeria": "ALG", "Argentina": "ARG",
    "Cape Verde": "CPV", "Colombia": "COL", "Ghana": "GHA", "Australia": "AUS", "Egypt": "EGY",
}
ISO2 = {
    "South Africa": "za", "Canada": "ca", "Germany": "de", "Paraguay": "py",
    "Netherlands": "nl", "Morocco": "ma", "Brazil": "br", "Japan": "jp",
    "France": "fr", "Sweden": "se", "Ivory Coast": "ci", "Norway": "no",
    "Mexico": "mx", "Ecuador": "ec", "England": "gb-eng", "DR Congo": "cd",
    "United States": "us", "Bosnia and Herzegovina": "ba", "Belgium": "be",
    "Senegal": "sn", "Portugal": "pt", "Croatia": "hr", "Spain": "es",
    "Austria": "at", "Switzerland": "ch", "Algeria": "dz", "Argentina": "ar",
    "Cape Verde": "cv", "Colombia": "co", "Ghana": "gh", "Australia": "au", "Egypt": "eg",
}
DATE = {73: "Sun Jun 28", 74: "Mon Jun 29", 75: "Mon Jun 29", 76: "Mon Jun 29",
        77: "Tue Jun 30", 78: "Tue Jun 30", 79: "Tue Jun 30", 80: "Wed Jul 1",
        81: "Wed Jul 1", 82: "Wed Jul 1", 83: "Thu Jul 2", 84: "Thu Jul 2",
        85: "Thu Jul 2", 86: "Fri Jul 3", 87: "Fri Jul 3", 88: "Fri Jul 3"}
ORDER = [73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88]


def team(name):
    return {"code": ISO2[name], "code3": CODE3[name], "name": name, "fifaRank": None}


def mk(key, group, label, p):
    return {"key": key, "group": group, "label": label, "model": round(p, 3),
            "market": None, "baseline": None, "edge": None, "fullKelly": None,
            "halfKelly": None, "stake": None, "ev": None, "verdict": "no-market"}


def main():
    r32 = {int(k): v for k, v in B["rounds"]["R32"].items()}
    matches = []
    for num in ORDER:
        g = r32[num]
        h, a = g["home"], g["away"]
        win_home = g["winner"] == h
        matches.append({
            "id": f"{CODE3[h].lower()}-{CODE3[a].lower()}",
            "round": "Round of 32",
            "kickoff": DATE[num], "kickoffLabel": DATE[num],
            "importance": 90,
            "venue": {"name": "", "city": "", "lat": 0, "lon": 0},
            "weather": {"tempF": 0, "condition": ""},
            "home": team(h), "away": team(a),
            "expectedGoals": {"home": g["xg"][0], "away": g["xg"][1],
                              "total": round(g["xg"][0] + g["xg"][1], 2)},
            "modelFavorite": {"side": "home" if win_home else "away",
                              "team": g["winner"], "prob": g["adv_home"] if win_home else g["adv_away"]},
            "likelyScore": g["top_score"],
            "markets": [
                mk("result_home", "Result", f"{h} win", g["win"]),
                mk("result_draw", "Result", "Draw (90′)", g["draw"]),
                mk("result_away", "Result", f"{a} win", g["lose"]),
                mk("total_over_1.5", "Total goals", "Over 1.5", g["o15"]),
                mk("total_over_2.5", "Total goals", "Over 2.5", g["o25"]),
                mk("total_over_3.5", "Total goals", "Over 3.5", g["o35"]),
                mk("btts_yes", "Both teams score", "Yes", g["btts"]),
            ],
            "bestBetKey": None,
        })
    out = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataMode": "model", "oddsConnected": False, "round": "Round of 32",
        "bankroll": 10000, "kellyFraction": 0.5, "fee": 0.01,
        "champion": B["champion"], "matches": matches,
        "modelCard": {
            "method": "Bivariate-Poisson / Dixon-Coles; ratings fit by regularized Poisson MLE (World-Cup weighted).",
            "trainedOn": "200 real 2026 matches — full group stage (72) + 128 international friendlies.",
            "markets": "Result, advancement (90′ + extra time + penalties), totals, BTTS.",
            "note": "Knockout predictions. Each tie's favourite to advance is the model's pick; live odds not connected.",
        },
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(REPO)} — {len(matches)} R32 ties, champion {B['champion']}")


if __name__ == "__main__":
    main()
