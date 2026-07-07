"""World Cup 2026 value-betting model (sush_model).

A transparent, interpretable engine for finding positive-EV bets on the
2026 World Cup and sizing them with fee-aware half-Kelly:

  kelly.py    fee-aware Kelly / EV sizing for binary event contracts
  poisson.py  bivariate-Poisson / Dixon-Coles match model -> every market

The pipeline (Phase 1.1+) ingests 2026-only match data, fits team ratings,
pulls live odds from Kalshi, and exports predictions to JSON that the
Next.js dashboard reads. The math here is deliberately legible: every
market falls out of one coherent goal distribution, so the numbers can be
audited rather than trusted blindly.
"""

__version__ = "0.1.0"
