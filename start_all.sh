#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"

if [ ! -d ".venv" ]; then
  echo "Creating Python environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "Installing backend dependencies..."
python -m pip install -q -r backend/requirements.txt

echo "Validating Python..."
python -m py_compile backend/main.py app/company/intelligence_engine.py

if [ ! -d "frontend/web/node_modules" ]; then
  echo "Installing web dependencies..."
  (cd frontend/web && npm install)
fi

echo "Validating React source syntax..."
if command -v node >/dev/null 2>&1; then
  node - <<'NODE'
const fs=require("fs");
const ts=require("typescript");
const file="frontend/web/src/main.tsx";
const source=fs.readFileSync(file,"utf8");
const result=ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext},reportDiagnostics:true,fileName:file});
if ((result.diagnostics||[]).length) {
  for (const d of result.diagnostics) console.error(ts.flattenDiagnosticMessageText(d.messageText,"\\n"));
  process.exit(1);
}
console.log("React source syntax: PASS");
NODE
fi

echo "Starting FastAPI on http://127.0.0.1:8000 ..."
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload > "$ROOT/.haviquant_backend.log" 2>&1 &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null || true' EXIT INT TERM

sleep 2
echo "Starting React/Vite on http://localhost:5173 ..."
(cd frontend/web && npm run dev -- --host 127.0.0.1) &
WEB_PID=$!
trap 'kill $BACKEND_PID $WEB_PID 2>/dev/null || true' EXIT INT TERM

sleep 3
open "http://localhost:5173/" 2>/dev/null || true

echo ""
echo "HaViQuant 360 is running."
echo "Web:     http://localhost:5173/"
echo "API:     http://127.0.0.1:8000/docs"
echo "Logs:    $ROOT/.haviquant_backend.log"
echo "Press Ctrl+C to stop both servers."
wait $WEB_PID
