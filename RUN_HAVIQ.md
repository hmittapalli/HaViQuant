# HaViQuant — Simple Run Guide

You do not need to manually edit Python files.

## Recommended

Open Terminal and run:

```bash
cd /Users/harimittapalli/Downloads/HaViQuant_all_phases_portfolio_complete_v4_premium
./run_haviquant.sh
```

The script creates `.venv` if needed, installs dependencies, compiles the dashboard, and starts Streamlit.

Open `http://localhost:8501` if the browser does not open automatically.

## Manual

```bash
cd /Users/harimittapalli/Downloads/HaViQuant_all_phases_portfolio_complete_v4_premium
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m py_compile app/ui/dashboard.py
python -m streamlit run app/ui/dashboard.py
```

## Navigation

- 📊 Dashboard — fast command center
- 📈 Stock Analysis — full ticker workspace
- 💼 Portfolio — live valuation, portfolio doctor, alerts
- 🔥 Opportunity Radar — macro, sector and opportunity discovery
- 🧪 Backtesting — historical validation
- 🔬 Evidence Research — Phase 3.8/3.9 research
