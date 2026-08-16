# HaViQuant V26.1 — 360° Trading Intelligence

## Recommended one-command startup

```bash
cd ~/Downloads/HaViQuant_V26_360_TRADING_INTELLIGENCE_FIXED_TESTED
chmod +x start_all.sh start_web.sh start_backend.sh
./start_all.sh
```

Open: `http://127.0.0.1:5175`

`start_all.sh` safely clears only listeners on ports **5175** and **8000**, creates `.venv` when needed, installs dependencies when missing, verifies the backend health endpoint, then starts the frontend.

**Do not start another frontend or backend while `start_all.sh` is running.**

## Separate startup

Backend:
```bash
./start_backend.sh
```

Frontend:
```bash
./start_web.sh
```

Both scripts clean only their own port first, so repeated starts do not intentionally create duplicate HaViQuant servers.

## V26.1 fixes included

### Stock Analysis
- Live daily chart plus **1m, 5m, 15m and 1h intraday chart modes**.
- 4H/1H/15m/5m/1m multi-timeframe confluence uses real timeframe data where the provider supports it.
- 4H is built by resampling 1H candles because Yahoo Finance does not provide a native 4H interval.
- Intraday chart hover shows timestamp, OHLC, volume, RSI and volume ratio.
- Chart zoom, pan and reset remain available.

### 360° Trade Plan Calculator
- Capital, risk budget %, and stop distance % inputs.
- Tooltips explain each input.
- Position sizing is constrained by both available capital and risk budget.
- Displays risk/share, maximum loss, target profits, R/R and daily stop.
- Explicit explanation when the result is zero shares.

### News / Calendar
- Every article gets **green Positive**, **yellow Neutral**, or **red Negative** sentiment.
- Impact is labeled Low / Medium / High.
- News is sorted by publication time when available.
- Calendar clearly states that displayed dates are publication dates and does not invent future economic events.
- Macro/political/geopolitical feeds use the same sentiment presentation.
- RSS context is limited to recent results when dates are available, with a safe fallback.

### Company / Fundamentals
- Company profile now attempts to populate name, sector, industry, market cap, exchange and country.
- Fundamentals endpoint now returns actual Yahoo Finance fundamentals instead of technical-analysis data.

### Reliability
- Single V26.1 version across frontend/backend.
- Duplicate trade-plan route removed.
- Health endpoint returns V26.1.
- Startup scripts clean stale listeners on the correct port.
- Backend startup is health-checked before frontend starts.

## API endpoints

- `/api/v1/health`
- `/api/v1/market/quote?ticker=AAPL`
- `/api/v1/market/analysis?ticker=AAPL&period=60d&interval=5m`
- `/api/v1/market/news?ticker=AAPL`
- `/api/v1/market/macro?ticker=AAPL`
- `/api/v1/market/360?ticker=AAPL`
- `/api/v1/trade-plan?ticker=AAPL&capital=10000&risk_pct=1&stop_pct=3`
- `/api/v1/company/AAPL`
- `/api/v1/fundamental/AAPL`
- `/api/v1/portfolio`

## Testing

`tests/smoke_test.py` validates the backend with deterministic synthetic market data, including:
- daily analysis
- 1m / 5m / 15m / 1h / 4h analysis
- 4H / 1H / 15m / 5m / 1m MTF output
- positive / negative / neutral sentiment
- company and fundamental fields
- trade-plan boundary scenarios
- duplicate FastAPI method/path detection

The final package also contains `TEST_REPORT.md` with the validation performed in this build environment.

## Port checks

```bash
lsof -nP -iTCP:5175 -sTCP:LISTEN
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

Manual cleanup if ever required:

```bash
lsof -tiTCP:5175 -sTCP:LISTEN | xargs kill -9 2>/dev/null
lsof -tiTCP:8000 -sTCP:LISTEN | xargs kill -9 2>/dev/null
```


## V26.2 validation notes

This build preserves the uploaded V26 UI as the master and applies incremental fixes only:
- 1m / 5m / 15m / 1h / 4h chart controls
- more robust chart zoom, pan, hover and resize behavior
- explicit Capital / Risk Budget / Stop Distance explanations
- Target 3 and R/R calculations remain visible
- green/yellow/red sentiment indicators remain available for news and calendar context
- bundled-venv startup commands avoid accidentally using a different Python installation
- API metadata endpoint exposes supported timeframes/navigation for smoke validation

Live market-data verification must be performed on the user's Mac with internet access because this build environment cannot reliably reach Yahoo Finance.
