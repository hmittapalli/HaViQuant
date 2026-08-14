# HaViQuant COMPLETE END-TO-END

This package is based on the uploaded HaViQuant V10 all-phases source and preserves the existing Python engines. The API is now an adapter over those engines rather than a placeholder/mock API.

## Included
- Existing Python market-data, technical, decision, company intelligence, portfolio and research engines.
- FastAPI endpoints over those engines.
- React web UI with navigation, dynamic ticker, live quote, real historical candlestick chart, technical decision, company intelligence, evidence research status, news and portfolio.
- React Native/Expo starter consuming the same API.
- SciPy included for Phase 3.9.1 statistical diagnostics.

## Web startup

Terminal 1:
```bash
cd ~/Downloads/HaViQuant_COMPLETE_END_TO_END
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

Terminal 2:
```bash
cd ~/Downloads/HaViQuant_COMPLETE_END_TO_END/frontend/web
npm install
npm run dev
```

Open:
- http://localhost:5173
- http://localhost:8000/docs

## Research
Research is deliberately not executed on every dashboard refresh. Open Evidence Research and call:
`GET /api/v1/research/{ticker}?run=true`
to execute the existing Phase 3.8 → 3.9 → 3.9.1 engines. Results are marked research-only and are not used to alter the production DecisionEngine.

## Mobile
```bash
cd mobile/app
npm install
npx expo start
```
Set the API URL for a physical device to the Mac's LAN address rather than localhost.
