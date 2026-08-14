# HaViQuant COMPLETE 360 WEB + iOS + Android — V17

This package is a **complete migration/fix of the V16 package you supplied**, preserving the existing Python intelligence engines and wiring the React/mobile clients to their real API response shapes.

## What was fixed

1. **React object/array crash**
   - Collection rendering now normalizes API envelopes safely.
   - A UI Error Boundary prevents one bad section from blanking the whole application.

2. **Fundamental score missing**
   - The existing engine publishes `overall_company_score`; the API now exposes stable aliases (`fundamental_score`, `fundamental`, `overall`) without inventing values.

3. **Fundamental fields missing**
   - Existing provider fields for profit margin, ROE, revenue growth, earnings growth, P/E and forward P/E are exposed through the company profile/fundamental adapter.
   - Company description is mapped from the engine's existing `summary`.

4. **Company Intelligence**
   - Products/Demand, quarterly data, backlog, competition, risks, governance/ethics, sources and scores remain connected to the existing engine.

5. **Evidence Research**
   - Phase 3.8 → 3.9 → 3.9.1 continues to call the existing Python validation pipeline.
   - Research remains isolated from the production BUY/SELL decision.

6. **Reactive chart**
   - History is loaded from `/api/v1/history`.
   - Quote is polled every second.
   - The current plotted point is refreshed from the live quote.
   - Historical data is refreshed periodically.

7. **Navigation**
   - Dashboard, Stock Analysis, Company Intelligence, Fundamentals, Technical, Decision, Evidence Research, Portfolio, Risk, Backtesting and News are all wired to real API endpoints.

## Start everything on Mac

```bash
cd ~/Downloads/HaViQuant_COMPLETE_360_WEB_IOS_ANDROID_V17_FIXED
chmod +x start_all.sh
./start_all.sh
```

The script opens:

`http://localhost:5173/`

API documentation:

`http://127.0.0.1:8000/docs`

## Manual startup

Terminal 1:

```bash
cd ~/Downloads/HaViQuant_COMPLETE_360_WEB_IOS_ANDROID_V17_FIXED
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2:

```bash
cd ~/Downloads/HaViQuant_COMPLETE_360_WEB_IOS_ANDROID_V17_FIXED/frontend/web
npm install
npm run dev
```

Open `http://localhost:5173/`.

## iOS Simulator

Run the API on the Mac first. Then:

```bash
cd ~/Downloads/HaViQuant_COMPLETE_360_WEB_IOS_ANDROID_V17_FIXED/mobile/app
npm install
npx expo start --ios
```

The iOS Simulator can normally reach the Mac API through localhost.

For a physical iPhone/iPad, set:

```text
EXPO_PUBLIC_API_URL=http://YOUR_MAC_LAN_IP:8000/api/v1
```

## Android Emulator

Use the host alias:

```text
EXPO_PUBLIC_API_URL=http://10.0.2.2:8000/api/v1
```

For a physical Android device, use the Mac LAN IP and allow port 8000 through the local firewall if necessary.

## Important

Do not run the old Streamlit launcher when testing the new React application. The authoritative new UI is:

`frontend/web`

and its API is:

`backend/main.py`.
