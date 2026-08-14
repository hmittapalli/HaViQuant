# HaViQuant COMPLETE 360 — V19 FIXED

This package is a corrected rebuild of V18.

## Critical fix
Fixed the React/Vite compilation error in `frontend/web/src/main.tsx` inside `PortfolioContext`.
The malformed `Cards items` JSX array was missing its closing `]`.

## Verified in build environment
- Python backend source compiles with `python3 -m compileall`.
- `main.tsx` passes TypeScript/JSX syntax transpilation.
- Existing FastAPI routes and existing Python intelligence engine are preserved.
- No sample/demo intelligence was substituted for the Python engine.

## Run

```bash
cd ~/Downloads/HaViQuant_COMPLETE_360_WEB_IOS_ANDROID_V19_FIXED
chmod +x start_all.sh
./start_all.sh
```

Web:
http://localhost:5173

API:
http://127.0.0.1:8000/docs

If dependencies are already installed, startup is immediate. Otherwise `start_all.sh` installs them.
