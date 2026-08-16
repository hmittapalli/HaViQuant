#!/bin/bash
set -e
cd "$(dirname "$0")"
# Stop only an existing listener on our backend port; never kill unrelated Python processes.
OLD_PIDS=$(lsof -tiTCP:8000 -sTCP:LISTEN 2>/dev/null || true)
if [ -n "$OLD_PIDS" ]; then
  echo "Stopping old HaViQuant backend on port 8000..."
  kill $OLD_PIDS 2>/dev/null || true
  sleep 1
fi
if [ ! -x ".venv/bin/python3" ]; then python3 -m venv .venv; fi
source .venv/bin/activate
if ! python3 -c "import fastapi, uvicorn, yfinance, pandas, numpy" >/dev/null 2>&1; then
  echo "Installing backend dependencies..."
  python3 -m pip install -q -r backend/requirements.txt
fi
echo "HaViQuant V26 backend: http://127.0.0.1:8000"
"$PWD/.venv/bin/python3" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
