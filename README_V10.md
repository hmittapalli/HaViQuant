# HaViQuant V10 — Product Foundation

V10 moves the customer-facing product toward:
- React + TypeScript + HTML5 for Web
- React Native for iOS / Android
- FastAPI for the Python API
- Existing Python intelligence/research engines preserved under `app/`

## Run backend
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

## Run web
```bash
cd frontend/web
npm install
npm run dev
```

Open http://localhost:5173.

## Architecture rule

Evidence Research (Phases 3.8, 3.9 and 3.9.1) is explicitly research-only and
must not silently alter the production BUY/SELL decision.

The existing Streamlit application is preserved as a legacy/internal interface
while APIs are migrated incrementally. No production decision engine is deleted
by this foundation package.
