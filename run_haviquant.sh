#!/bin/zsh
set -e

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating HaViQuant virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "Python: $(python --version)"
echo "Installing/updating HaViQuant dependencies..."
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt

echo "Checking critical dependencies..."
python - <<'PY'
import scipy, streamlit, pandas, numpy, plotly, yfinance
print("Dependencies: OK")
print("SciPy:", scipy.__version__)
print("Streamlit:", streamlit.__version__)
PY

echo "Checking Python files..."
python -m py_compile app/ui/dashboard.py
python -m py_compile app/main.py

echo "Starting HaViQuant UI..."
echo "Open http://localhost:8501"
echo "Keep this Terminal window open."
exec python -m streamlit run app/ui/dashboard.py
