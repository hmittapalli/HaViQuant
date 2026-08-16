#!/bin/bash
set -e
cd "$(dirname "$0")"
OLD_PIDS=$(lsof -tiTCP:5175 -sTCP:LISTEN 2>/dev/null || true)
if [ -n "$OLD_PIDS" ]; then
  echo "Stopping old HaViQuant frontend on port 5175..."
  kill $OLD_PIDS 2>/dev/null || true
  sleep 1
fi
echo "HaViQuant V26 UI: http://127.0.0.1:5175"
"$PWD/.venv/bin/python3" serve_web.py
