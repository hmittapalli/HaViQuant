# HaViQuant — Complete Web + Mobile Migration

This package is the complete migration base for HaViQuant's existing Python intelligence engine.
The React web client is a presentation layer; production decisions remain in the Python engine.
Research phases 3.8, 3.9 and 3.9.1 remain isolated from production BUY/SELL decisions.

## 1. One-command local startup

```bash
cd ~/Downloads/HaViQuant_COMPLETE_MIGRATED_WEB_IOS_ANDROID
chmod +x start_all.sh
./start_all.sh
```

Open:

- Web: http://127.0.0.1:5173
- API docs: http://127.0.0.1:8000/docs

The startup script kills stale listeners on ports 8000/5173 before starting, preventing the common problem where the browser talks to an older HaViQuant backend.

## 2. Manual startup

Terminal 1:

```bash
cd ~/Downloads/HaViQuant_COMPLETE_MIGRATED_WEB_IOS_ANDROID
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2:

```bash
cd ~/Downloads/HaViQuant_COMPLETE_MIGRATED_WEB_IOS_ANDROID/frontend/web
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

## 3. Core API

The migrated API exposes:

- `/api/v1/health`
- `/api/v1/quote/{ticker}`
- `/api/v1/history/{ticker}`
- `/api/v1/dashboard/{ticker}`
- `/api/v1/technical/{ticker}`
- `/api/v1/decision/{ticker}`
- `/api/v1/fundamental/{ticker}`
- `/api/v1/fundamentals/{ticker}`
- `/api/v1/company/{ticker}`
- `/api/v1/news/{ticker}`
- `/api/v1/evidence/{ticker}`
- `/api/v1/research/{ticker}`
- `/api/v1/portfolio`
- `/api/v1/portfolio/{ticker}`
- `/api/v1/risk`
- `/api/v1/stock/{ticker}`
- `/api/v1/overview/{ticker}`

## 4. Why the UI no longer goes blank

The React client uses independent API requests. If one optional intelligence endpoint fails, the dashboard still renders quote, chart and other available engines and shows a partial-API warning instead of replacing the entire application with a generic data error.

## 5. Research

Click **Evidence Research → Run Full Research**. The web client calls:

```text
GET /api/v1/research/NVDA?run=true
```

The backend invokes the existing Phase 3.8, Phase 3.9 and Phase 3.9.1 Python engines. Results are displayed as research validation only.

## 6. Mobile

The `mobile/app` directory contains the React Native/Expo client. Set:

```bash
EXPO_PUBLIC_API_URL=http://YOUR-MAC-IP:8000/api/v1
```

For a physical phone, do not use `localhost`; use the Mac's LAN IP.

## 7. Existing engine

The package preserves the existing `app/` intelligence modules, including technical analysis, decision engine, company intelligence, portfolio intelligence, backtesting and evidence/research engines. The UI does not replace those engines with sample values.
