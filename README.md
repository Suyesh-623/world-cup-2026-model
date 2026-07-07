# World Cup 2026 — value-betting model

A transparent, interpretable model for finding positive-EV bets on the 2026
World Cup and sizing them with fee-aware half-Kelly. Pure-Python core (no heavy
deps to run or test); the live dashboard at https://suyesh-niraula.vercel.app/world-cup reads the JSON this exports.

## Layout

```
.
├── kelly.py          fee-aware Kelly / EV sizing for binary event contracts
├── poisson.py        bivariate-Poisson / Dixon-Coles -> every market
├── importance.py     match-importance (0-100) heuristic
├── export_json.py    fixtures + engine -> src/data/world-cup/predictions.json
├── data/fixtures.json  sample Round-of-32 fixtures (ratings, prices, venues)
├── tests/            pinned math + coherence tests
└── requirements.txt  pytest only for the core; the rest is for Phase 1.1+
```

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt   # or just: pip install pytest

# tests — reproduce the worked Kelly examples + market coherence
PYTHONPATH=. .venv/bin/python -m pytest model/tests -q

# regenerate the dashboard data
PYTHONPATH=. .venv/bin/python -m model.export_json
```

## The math

- **Kelly (binary contract):** `f* = (p - c) / (1 - c)`, half-Kelly `= f*/2`,
  fee-adjusted for Robinhood's ~1c/contract each side, capped per bet. The tests
  pin it to Suyesh's worked examples (Switzerland +155 -> 1.47% half; Morocco 35c
  -> 7.31% half).
- **Poisson core:** team attack/defense ratings -> expected goals -> a full
  scoreline matrix (Dixon-Coles low-score correction) from which every market
  is derived: result, double chance, BTTS, totals, handicap, correct score,
  first half. One coherent distribution, so the numbers can be audited.

## Going live (Phase 1.1+)

This v1 ships with **sample data**: team ratings are prior-seeded (not yet fit on
2026 results) and market prices are placeholders. To go live:

1. **Ingest 2026 results** (friendlies + WC matches) and fit ratings — replace
   the `att`/`def` priors in `data/fixtures.json`.
2. **Kalshi live odds.** Create an API key at <https://kalshi.com/account/profile>
   (the regulated exchange Robinhood routes to). Copy `.env.example` to `.env`,
   set `KALSHI_KEY_ID` + `KALSHI_PRIVATE_KEY_PATH`. Never commit the key.
3. **Alerts.** Schedule `export_json` + a Kalshi poll; email when a +EV bet
   crosses the threshold.

Execution stays manual — the tool recommends and sizes; you place the bets.
Robinhood's agentic trading (MCP) is equities-only in beta as of June 2026;
when event contracts ship, the execution layer is built to plug into it.

## Not betting advice

Model estimates carry variance; a positive edge only plays out over many bets.
Half-Kelly is still volatile. Size responsibly.
