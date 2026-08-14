# HaViQuant Phase 4 — Market Opportunity & Portfolio Intelligence

## Added
- Robust live quote fallback with explicit LIVE/LAST_AVAILABLE/UNAVAILABLE status.
- Portfolio valuation that never converts a missing quote into a zero value or fake -100% loss.
- Portfolio Doctor: health, concentration, sector exposure, underrepresented sectors and structural issues.
- Scrolling live portfolio tape.
- Cross-sector impact scenarios driven by rates, oil, dollar, volatility and current sector rotation.
- Opportunity Radar: technical Decision Engine score + historical analog statistics + risk/reward trade plan.
- Empirical probability fields: sample count, historical positive rate, P(+3%) and P(-3%) over a 5-day horizon.
- Entry zone, stop/invalidation, targets, support, resistance and risk/reward.
- Macro regime context using Treasury yield, VIX, Nasdaq, dollar, gold and oil proxies.
- Existing Phase 3.8/3.9 evidence infrastructure remains separate from production BUY/SELL logic.
- Existing mobile alert service remains available through Telegram/Pushover.

## Safety / interpretation
The Opportunity Radar is a research and risk-management layer. It does not guarantee profit and does not rewrite the production Decision Engine. Historical probabilities are descriptive empirical analogs and must be validated out-of-sample before being treated as production forecasts.
