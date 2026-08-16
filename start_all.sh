#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "=============================================="
echo " HaViQuant V26 — 360° Trading Intelligence"
echo "=============================================="
# Clean only processes listening on our two app ports.
for PORT in 5175 8000; do
  PIDS=$(lsof -tiTCP:$PORT -sTCP:LISTEN 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    echo "Stopping old process on port $PORT..."
    kill $PIDS 2>/dev/null || true
    sleep 1
  fi
done
if [ ! -x ".venv/bin/python3" ]; then
  echo "Creating Python environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate
if ! python3 -c "import fastapi, uvicorn, yfinance, pandas, numpy" >/dev/null 2>&1; then
  echo "Installing backend dependencies..."
  python3 -m pip install -q -r backend/requirements.txt
fi
echo "Starting backend on 8000..."
"$PWD/.venv/bin/python3" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 > .backend.log 2>&1 &
BACK_PID=$!
cleanup(){ kill "$BACK_PID" 2>/dev/null || true; echo; echo "HaViQuant stopped."; }
trap cleanup INT TERM EXIT
for i in {1..20}; do
  if curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then break; fi
  sleep 0.5
done
if ! curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then
  echo "Backend failed to start. See .backend.log"
  cat .backend.log
  exit 1
fi
echo "Starting frontend on 5175..."
echo "Frontend: http://127.0.0.1:5175"
"$PWD/.venv/bin/python3" serve_web.py
