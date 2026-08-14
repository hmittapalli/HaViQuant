from __future__ import annotations
import json, subprocess, sys, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
print(f"HaViQuant root: {ROOT}")
print("Python:",sys.version.split()[0])
required=[ROOT/"backend/main.py",ROOT/"frontend/web/package.json",ROOT/"mobile/app/package.json",ROOT/"app/company/intelligence_engine.py",ROOT/"app/portfolio/portfolio_intelligence.py"]
for p in required: print(("OK   " if p.exists() else "MISS ")+str(p.relative_to(ROOT)))
try:
    import fastapi, pandas, numpy, yfinance, scipy
    print("Dependencies: OK")
except Exception as e:
    print("Dependencies: INCOMPLETE -",e)
print("\nExpected API routes are generated dynamically by FastAPI. Start the app with ./start_all.sh and inspect http://127.0.0.1:8000/docs")
