#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "=============================================="
echo " HaViQuant V10"
echo "=============================================="
echo "Backend:  http://localhost:8000"
echo "Web:      http://localhost:5173"
echo
echo "Start backend:"
echo "  cd "$ROOT" && python -m uvicorn backend.main:app --reload --port 8000"
echo
echo "Start web:"
echo "  cd "$ROOT/frontend/web" && npm install && npm run dev"
echo "=============================================="
