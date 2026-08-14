# HaViQuant v6 Premium UI

## Design goals
- Dashboard owns the large chart.
- Stock Analysis is a no-duplicate-chart decision terminal.
- Premium dark terminal UI with glass panels, active navigation and command header.
- Performance-first: cached data remains cached and the app no longer blocks the whole Streamlit process with `sleep()` on every rerun.
- Live refresh is user-controlled from the sidebar.
- Existing production Decision Engine and Phase 3 research/validation remain separate.

## Run
```bash
cd /Users/harimittapalli/Downloads/HaViQuant_all_phases_portfolio_complete_v6_premium
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m py_compile app/ui/dashboard.py
python -m streamlit run app/ui/dashboard.py
```
