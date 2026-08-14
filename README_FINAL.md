# HaViQuant 360° Complete Final — Web + iOS + Android

This package is a complete migration built from the V14 source package. The existing Python intelligence engine is preserved under `app/` and exposed through the FastAPI adapter under `backend/`. The React web client consumes the real API instead of sample data.

## Included

- Existing Python market-data, technical, decision, company, portfolio, risk and research engines
- Phase 3.8 / 3.9 / 3.9.1 research pipeline
- Research isolation from production BUY/SELL decision
- FastAPI API layer
- React + TypeScript premium web UI
- Navigation for Dashboard, Stock Analysis, Company Intelligence, Fundamentals, Technical, Decision, Evidence Research, Portfolio, Risk, Backtesting and News
- Reactive market chart
- 1-second live quote polling with periodic history refresh
- Robust response normalization (prevents `items.slice is not a function`)
- Expo React Native mobile application for iOS and Android
- One-command local web/backend startup

## Web

Open Terminal 1:

```bash
cd ~/Downloads/HaViQuant_COMPLETE_360_WEB_IOS_ANDROID_FINAL
chmod +x start_all.sh
./start_all.sh
```

Then open:

- Web: http://127.0.0.1:5173
- API: http://127.0.0.1:8000
- API docs: http://127.0.0.1:8000/docs

If you start the servers manually:

```bash
cd ~/Downloads/HaViQuant_COMPLETE_360_WEB_IOS_ANDROID_FINAL

python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In another Terminal:

```bash
cd ~/Downloads/HaViQuant_COMPLETE_360_WEB_IOS_ANDROID_FINAL/frontend/web
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

## iOS / Android

Install Expo dependencies:

```bash
cd ~/Downloads/HaViQuant_COMPLETE_360_WEB_IOS_ANDROID_FINAL/mobile/app
npm install
npx expo start
```

For iOS Simulator:

```bash
npx expo start --ios
```

For Android Emulator:

```bash
EXPO_PUBLIC_API_URL=http://10.0.2.2:8000/api/v1 npx expo start --android
```

For a physical phone/tablet on the same Wi-Fi, use the Mac's LAN IP:

```bash
EXPO_PUBLIC_API_URL=http://YOUR_MAC_IP:8000/api/v1 npx expo start
```

## Important

The web chart polls the quote endpoint every second. The market-data provider may return the same quote for multiple seconds; the UI cannot manufacture a real market tick that the provider does not supply.

Research is intentionally separate:

`Production Decision` -> BUY / SELL / WATCH

`Research` -> Phase 3.8 -> Phase 3.9 -> Phase 3.9.1

Research results do not silently modify the production signal.

## Data

The portfolio is read from:

`data/portfolio.json`

The application uses the existing V14 engine implementations rather than replacing them with sample calculations.
