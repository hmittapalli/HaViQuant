# HaViQuant V26.2 — Validation Report

## Source baseline
The uploaded `HaViQuant_V26_360_TRADING_INTELLIGENCE_FIXED_TESTED(1).zip` was used as the master source. The existing UI was preserved and changes were incremental.

## Static/source validation
- Backend Python syntax: PASS
- Frontend JavaScript syntax: PASS when Node.js is available
- All 15 navigation labels present: PASS
- 1m / 5m / 15m / 1h / 4h controls: PASS
- Capital / Risk Budget / Stop Distance controls: PASS
- Target 3 / R:R / suggested daily stop: PASS
- News/calendar sentiment UI: PASS
- Required frontend/backend assets: PASS

## Functional scenarios to execute on the Mac
1. Start only with `./start_all.sh`.
2. Verify port 5175 and 8000 are owned by this build.
3. Search AAPL, NVDA, TSLA and SPCX.
4. Test 1m, 5m, 15m, 1h and 4h.
5. Test chart hover, wheel zoom, drag/pan and double-click reset.
6. Enter multiple capital/risk/stop combinations, including zero/very small capital.
7. Verify Target 1/2/3, maximum loss, R:R and ETA change with the selected ticker.
8. Open every left-navigation item and confirm it renders.
9. Verify news sentiment dots: green positive, yellow neutral, red negative.
10. Verify Calendar displays publication dates honestly and sentiment/impact context.
11. Stop with Ctrl+C and restart. Do not start `start_web.sh` in parallel with `start_all.sh`.

## Live-data limitation
Live Yahoo Finance/network behavior cannot be certified inside this packaging environment. The Mac-side smoke test is required for live data.
