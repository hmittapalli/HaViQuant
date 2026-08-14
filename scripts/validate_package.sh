#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 -m compileall -q backend app
echo "Python compile checks: PASS"
if command -v node >/dev/null 2>&1; then
  node - <<'NODE'
const fs=require("fs");
const ts=require("typescript");
const file="frontend/web/src/main.tsx";
const source=fs.readFileSync(file,"utf8");
const result=ts.transpileModule(source,{compilerOptions:{jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext},reportDiagnostics:true,fileName:file});
if ((result.diagnostics||[]).length) {
  for (const d of result.diagnostics) console.error(ts.flattenDiagnosticMessageText(d.messageText,"\n"));
  process.exit(1);
}
console.log("React TSX syntax: PASS");
NODE
else
  echo "Node not installed; skipped React syntax check."
fi
echo "Package validation: PASS"
