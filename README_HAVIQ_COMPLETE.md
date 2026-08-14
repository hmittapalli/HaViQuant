# HaViQuant — Complete Fixed Package

This package contains the complete HaViQuant source/data project from the supplied ZIP, excluding the local `.venv`, macOS metadata, Python caches and `.pyc` files.

## Fixes included

### UI startup
The UI is launched from:

```bash
python -m streamlit run app/ui/dashboard.py
```

not `app/main.py`. `app/main.py` remains the full CLI/research pipeline and is intentionally not executed during UI startup.

### Streamlit refresh state
Fixed the `refresh_seconds` widget conflict caused by setting a widget's `value=` from `st.session_state` while also using the same widget key.

### Company Intelligence
The Company Intelligence governance/status renderer now safely handles dictionary/string/scalar items instead of assuming every item supports `item["status"]`.

### SciPy
Added SciPy to `requirements.txt` because Phase 3.9.1 uses Pandas Spearman correlation, which requires SciPy.

### Charts
The supplied dashboard already uses Plotly and `width="stretch"` for the main chart. The 1M/3M/6M/1Y/5Y controls are preserved.

### Live quote
The dashboard's canonical live quote service is preserved. It uses a short cache and the manual Refresh Market Data button clears the relevant cached functions before rerunning.

## Architecture preserved

- Existing TechnicalAnalysisEngine
- Existing DecisionEngine
- Existing BUY/SELL production logic
- Portfolio intelligence
- Opportunity Radar
- Backtesting
- Evidence Research
- Phase 3.7
- Phase 3.8
- Phase 3.9
- Phase 3.9.1
- Company Intelligence

The Evidence/validation layer remains separate from the production BUY/SELL decision engine.

## Run on Mac

```bash
cd ~/Downloads/"HaViQuant_all_phases_portfolio_complete_v7_360_intelligence 2_New"
chmod +x run_haviquant.sh
./run_haviquant.sh
```

The launcher creates `.venv` if necessary, installs `requirements.txt`, verifies SciPy/Streamlit/Plotly/yfinance, compiles the main UI and then starts the UI.

Open:

```text
http://localhost:8501
```

Keep the Terminal window running.

## Diagnostic

If the UI does not start:

```bash
source .venv/bin/activate
python diagnose_haviquant.py
```

Then:

```bash
python -m streamlit run app/ui/dashboard.py
```

Do not paste the shell prompt itself into Terminal; only enter the command after `%`.
