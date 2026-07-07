"""Build model/data/matches_2026.csv from sourced 2026 results only.

Two sources, both fetched live this session (nothing from memory):
  * World Cup 2026 group-stage results — transcribed verbatim from the
    Wikipedia group pages (Group A-L), 54 matches played through Jun 24.
  * 2026 international friendlies — parsed from a firecrawl scrape of
    worldfootball.net, kept only when at least one side is a WC team.

Output columns: date, competition (WC|Friendly), home, away, hg, ag.
The CSV is the auditable source of truth the rating fit consumes.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FRIENDLIES_MD = REPO / ".firecrawl" / "wf-friendlies.md"
OUT = REPO / "model" / "data" / "matches_2026.csv"

# ── The 48 qualified teams (canonical names) ────────────────────────────────
WC_TEAMS = {
    "Mexico", "South Africa", "South Korea", "Czechia",
    "Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland",
    "Brazil", "Morocco", "Haiti", "Scotland",
    "United States", "Paraguay", "Australia", "Turkey",
    "Germany", "Curaçao", "Ivory Coast", "Ecuador",
    "Netherlands", "Japan", "Sweden", "Tunisia",
    "Belgium", "Egypt", "Iran", "New Zealand",
    "Spain", "Cape Verde", "Saudi Arabia", "Uruguay",
    "France", "Senegal", "Iraq", "Norway",
    "Argentina", "Algeria", "Austria", "Jordan",
    "Portugal", "DR Congo", "Uzbekistan", "Colombia",
    "England", "Croatia", "Ghana", "Panama",
}

# Map source spellings -> canonical.
NORMALIZE = {
    "Czech Republic": "Czechia",
    "Cape Verde Islands": "Cape Verde",
    "USA": "United States",
    "United States of America": "United States",
    "Korea Republic": "South Korea",
    "Türkiye": "Turkey",
    "Turkiye": "Turkey",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Curacao": "Curaçao",
    "Cote d'Ivoire": "Ivory Coast",
    "Côte d'Ivoire": "Ivory Coast",
    "IR Iran": "Iran",
    "Congo DR": "DR Congo",
}


def canon(name: str) -> str:
    name = name.strip()
    return NORMALIZE.get(name, name)


# Penalty-shootout draws: worldfootball lists the SHOOTOUT score as the result
# (tagged "pso"), so the raw score is a lie for the rating model. We override
# these with the verified regular-time score (the actual draw). Any shootout
# match without a verified score here is dropped, never ingested.
PSO_OVERRIDES: dict[str, tuple[int, int]] = {
    "ma11876209": (1, 1),  # Cape Verde 1-1 Finland (CV won 4-2 on pens) — ESPN/Fox/Sofascore
    "ma11912452": (0, 0),  # Uzbekistan 0-0 Venezuela (UZB won 5-4 on pens) — ESPN/VAVEL/Sofascore
}


# ── World Cup 2026 results (verbatim from Wikipedia group pages) ─────────────
# (date, home, away, home_goals, away_goals)
WC_MATCHES = [
    ("2026-06-11", "Mexico", "South Africa", 2, 0),
    ("2026-06-11", "South Korea", "Czechia", 2, 1),
    ("2026-06-18", "Czechia", "South Africa", 1, 1),
    ("2026-06-18", "Mexico", "South Korea", 1, 0),
    ("2026-06-24", "Czechia", "Mexico", 0, 3),
    ("2026-06-24", "South Africa", "South Korea", 1, 0),
    ("2026-06-12", "Canada", "Bosnia and Herzegovina", 1, 1),
    ("2026-06-13", "Qatar", "Switzerland", 1, 1),
    ("2026-06-18", "Switzerland", "Bosnia and Herzegovina", 4, 1),
    ("2026-06-18", "Canada", "Qatar", 6, 0),
    ("2026-06-24", "Switzerland", "Canada", 2, 1),
    ("2026-06-24", "Bosnia and Herzegovina", "Qatar", 3, 1),
    ("2026-06-13", "Brazil", "Morocco", 1, 1),
    ("2026-06-13", "Haiti", "Scotland", 0, 1),
    ("2026-06-19", "Scotland", "Morocco", 0, 1),
    ("2026-06-19", "Brazil", "Haiti", 3, 0),
    ("2026-06-24", "Scotland", "Brazil", 0, 3),
    ("2026-06-24", "Morocco", "Haiti", 4, 2),
    ("2026-06-12", "United States", "Paraguay", 4, 1),
    ("2026-06-13", "Australia", "Turkey", 2, 0),
    ("2026-06-19", "United States", "Australia", 2, 0),
    ("2026-06-19", "Turkey", "Paraguay", 0, 1),
    ("2026-06-14", "Germany", "Curaçao", 7, 1),
    ("2026-06-14", "Ivory Coast", "Ecuador", 1, 0),
    ("2026-06-20", "Germany", "Ivory Coast", 2, 1),
    ("2026-06-20", "Ecuador", "Curaçao", 0, 0),
    ("2026-06-14", "Netherlands", "Japan", 2, 2),
    ("2026-06-14", "Sweden", "Tunisia", 5, 1),
    ("2026-06-20", "Netherlands", "Sweden", 5, 1),
    ("2026-06-20", "Tunisia", "Japan", 0, 4),
    ("2026-06-15", "Belgium", "Egypt", 1, 1),
    ("2026-06-15", "Iran", "New Zealand", 2, 2),
    ("2026-06-21", "Belgium", "Iran", 0, 0),
    ("2026-06-21", "New Zealand", "Egypt", 1, 3),
    ("2026-06-15", "Spain", "Cape Verde", 0, 0),
    ("2026-06-15", "Saudi Arabia", "Uruguay", 1, 1),
    ("2026-06-21", "Spain", "Saudi Arabia", 4, 0),
    ("2026-06-21", "Uruguay", "Cape Verde", 2, 2),
    ("2026-06-16", "France", "Senegal", 3, 1),
    ("2026-06-16", "Iraq", "Norway", 1, 4),
    ("2026-06-22", "France", "Iraq", 3, 0),
    ("2026-06-22", "Norway", "Senegal", 3, 2),
    ("2026-06-16", "Argentina", "Algeria", 3, 0),
    ("2026-06-16", "Austria", "Jordan", 3, 1),
    ("2026-06-22", "Argentina", "Austria", 2, 0),
    ("2026-06-22", "Jordan", "Algeria", 1, 2),
    ("2026-06-17", "Portugal", "DR Congo", 1, 1),
    ("2026-06-17", "Uzbekistan", "Colombia", 1, 3),
    ("2026-06-23", "Portugal", "Uzbekistan", 5, 0),
    ("2026-06-23", "Colombia", "DR Congo", 1, 0),
    ("2026-06-17", "England", "Croatia", 4, 2),
    ("2026-06-17", "Ghana", "Panama", 1, 0),
    ("2026-06-23", "England", "Ghana", 0, 0),
    ("2026-06-23", "Panama", "Croatia", 0, 1),
    # Matchday 3 (final group games), verbatim from Wikipedia group pages.
    ("2026-06-25", "Turkey", "United States", 3, 2),
    ("2026-06-25", "Paraguay", "Australia", 0, 0),
    ("2026-06-25", "Curaçao", "Ivory Coast", 0, 2),
    ("2026-06-25", "Ecuador", "Germany", 2, 1),
    ("2026-06-25", "Japan", "Sweden", 1, 1),
    ("2026-06-25", "Tunisia", "Netherlands", 1, 3),
    ("2026-06-26", "Egypt", "Iran", 1, 1),
    ("2026-06-26", "New Zealand", "Belgium", 1, 5),
    ("2026-06-26", "Cape Verde", "Saudi Arabia", 0, 0),
    ("2026-06-26", "Uruguay", "Spain", 0, 1),
    ("2026-06-26", "Norway", "France", 1, 4),
    ("2026-06-26", "Senegal", "Iraq", 5, 0),
    ("2026-06-27", "Algeria", "Austria", 3, 3),
    ("2026-06-27", "Jordan", "Argentina", 1, 3),
    ("2026-06-27", "Colombia", "Portugal", 0, 0),
    ("2026-06-27", "DR Congo", "Uzbekistan", 3, 1),
    ("2026-06-27", "Panama", "England", 0, 2),
    ("2026-06-27", "Croatia", "Ghana", 2, 1),
]

# ── Friendly parsing from the firecrawl scrape ──────────────────────────────
SCORE_RE = re.compile(r"^\[(\d+):(\d+)\]\(.*?/(ma\d+)/")
LABEL_RE = re.compile(
    r"\[Football Friendlies \w+ (.+?) - (.+?) on (\d{2})\.(\d{2})\.2026 [\d:]+\]\(.*?/(ma\d+)/"
)


def parse_friendlies() -> list[tuple]:
    if not FRIENDLIES_MD.exists():
        print(f"  (no friendlies scrape at {FRIENDLIES_MD.relative_to(REPO)} — skipping)")
        return []

    scores: dict[str, tuple[int, int]] = {}
    labels: dict[str, tuple[str, str, str]] = {}  # maID -> (home, away, iso_date)
    shootouts: set[str] = set()
    last_maid: str | None = None
    for raw in FRIENDLIES_MD.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line == "pso" and last_maid:  # this match was decided on penalties
            shootouts.add(last_maid)
            continue
        s = SCORE_RE.match(line)
        if s:
            last_maid = s.group(3)
            scores[last_maid] = (int(s.group(1)), int(s.group(2)))
            continue
        m = LABEL_RE.search(line)
        if m:
            home, away, dd, mm, maid = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
            labels[maid] = (canon(home), canon(away), f"2026-{mm}-{dd}")

    rows: list[tuple] = []
    corrected = dropped = 0
    for maid, (home, away, date) in labels.items():
        if maid not in scores:
            continue  # not yet played / no score
        if home not in WC_TEAMS and away not in WC_TEAMS:
            continue  # both non-WC — irrelevant
        if maid in shootouts:
            # Never ingest a shootout score; use a verified regular-time score
            # if we have one, otherwise drop rather than record a fiction.
            if maid in PSO_OVERRIDES:
                hg, ag = PSO_OVERRIDES[maid]
                corrected += 1
            else:
                dropped += 1
                continue
        else:
            hg, ag = scores[maid]
        rows.append((date, "Friendly", home, away, hg, ag))
    rows.sort()
    if shootouts:
        print(f"  penalty shootouts: {corrected} corrected to regular-time draw, {dropped} dropped (unverified)")
    return rows


def main() -> None:
    wc_rows = [(d, "WC", h, a, hg, ag) for (d, h, a, hg, ag) in WC_MATCHES]
    fr_rows = parse_friendlies()
    all_rows = sorted(wc_rows + fr_rows)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "competition", "home", "away", "hg", "ag"])
        w.writerows(all_rows)

    # Summary for the human sanity-check.
    counts: dict[str, int] = {t: 0 for t in WC_TEAMS}
    for _, _, h, a, _, _ in all_rows:
        if h in counts:
            counts[h] += 1
        if a in counts:
            counts[a] += 1
    print(f"Wrote {OUT.relative_to(REPO)}: {len(wc_rows)} WC + {len(fr_rows)} friendly = {len(all_rows)} matches")
    miss = [t for t, c in counts.items() if c == 0]
    print("games per WC team (2026):")
    for t in sorted(counts, key=lambda x: -counts[x]):
        print(f"  {counts[t]:>2}  {t}")
    if miss:
        print("WARNING — WC teams with zero 2026 matches found:", miss)


if __name__ == "__main__":
    main()
