#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "HaViQuant COMPLETE END-TO-END"
echo "Terminal 1:"
echo "  cd "$ROOT" && source .venv/bin/activate && python -m uvicorn backend.main:app --reload --port 8000"
echo "Terminal 2:"
echo "  cd "$ROOT/frontend/web" && npm install && npm run dev"
echo "Web: http://localhost:5173"
echo "API docs: http://localhost:8000/docs"
