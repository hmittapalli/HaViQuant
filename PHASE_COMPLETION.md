# HaViQuant Phase Completion

## Preserved foundation
- Phase 3.5 / 3.6 feature engineering and live-feature validation.
- Phase 3.7 / 3.7A evidence diagnostics and stability filtering.
- Phase 3.8 walk-forward robustness and robust-feature handoff.
- Phase 3.9 statistical validation.
- Phase 3.9.1 evidence diagnostic.
- Phase 3.9.3 training-only provisional weighting inside Evidence Engine.
- Production Decision Engine isolated from Evidence/Research.
- Existing chart/UI and the fixed `KeyError: 's'` chart-axis issue.

## Added in this complete package
- Robust live quote service with explicit LIVE/LAST_AVAILABLE/UNAVAILABLE status.
- Portfolio Doctor and sector exposure diagnostics.
- Live scrolling portfolio tape.
- Correct portfolio valuation/P&L behavior when quotes are unavailable.
- Macro/cross-asset regime layer.
- Cross-sector impact and potential-beneficiary scenario layer.
- Market-wide Opportunity Radar.
- Historical analog probability statistics.
- Entry/invalidation/target/risk-reward trade plans.
- Portfolio-aware monitoring and mobile alert integration.

## Production boundary
Opportunity Radar and macro/sector intelligence are research/decision-support layers. They do not rewrite the existing production BUY/SELL Decision Engine. A signal is not a guarantee of profit.

## Validation
All Python source files compile with `py_compile`. The package includes static tests for phase modules and the missing-price safety rule.
