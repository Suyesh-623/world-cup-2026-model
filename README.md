# World Cup 2026 — value-betting model

[![tests](https://github.com/Suyesh-623/world-cup-2026-model/actions/workflows/tests.yml/badge.svg)](https://github.com/Suyesh-623/world-cup-2026-model/actions/workflows/tests.yml)

A transparent, interpretable model that priced the 2026 World Cup knockout
rounds and graded its own predictions in public. Pure-Python core (pytest is
the only dependency to run the tests); the live dashboard at
https://www.suyeshniraula.com/world-cup reads the JSON this repo exports.

**Final record (tournament complete, Jul 2026):** 24/32 advancement calls
(75%), 107/192 across six markets (56%), and a fee-aware half-Kelly paper
ledger that finished net −$799 against live Bet365 prices. Misses included —
a results page that only shows wins is marketing. Method + limitations:
[Data & Method PDF](https://www.suyeshniraula.com/docs/world-cup-data-method.pdf).

## Layout

```
.
├── ingest.py         builds data/matches_2026.csv from sourced 2026 results
├── ratings.py        regularized Poisson MLE -> per-team att/def ratings
├── poisson.py        bivariate-Poisson / Dixon-Coles -> every market
├── kelly.py          fee-aware Kelly / EV sizing for binary event contracts
├── importance.py     match-importance (0-100) heuristic
├── bracket.py        knockout simulation through to a champion
├── fetch_odds.py     live market prices (TheStatsAPI; key stays in .env)
├── export_json.py    fixtures + engine -> the dashboard's predictions JSON
├── data/
│   ├── matches_2026.csv   the 200-match training set (72 WC group + 128 friendlies)
│   ├── ratings.json       fitted ratings with per-team game counts
│   └── bracket.json       the simulated knockout bracket
├── tests/            pinned math + coherence tests
└── requirements.txt
```

## Run

```bash
# the code imports itself as the `model` package, so clone it under that name
git clone https://github.com/Suyesh-623/world-cup-2026-model.git model
python3 -m venv .venv
.venv/bin/pip install -r model/requirements.txt   # or just: pip install pytest

# tests — reproduce the worked Kelly examples + market coherence
.venv/bin/python -m pytest model -q

# regenerate the dashboard data
PYTHONPATH=. .venv/bin/python -m model.export_json
```

## The math

- **Kelly (binary contract):** `f* = (p - c) / (1 - c)`, half-Kelly `= f*/2`,
  fee-adjusted for the ~1c/contract each side, capped per bet. The tests pin it
  to worked examples (Switzerland +155 -> 1.47% half; Morocco 35c -> 7.31% half).
- **Poisson core:** team attack/defense ratings — fit by regularized Poisson
  MLE on the 200 real 2026 matches in `data/matches_2026.csv` (World-Cup
  weighted) — produce expected goals, then a full scoreline matrix with the
  Dixon-Coles low-score correction. Every market derives from that one
  distribution: result, totals, BTTS, correct score, advancement.
- **Walk-forward:** after each knockout round the bracket re-seeded on the real
  winners and the ratings refit before pricing the next round, so later
  predictions build on actual results, including the model's own misses.

## Honest limitations

200 matches across 48+ teams is a small sample; the model sees final scores
only (no xG, lineups, or injuries); friendlies are noisy even down-weighted;
and only 6 of the 32 knockout games had live prices attached, so the betting
ledger proves nothing on its own. Forecasts, not betting advice. Execution
always stayed manual.

## License

MIT, see [LICENSE](LICENSE).
