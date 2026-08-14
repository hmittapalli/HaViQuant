
"""
HaViQuant v3 - Premium Market Intelligence Terminal

COMPLETE REPLACEMENT:
    app/ui/dashboard.py

Design:
1. Large chart at the top.
2. Live quote refresh.
3. Technical signal map.
4. Buy/Sell setup, entry zone, targets and invalidation.
5. Pattern detection.
6. Support/resistance.
7. Live news in a compact scroll panel.
8. Insider intelligence.
9. Fair-value engine with transparent inputs.
10. Existing TechnicalAnalysisEngine and DecisionEngine remain authoritative.
11. News/insiders/fair-value never modify the production DecisionEngine.
"""

from __future__ import annotations

import json
import math
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ------------------------------------------------------------------
# Project imports
# ------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT / "app"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

try:
    from app.data.market_data import MarketDataService
    from app.analysis.technical_analysis import TechnicalAnalysisEngine
    from app.analysis.decision_engine import DecisionEngine
except Exception:
    from data.market_data import MarketDataService
    from analysis.technical_analysis import TechnicalAnalysisEngine
    from analysis.decision_engine import DecisionEngine

try:
    from app.backtesting.backtest_engine import BacktestEngine
except Exception:
    try:
        from backtesting.backtest_engine import BacktestEngine
    except Exception:
        BacktestEngine = None

try:
    import yfinance as yf
except Exception:
    yf = None

try:
    from app.portfolio.portfolio_manager import load_portfolio, save_portfolio, normalize_positions
    from app.portfolio.alert_service import send_telegram, send_pushover
except Exception:
    from portfolio.portfolio_manager import load_portfolio, save_portfolio, normalize_positions
    from portfolio.alert_service import send_telegram, send_pushover

try:
    from app.portfolio.portfolio_intelligence import portfolio_rows, portfolio_doctor, analyze_ticker
    from app.market_intelligence import macro_snapshot, sector_rotation, scan_opportunities, sector_impact_map
    from app.market_move_intelligence import explain_move
    from app.company.intelligence_engine import build_company_intelligence
except Exception:
    from portfolio.portfolio_intelligence import portfolio_rows, portfolio_doctor, analyze_ticker
    from market_intelligence import macro_snapshot, sector_rotation, scan_opportunities, sector_impact_map
    from market_move_intelligence import explain_move
    from company.intelligence_engine import build_company_intelligence


# ------------------------------------------------------------------
# Page
# ------------------------------------------------------------------
st.set_page_config(
    page_title="HaViQuant",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULT_TICKER = "NVDA"

if "ticker" not in st.session_state:
    st.session_state.ticker = DEFAULT_TICKER
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True
if "chart_range" not in st.session_state:
    st.session_state.chart_range = "6M"
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

# Performance-first defaults: live refresh is opt-in so navigation remains responsive.
if "last_refresh_label" not in st.session_state:
    st.session_state.last_refresh_label = datetime.now().strftime("%H:%M:%S")


# ==================================================================
# UI THEME
# ==================================================================

def inject_theme():
    st.markdown(
        """
        <style>
        :root { --hq-bg:#050b12; --hq-panel:#0a1520; --hq-panel2:#0d1b29; --hq-line:rgba(255,255,255,.07); --hq-muted:#7f93a7; --hq-text:#eaf3fb; --hq-cyan:#58c7ff; --hq-green:#28e39a; --hq-red:#ff6078; --hq-gold:#f5c95b; }
        .stApp { background:radial-gradient(circle at 12% -8%,rgba(45,221,158,.09),transparent 26%),radial-gradient(circle at 88% -8%,rgba(72,166,255,.11),transparent 30%),linear-gradient(180deg,#050b12 0%,#07111a 100%); color:var(--hq-text); }
        .main .block-container { max-width:1860px; padding:1.05rem 1.35rem 2.2rem; }
        #MainMenu, footer, header { visibility:hidden; }
        section[data-testid="stSidebar"] { background:linear-gradient(180deg,#06101a 0%,#040910 100%); border-right:1px solid rgba(255,255,255,.075); box-shadow:18px 0 50px rgba(0,0,0,.18); }
        section[data-testid="stSidebar"] > div { padding-top:1rem; }
        .hq-brand { display:flex; align-items:center; gap:10px; padding:10px 4px 2px; }
        .hq-brand-mark { width:36px;height:36px;border-radius:11px;display:grid;place-items:center;background:linear-gradient(135deg,#27df9a,#4da9ff);color:#031019;font-weight:1000;box-shadow:0 8px 28px rgba(45,219,158,.18); }
        .hq-brand-name { font-size:21px;font-weight:950;letter-spacing:-.045em;line-height:1; }
        .hq-brand-tag { color:#7890a5;font-size:8px;font-weight:900;letter-spacing:.16em;text-transform:uppercase;margin-top:4px; }
        .hq-command { display:flex;align-items:center;justify-content:space-between;gap:16px;padding:13px 16px;margin-bottom:13px;border:1px solid var(--hq-line);border-radius:16px;background:linear-gradient(135deg,rgba(13,29,43,.92),rgba(7,17,27,.86));box-shadow:0 14px 45px rgba(0,0,0,.16);backdrop-filter:blur(14px); }
        .hq-command-left { display:flex;align-items:center;gap:12px;min-width:0; }
        .hq-command-ticker { font-size:20px;font-weight:950;letter-spacing:-.04em; }
        .hq-command-page { color:#8095aa;font-size:10px;font-weight:850;letter-spacing:.12em;text-transform:uppercase; }
        .hq-status { display:inline-flex;align-items:center;gap:6px;border:1px solid rgba(40,227,154,.2);background:rgba(40,227,154,.06);padding:6px 9px;border-radius:999px;color:#8feec4;font-size:9px;font-weight:900;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap; }
        .hq-dot { width:7px;height:7px;border-radius:50%;background:var(--hq-green);box-shadow:0 0 12px rgba(40,227,154,.8); }
        .hq-card { background:linear-gradient(145deg,rgba(14,29,43,.98),rgba(7,17,26,.98));border:1px solid var(--hq-line);border-radius:16px;padding:16px;box-shadow:0 14px 38px rgba(0,0,0,.16); }
        .hq-card:hover { border-color:rgba(88,199,255,.14); }
        .hq-title { font-size:11px;font-weight:950;letter-spacing:.12em;text-transform:uppercase;color:#a9bfd2;margin-bottom:10px; }
        .hq-sub { font-size:10px;color:var(--hq-muted); }
        .hq-big { font-size:34px;font-weight:950;letter-spacing:-.05em; }
        .hq-positive { color:var(--hq-green)!important; } .hq-negative { color:var(--hq-red)!important; } .hq-neutral { color:var(--hq-gold)!important; }
        .hq-page-kicker { color:#5f7c94;font-size:9px;font-weight:950;letter-spacing:.18em;text-transform:uppercase;margin-bottom:3px; }
        .hq-page-title { font-size:32px;font-weight:950;letter-spacing:-.055em;line-height:1.05;margin:0; }
        .hq-page-subtitle { color:#7f94a8;font-size:11px;margin-top:6px;margin-bottom:14px;max-width:1000px;line-height:1.55; }
        .hq-section { margin:18px 0 9px;font-size:14px;font-weight:950;letter-spacing:-.015em;color:#e7f0f7; }
        .hq-tape { overflow:hidden;white-space:nowrap;border:1px solid var(--hq-line);border-radius:13px;background:rgba(6,17,27,.88);margin:0 0 13px;padding:8px 0;box-shadow:inset 0 1px 0 rgba(255,255,255,.02); }
        .hq-tape-track { display:inline-block;min-width:100%;animation:hqscroll 48s linear infinite; }
        .hq-tape-item { display:inline-block;margin-right:34px;font-size:11px;color:#dce8f2; }
        @keyframes hqscroll { from{transform:translateX(0)} to{transform:translateX(-50%)} }
        .hq-news-scroll { height:310px;overflow-y:auto;padding-right:7px; }
        .hq-news-scroll::-webkit-scrollbar { width:4px; } .hq-news-scroll::-webkit-scrollbar-thumb { background:#29465d;border-radius:8px; }
        .hq-news-item { padding:10px 2px;border-bottom:1px solid rgba(255,255,255,.05); }
        .hq-news-title { color:#edf4fa;font-size:11px;line-height:1.45;font-weight:760; } .hq-news-meta{color:#71869a;font-size:8px;margin-top:4px;}
        .hq-signal { border-radius:14px;padding:13px;background:linear-gradient(145deg,#0a1825,#07131e);border:1px solid var(--hq-line); }
        .hq-mini-grid { display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px; }
        .hq-mini { padding:10px 11px;border:1px solid var(--hq-line);border-radius:12px;background:rgba(255,255,255,.018); }
        .hq-mini-label { color:#70879c;font-size:8px;font-weight:850;letter-spacing:.09em;text-transform:uppercase; }
        .hq-mini-value { margin-top:4px;font-size:15px;font-weight:900;letter-spacing:-.02em; }
        .hq-chip { display:inline-flex;align-items:center;padding:5px 8px;border-radius:999px;background:rgba(255,255,255,.04);border:1px solid var(--hq-line);font-size:9px;font-weight:850;color:#9db2c5;margin-right:5px;margin-bottom:5px; }
        div[data-testid="stMetric"] { background:linear-gradient(145deg,rgba(13,29,43,.95),rgba(8,18,28,.96));border:1px solid rgba(255,255,255,.055);border-radius:13px;padding:.68rem .75rem;box-shadow:0 8px 24px rgba(0,0,0,.12); }
        div[data-testid="stMetricLabel"] { color:#7890a4!important;font-size:9px!important;font-weight:800!important;letter-spacing:.06em;text-transform:uppercase; }
        div[data-testid="stMetricValue"] { font-size:21px!important;font-weight:930!important;letter-spacing:-.04em; }
        div[data-testid="stPlotlyChart"] { background:#07121d;border:1px solid var(--hq-line);border-radius:16px;overflow:hidden;box-shadow:0 16px 45px rgba(0,0,0,.16); }
        section[data-testid="stSidebar"] .stRadio > label { color:#5f7890!important;font-size:8px!important;font-weight:950!important;letter-spacing:.16em!important;text-transform:uppercase!important; }
        section[data-testid="stSidebar"] div[role="radiogroup"] { gap:5px!important; }
        section[data-testid="stSidebar"] div[role="radiogroup"] label { background:rgba(255,255,255,.018);border:1px solid rgba(255,255,255,.045);border-radius:12px;padding:9px 10px!important;transition:all .15s ease; }
        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover { background:rgba(77,169,255,.07);border-color:rgba(77,169,255,.18);transform:translateX(2px); }
        section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] { background:linear-gradient(135deg,rgba(40,227,154,.12),rgba(77,169,255,.09));border-color:rgba(40,227,154,.28);box-shadow:0 8px 22px rgba(0,0,0,.16); }
        section[data-testid="stSidebar"] .stTextInput input { background:#081522;border:1px solid rgba(255,255,255,.08);border-radius:11px;color:#eef7ff;font-weight:850; }
        section[data-testid="stSidebar"] .stButton button { border-radius:10px;border:1px solid rgba(255,255,255,.07);background:linear-gradient(135deg,#0d2130,#091721);font-weight:850; }
        .small-note { color:#71879a;font-size:8px;line-height:1.5; }
        .stTabs [data-baseweb="tab-list"] { gap:5px;background:rgba(5,13,20,.72);padding:5px;border:1px solid var(--hq-line);border-radius:13px; }
        .stTabs [data-baseweb="tab"] { height:34px;border-radius:9px;color:#7890a4;font-size:10px;font-weight:850; }
        .stTabs [aria-selected="true"] { background:linear-gradient(135deg,rgba(40,227,154,.12),rgba(77,169,255,.08));color:#eaf7ff; }
        div[data-testid="stDataFrame"] { border:1px solid var(--hq-line);border-radius:14px;overflow:hidden; }

        /* ============================================================
           HaViQuant V9 — Institutional Dark Glass Theme
           Force dark rendering even when the browser/OS is in light mode.
           ============================================================ */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
            color-scheme: dark !important;
        }
        body, .stApp, [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(900px 500px at 15% -5%, rgba(53, 224, 171, .10), transparent 58%),
                radial-gradient(800px 480px at 92% 0%, rgba(76, 143, 255, .12), transparent 55%),
                linear-gradient(180deg, #03070d 0%, #06101a 45%, #040a11 100%) !important;
        }
        .stApp * { box-sizing: border-box; }
        [data-testid="stHeader"] { background: rgba(3,7,13,.78) !important; }
        [data-testid="stToolbar"] { background: transparent !important; }
        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(8,18,29,.98), rgba(3,8,14,.99)) !important;
            border-right: 1px solid rgba(122,169,205,.12) !important;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stCaption {
            color: #9bb0c3 !important;
        }
        /* Inputs / controls */
        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        div[data-baseweb="textarea"] > div,
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input {
            background: #08131f !important;
            color: #f4f8fc !important;
            border-color: rgba(130,170,204,.18) !important;
        }
        [data-baseweb="popover"],
        [data-baseweb="menu"],
        [role="listbox"] {
            background: #0a1623 !important;
            color: #edf5fb !important;
            border: 1px solid rgba(130,170,204,.16) !important;
        }
        [role="option"] { color: #dce9f3 !important; }
        [role="option"]:hover { background: rgba(76,143,255,.14) !important; }
        /* Buttons */
        .stButton > button,
        button[kind="secondary"],
        button[kind="primary"] {
            color: #edf7ff !important;
            background: linear-gradient(135deg,#0d2030,#091621) !important;
            border: 1px solid rgba(113,160,195,.20) !important;
            border-radius: 11px !important;
            min-height: 38px !important;
            box-shadow: 0 7px 20px rgba(0,0,0,.18) !important;
            transition: .16s ease !important;
        }
        .stButton > button:hover,
        button[kind="secondary"]:hover,
        button[kind="primary"]:hover {
            border-color: rgba(72,213,168,.42) !important;
            transform: translateY(-1px);
            box-shadow: 0 10px 28px rgba(0,0,0,.28) !important;
        }
        button[kind="primary"] {
            background: linear-gradient(135deg,#0c6b57,#0d4560) !important;
            border-color: rgba(58,229,175,.38) !important;
        }
        /* Checkbox / slider */
        [data-testid="stCheckbox"] label,
        [data-testid="stSlider"] label {
            color: #b6c8d7 !important;
        }
        /* Tabs / segmented controls */
        [data-baseweb="segmented-control"] {
            background: #07111c !important;
            border: 1px solid rgba(130,170,204,.14) !important;
            padding: 4px !important;
            border-radius: 12px !important;
        }
        [data-baseweb="segmented-control"] button {
            color: #8fa6b9 !important;
            background: transparent !important;
            border-radius: 8px !important;
        }
        [data-baseweb="segmented-control"] button[aria-checked="true"] {
            color: #ecfbf6 !important;
            background: linear-gradient(135deg,rgba(40,227,154,.22),rgba(77,169,255,.16)) !important;
            box-shadow: inset 0 0 0 1px rgba(65,224,178,.20) !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(4,10,17,.88) !important;
            border: 1px solid rgba(130,170,204,.12) !important;
        }
        /* Tables / alerts */
        [data-testid="stDataFrame"] {
            background: #07111c !important;
            border-color: rgba(130,170,204,.14) !important;
        }
        [data-testid="stAlert"] {
            background: rgba(10,23,35,.94) !important;
            border: 1px solid rgba(130,170,204,.14) !important;
            color: #dbe8f2 !important;
        }
        /* Expander */
        [data-testid="stExpander"] {
            background: rgba(8,18,29,.86) !important;
            border: 1px solid rgba(130,170,204,.12) !important;
            border-radius: 14px !important;
        }
        /* Remove accidental light cards from Streamlit internals */
        [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stPopover"],
        [data-testid="stDialog"] {
            color-scheme: dark !important;
        }
        /* Premium live pulse */
        .hq-status .hq-dot {
            animation: hqPulse 1.8s ease-in-out infinite;
        }
        @keyframes hqPulse {
            0%,100% { opacity: 1; transform: scale(1); }
            50% { opacity: .45; transform: scale(.78); }
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# ==================================================================
# HELPERS
# ==================================================================

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        x = float(value)
        return x if np.isfinite(x) else default
    except Exception:
        return default


def opt_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        x = float(value)
        return x if np.isfinite(x) else None
    except Exception:
        return None


def safe_text(value: Any, default: str = "N/A") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def first_value(source: Any, keys: list[str], default=None):
    if source is None:
        return default
    if isinstance(source, dict):
        for key in keys:
            if key in source and source[key] is not None:
                return source[key]
        return default
    for key in keys:
        value = getattr(source, key, None)
        if value is not None:
            return value
    return default


def money(value: Any) -> str:
    x = opt_float(value)
    if x is None:
        return "N/A"
    if abs(x) >= 1_000_000_000:
        return f"${x/1_000_000_000:.2f}B"
    if abs(x) >= 1_000_000:
        return f"${x/1_000_000:.2f}M"
    if abs(x) >= 1_000:
        return f"${x/1_000:.1f}K"
    return f"${x:,.0f}"


def _fmt_money(value: Any, default: str = "N/A") -> str:
    """UI-safe money formatter used by Company Intelligence and comparison tables."""
    x = opt_float(value)
    if x is None:
        return default
    sign = "-" if x < 0 else ""
    ax = abs(x)
    if ax >= 1_000_000_000_000:
        return f"{sign}${ax/1_000_000_000_000:.2f}T"
    if ax >= 1_000_000_000:
        return f"{sign}${ax/1_000_000_000:.2f}B"
    if ax >= 1_000_000:
        return f"{sign}${ax/1_000_000:.2f}M"
    if ax >= 1_000:
        return f"{sign}${ax/1_000:.1f}K"
    return f"{sign}${ax:,.2f}"


def _fmt_pct(value: Any, default: str = "N/A") -> str:
    x = opt_float(value)
    if x is None:
        return default
    return f"{x:+.2f}%"


def _fmt_number(value: Any, decimals: int = 2, default: str = "N/A") -> str:
    x = opt_float(value)
    if x is None:
        return default
    return f"{x:,.{decimals}f}"


def relative_time(dt: Optional[datetime]) -> str:
    if dt is None:
        return "Recent"
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        seconds = max(
            0,
            int((now - dt.astimezone(timezone.utc)).total_seconds()),
        )
        if seconds < 60:
            return "Just now"
        if seconds < 3600:
            return f"{seconds//60} min ago"
        if seconds < 86400:
            return f"{seconds//3600} hr ago"
        return dt.strftime("%b %d")
    except Exception:
        return "Recent"


def http_json(url: str, timeout: int = 12) -> Optional[dict]:
    request = Request(
        url,
        headers={
            "User-Agent": "HaViQuant research dashboard",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


# ==================================================================
# MARKET DATA / EXISTING ENGINES
# ==================================================================

@st.cache_data(ttl=300, show_spinner=False)
def load_market_data(ticker: str) -> pd.DataFrame:
    service = MarketDataService()
    data = service.get_history(ticker, period="5y")
    if data is None or data.empty:
        raise RuntimeError(f"No market data returned for {ticker}.")
    return data


@st.cache_data(ttl=300, show_spinner=False)
def run_existing_analysis(ticker: str):
    data = load_market_data(ticker)

    technical = TechnicalAnalysisEngine().analyze(data)
    engine = DecisionEngine()

    if hasattr(engine, "evaluate"):
        decision = engine.evaluate(technical)
    elif hasattr(engine, "decide"):
        try:
            decision = engine.decide(technical)
        except TypeError:
            decision = engine.decide(None, technical)
    else:
        raise RuntimeError(
            "DecisionEngine does not expose evaluate() or decide()."
        )

    return {
        "ticker": ticker,
        "data": data,
        "technical": technical,
        "decision": decision,
    }


# ==================================================================
# DATAFRAME + INDICATORS
# ==================================================================

def normalize_market_dataframe(data: Any) -> Optional[pd.DataFrame]:
    if data is None:
        return None

    if not isinstance(data, pd.DataFrame):
        try:
            data = pd.DataFrame(data)
        except Exception:
            return None

    if data.empty:
        return None

    df = data.copy()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [
            col[0] if isinstance(col, tuple) else col
            for col in df.columns
        ]

    mapping = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "adj close": "Adj Close",
        "volume": "Volume",
    }

    rename = {}
    for column in df.columns:
        key = str(column).strip().lower()
        if key in mapping:
            rename[column] = mapping[key]

    df = df.rename(columns=rename)

    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = [x for x in required if x not in df.columns]

    if missing:
        raise RuntimeError(
            "Missing market columns: " + ", ".join(missing)
        )

    try:
        df.index = pd.to_datetime(df.index)
    except Exception:
        pass

    df = df.sort_index()

    for column in required:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = df.dropna(
        subset=["Open", "High", "Low", "Close"]
    )

    if df.empty:
        return None

    # --------------------------------------------------------------
    # Technical display layer.
    # These values are for visualization/signals only.
    # They DO NOT replace the existing Decision Engine.
    # --------------------------------------------------------------

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    for period in [9, 20, 21, 50, 200]:
        df[f"EMA{period}"] = close.ewm(
            span=period,
            adjust=False,
        ).mean()

        df[f"SMA{period}"] = close.rolling(
            period,
            min_periods=period,
        ).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1/14,
        adjust=False,
    ).mean()

    avg_loss = loss.ewm(
        alpha=1/14,
        adjust=False,
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)

    df["RSI14"] = 100 - (100 / (1 + rs))

    ema12 = close.ewm(
        span=12,
        adjust=False,
    ).mean()

    ema26 = close.ewm(
        span=26,
        adjust=False,
    ).mean()

    df["MACD"] = ema12 - ema26
    df["MACDSignal"] = df["MACD"].ewm(
        span=9,
        adjust=False,
    ).mean()
    df["MACDHist"] = (
        df["MACD"] - df["MACDSignal"]
    )

    df["BBMid"] = close.rolling(
        20,
        min_periods=20,
    ).mean()

    bb_std = close.rolling(
        20,
        min_periods=20,
    ).std()

    df["BBUpper"] = (
        df["BBMid"] + 2 * bb_std
    )

    df["BBLower"] = (
        df["BBMid"] - 2 * bb_std
    )

    prev_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    df["ATR14"] = tr.rolling(
        14,
        min_periods=14,
    ).mean()

    df["VolumeAvg20"] = volume.rolling(
        20,
        min_periods=20,
    ).mean()

    df["RelativeVolume"] = (
        volume / df["VolumeAvg20"]
    )

    df["OBV"] = (
        np.sign(close.diff())
        .fillna(0)
        * volume
    ).cumsum()

    return df


# ==================================================================
# PATTERN ENGINE
# ==================================================================

def detect_patterns(df: pd.DataFrame) -> list[dict[str, str]]:
    if len(df) < 5:
        return []

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    patterns = []

    o = safe_float(latest["Open"])
    h = safe_float(latest["High"])
    l = safe_float(latest["Low"])
    c = safe_float(latest["Close"])

    po = safe_float(previous["Open"])
    pc = safe_float(previous["Close"])

    body = abs(c - o)
    candle_range = max(h - l, 1e-9)

    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    if body <= candle_range * 0.10:
        patterns.append(
            {
                "name": "Doji",
                "signal": "NEUTRAL",
                "detail": "Indecision candle",
            }
        )

    if lower_wick >= body * 2 and upper_wick <= body:
        patterns.append(
            {
                "name": "Hammer",
                "signal": "BULLISH",
                "detail": "Long lower rejection",
            }
        )

    if upper_wick >= body * 2 and lower_wick <= body:
        patterns.append(
            {
                "name": "Shooting Star",
                "signal": "BEARISH",
                "detail": "Upper-price rejection",
            }
        )

    if (
        pc < po
        and c > o
        and c >= po
        and o <= pc
    ):
        patterns.append(
            {
                "name": "Bullish Engulfing",
                "signal": "BULLISH",
                "detail": "Current body engulfs prior body",
            }
        )

    if (
        pc > po
        and c < o
        and o >= pc
        and c <= po
    ):
        patterns.append(
            {
                "name": "Bearish Engulfing",
                "signal": "BEARISH",
                "detail": "Current body engulfs prior body",
            }
        )

    if not patterns:
        patterns.append(
            {
                "name": "No major candle pattern",
                "signal": "NEUTRAL",
                "detail": "No high-confidence pattern detected",
            }
        )

    return patterns


# ==================================================================
# SUPPORT / RESISTANCE
# ==================================================================

def support_resistance(
    df: pd.DataFrame,
) -> tuple[Optional[float], Optional[float]]:

    if len(df) < 20:
        return None, None

    recent = df.tail(
        min(60, len(df))
    )

    current = safe_float(
        recent["Close"].iloc[-1]
    )

    lows = recent["Low"].nsmallest(
        min(8, len(recent))
    )

    highs = recent["High"].nlargest(
        min(8, len(recent))
    )

    supports = [
        safe_float(x)
        for x in lows
        if safe_float(x) < current
    ]

    resistances = [
        safe_float(x)
        for x in highs
        if safe_float(x) > current
    ]

    support = (
        max(supports)
        if supports
        else None
    )

    resistance = (
        min(resistances)
        if resistances
        else None
    )

    return support, resistance


# ==================================================================
# LIVE SIGNAL MAP
# ==================================================================

def build_signal_map(
    df: pd.DataFrame,
    technical: Any,
    decision: Any,
) -> dict[str, Any]:

    current = safe_float(
        df["Close"].iloc[-1]
    )

    ema9 = opt_float(
        df["EMA9"].iloc[-1]
    )
    ema21 = opt_float(
        df["EMA21"].iloc[-1]
    )
    sma50 = opt_float(
        df["SMA50"].iloc[-1]
    )
    sma200 = opt_float(
        df["SMA200"].iloc[-1]
    )
    rsi = opt_float(
        df["RSI14"].iloc[-1]
    )
    macd_hist = opt_float(
        df["MACDHist"].iloc[-1]
    )
    rel_volume = opt_float(
        df["RelativeVolume"].iloc[-1]
    )
    atr = opt_float(
        df["ATR14"].iloc[-1]
    )

    support, resistance = (
        support_resistance(df)
    )

    trend_points = 0

    if ema9 is not None and ema21 is not None:
        trend_points += 1 if ema9 > ema21 else -1

    if (
        current > 0
        and sma50 is not None
    ):
        trend_points += 1 if current > sma50 else -1

    if (
        current > 0
        and sma200 is not None
    ):
        trend_points += 1 if current > sma200 else -1

    momentum_points = 0

    if rsi is not None:
        if 52 <= rsi <= 68:
            momentum_points += 2
        elif 45 <= rsi < 52:
            momentum_points += 1
        elif 68 < rsi <= 75:
            momentum_points -= 1
        elif rsi > 75:
            momentum_points -= 2
        elif rsi < 35:
            momentum_points += 1

    if macd_hist is not None:
        momentum_points += (
            1 if macd_hist > 0 else -1
        )

    volume_points = 0

    if rel_volume is not None:
        if rel_volume >= 1.5:
            volume_points += 2
        elif rel_volume >= 1.0:
            volume_points += 1
        elif rel_volume < .70:
            volume_points -= 1

    trend_score = max(
        0,
        min(
            100,
            50 + trend_points * 16,
        ),
    )

    momentum_score = max(
        0,
        min(
            100,
            50 + momentum_points * 15,
        ),
    )

    volume_score = max(
        0,
        min(
            100,
            50 + volume_points * 20,
        ),
    )

    technical_score = opt_float(
        first_value(
            decision,
            ["score", "technical_score"],
        )
    )

    # If the production engine has a score, display it.
    # The new signal map is supplemental and never overwrites it.
    display_score = (
        technical_score
        if technical_score is not None
        else round(
            trend_score * .40
            + momentum_score * .40
            + volume_score * .20
        )
    )

    if (
        trend_points >= 2
        and momentum_points >= 1
        and volume_points >= 0
    ):
        setup = "BULLISH SETUP"
        setup_icon = "🟢"

    elif (
        trend_points <= -2
        and momentum_points <= -1
    ):
        setup = "BEARISH SETUP"
        setup_icon = "🔴"

    else:
        setup = "MIXED / WAIT"
        setup_icon = "🟡"

    buy_zone_low = None
    buy_zone_high = None
    target1 = None
    target2 = None
    invalidation = None

    if atr is not None and atr > 0:

        buy_zone_low = (
            current - atr * .75
        )

        buy_zone_high = (
            current + atr * .15
        )

        target1 = (
            current + atr * 1.5
        )

        target2 = (
            current + atr * 2.5
        )

        invalidation = (
            current - atr * 1.25
        )

    if resistance is not None:
        target1 = (
            resistance
            if resistance > current
            else target1
        )

    return {
        "current": current,
        "ema9": ema9,
        "ema21": ema21,
        "sma50": sma50,
        "sma200": sma200,
        "rsi": rsi,
        "macd_hist": macd_hist,
        "relative_volume": rel_volume,
        "atr": atr,
        "support": support,
        "resistance": resistance,
        "trend_score": trend_score,
        "momentum_score": momentum_score,
        "volume_score": volume_score,
        "technical_score": display_score,
        "setup": setup,
        "setup_icon": setup_icon,
        "buy_zone_low": buy_zone_low,
        "buy_zone_high": buy_zone_high,
        "target1": target1,
        "target2": target2,
        "invalidation": invalidation,
    }


# ==================================================================
# CHART
# ==================================================================

def build_price_chart(
    df: pd.DataFrame,
    ticker: str,
    signals: dict[str, Any],
) -> go.Figure:

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=.018,
        row_heights=[.68, .17, .15],
    )

    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=ticker,
            increasing=dict(
                line=dict(color="#22d68a"),
                fillcolor="#22d68a",
            ),
            decreasing=dict(
                line=dict(color="#ff5f73"),
                fillcolor="#ff5f73",
            ),
        ),
        row=1,
        col=1,
    )

    for column, label, color in [
        ("EMA9", "EMA 9", "#67e8f9"),
        ("EMA21", "EMA 21", "#4c9cff"),
        ("SMA50", "SMA 50", "#f2c75c"),
        ("SMA200", "SMA 200", "#a978ff"),
    ]:

        if column in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[column],
                    mode="lines",
                    name=label,
                    line=dict(
                        color=color,
                        width=1.35,
                    ),
                    connectgaps=False,
                ),
                row=1,
                col=1,
            )

    if "BBUpper" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["BBUpper"],
                mode="lines",
                name="BB Upper",
                line=dict(
                    color="rgba(150,170,190,.35)",
                    width=1,
                    dash="dot",
                ),
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["BBLower"],
                mode="lines",
                name="BB Lower",
                line=dict(
                    color="rgba(150,170,190,.35)",
                    width=1,
                    dash="dot",
                ),
                fill="tonexty",
                fillcolor="rgba(100,130,160,.035)",
            ),
            row=1,
            col=1,
        )

    # Pattern markers
    pattern = detect_patterns(df)

    if pattern:
        last = df.iloc[-1]
        marker_color = (
            "#22d68a"
            if pattern[0]["signal"] == "BULLISH"
            else "#ff5f73"
            if pattern[0]["signal"] == "BEARISH"
            else "#f2c75c"
        )

        fig.add_trace(
            go.Scatter(
                x=[df.index[-1]],
                y=[safe_float(last["High"])],
                mode="markers+text",
                text=[pattern[0]["name"]],
                textposition="top center",
                marker=dict(
                    size=9,
                    color=marker_color,
                ),
                name="Pattern",
                hovertemplate=(
                    pattern[0]["name"]
                    + "<extra></extra>"
                ),
            ),
            row=1,
            col=1,
        )

    # Volume
    volume_colors = np.where(
        df["Close"] >= df["Open"],
        "rgba(34,214,138,.30)",
        "rgba(255,95,115,.30)",
    )

    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            marker_color=volume_colors,
            name="Volume",
        ),
        row=2,
        col=1,
    )

    # RSI
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["RSI14"],
            mode="lines",
            name="RSI 14",
            line=dict(
                color="#67e8f9",
                width=1.5,
            ),
        ),
        row=3,
        col=1,
    )

    fig.add_hline(
        y=70,
        line_dash="dot",
        line_color="rgba(255,95,115,.5)",
        row=3,
        col=1,
    )

    fig.add_hline(
        y=30,
        line_dash="dot",
        line_color="rgba(34,214,138,.5)",
        row=3,
        col=1,
    )

    fig.update_layout(
        height=690,
        margin=dict(
            l=10,
            r=55,
            t=10,
            b=10,
            pad=0,
        ),
        paper_bgcolor="#08131f",
        plot_bgcolor="#08131f",
        font=dict(
            color="#cdd8e4",
            size=9,
        ),
        hovermode="x unified",
        dragmode="pan",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0,
            font=dict(size=8),
        ),
        xaxis_rangeslider_visible=False,
        modebar=dict(
            bgcolor="rgba(0,0,0,0)",
            color="#718398",
            activecolor="#22d68a",
        ),
    )

    # Explicit axis rows. Do not derive the row from the last subplot axis:
    # "xaxis" ends with "s", which causes KeyError: 's'.
    for row_number in (1, 2, 3):
        fig.update_xaxes(
            row=row_number,
            col=1,
            showgrid=False,
            zeroline=False,
        )

    fig.update_yaxes(
        row=1,
        col=1,
        side="right",
        showgrid=True,
        gridcolor="rgba(255,255,255,.045)",
        zeroline=False,
    )

    fig.update_yaxes(
        row=2,
        col=1,
        side="right",
        showgrid=False,
        zeroline=False,
    )

    fig.update_yaxes(
        row=3,
        col=1,
        side="right",
        range=[0, 100],
        showgrid=True,
        gridcolor="rgba(255,255,255,.035)",
        zeroline=False,
    )

    return fig


def render_chart(
    ticker: str,
    df: pd.DataFrame,
    signals: dict[str, Any],
):

    st.subheader("📈 Live Price & Technical Map")

    st.caption(
        "Price visualization + supplemental signal map. "
        "The production BUY / SELL Decision Engine remains independent."
    )

    selected = st.segmented_control(
        "Chart range",
        ["1D", "5D", "1M", "3M", "6M", "1Y", "5Y"],
        default=st.session_state.chart_range,
        key="hq_chart_range",
        label_visibility="collapsed",
    )

    if selected is None:
        selected = "6M"

    st.session_state.chart_range = selected

    periods = {
        "1D": 1,
        "5D": 5,
        "1M": 22,
        "3M": 66,
        "6M": 132,
        "1Y": 252,
        "5Y": 1260,
    }

    chart_df = df.tail(
        min(
            periods[selected],
            len(df),
        )
    )

    fig = build_price_chart(
        chart_df,
        ticker,
        signals,
    )

    st.plotly_chart(
        fig,
        width="stretch",
        config={
            "displaylogo": False,
            "responsive": True,
            "scrollZoom": True,
            "displayModeBar": True,
        },
    )


# ==================================================================
# LIVE QUOTE
# ==================================================================

@st.cache_data(ttl=2, show_spinner=False)
def fetch_live_quote(ticker: str) -> dict[str, Any]:
    """
    Single source of truth for live quotes.

    Uses app.data.live_quotes.get_live_quote()
    so Dashboard, Portfolio and other modules can rely
    on the same normalized quote structure.
    """

    try:
        from app.data.live_quotes import get_live_quote

        quote = get_live_quote(ticker)

        if not isinstance(quote, dict):
            return {
                "ticker": ticker.upper(),
                "price": None,
                "previous": None,
                "change": None,
                "change_pct": None,
                "source": None,
                "status": "UNAVAILABLE",
            }

        return {
            "ticker": quote.get("ticker", ticker.upper()),
            "price": quote.get("price"),
            "previous": quote.get("previous"),
            "change": quote.get("change"),
            "change_pct": quote.get("change_pct"),
            "source": quote.get("source"),
            "status": quote.get("status", "UNKNOWN"),
            "timestamp": quote.get("timestamp"),
            "errors": quote.get("errors", []),
        }

    except Exception as exc:
        return {
            "ticker": str(ticker or "").upper(),
            "price": None,
            "previous": None,
            "change": None,
            "change_pct": None,
            "source": None,
            "status": "ERROR",
            "errors": [str(exc)],
        }

def render_live_header(
    ticker: str,
    df: pd.DataFrame,
):
    """
    Premium live market header.

    Live quote comes from the canonical quote service.
    Historical Close is used only as a fallback.
    """

    quote = fetch_live_quote(ticker)

    # ------------------------------------------------------------
    # Historical fallback
    # ------------------------------------------------------------

    historical_price = None

    try:
        if df is not None and not df.empty and "Close" in df.columns:
            historical_price = safe_float(
                df["Close"].dropna().iloc[-1]
            )
    except Exception:
        historical_price = None

    # ------------------------------------------------------------
    # Live price
    # ------------------------------------------------------------

    live_price = safe_float(
        quote.get("price")
    )

    price = (
        live_price
        if live_price is not None and live_price > 0
        else historical_price
    )

    # ------------------------------------------------------------
    # Change
    # ------------------------------------------------------------

    change_pct = safe_float(
        quote.get("change_pct")
    )

    change = safe_float(
        quote.get("change")
    )

    status = str(
        quote.get("status") or "UNKNOWN"
    )

    source = (
        quote.get("source")
        or "Market data"
    )

    # ------------------------------------------------------------
    # Header layout
    # ------------------------------------------------------------

    title_col, price_col, change_col, status_col = st.columns(
        [4.2, 2.0, 1.8, 2.0],
        vertical_alignment="center",
    )

    # ------------------------------------------------------------
    # Company / ticker
    # ------------------------------------------------------------

    with title_col:

        st.title(
            f"{ticker.upper()} · HaViQuant"
        )

        st.caption(
            "INTELLIGENT MARKET ANALYSIS"
        )

    # ------------------------------------------------------------
    # LIVE PRICE
    # ------------------------------------------------------------

    with price_col:

        if price is not None:

            st.metric(
                "Live Price",
                f"${price:,.2f}",
            )

        else:

            st.metric(
                "Live Price",
                "N/A",
            )

    # ------------------------------------------------------------
    # DAILY CHANGE
    # ------------------------------------------------------------

    with change_col:

        if change_pct is not None:

            st.metric(
                "Today",
                f"{change_pct:+.2f}%",
                (
                    f"${change:+,.2f}"
                    if change is not None
                    else None
                ),
            )

        else:

            st.metric(
                "Today",
                "N/A",
            )

    # ------------------------------------------------------------
    # DATA STATUS
    # ------------------------------------------------------------

    with status_col:

        if status == "LIVE":

            st.success(
                "● LIVE MARKET DATA"
            )

        elif status == "LAST_AVAILABLE":

            st.warning(
                "● LAST AVAILABLE"
            )

        elif status == "UNAVAILABLE":

            st.error(
                "● DATA UNAVAILABLE"
            )

        else:

            st.info(
                "● MARKET DATA"
            )

        st.caption(
            f"Source: {source}"
        )
# ==================================================================
# NEWS
# ==================================================================

def news_category(title: str) -> str:
    text = title.lower()

    groups = {
        "Earnings": [
            "earnings",
            "revenue",
            "profit",
            "eps",
            "guidance",
        ],
        "Management": [
            "ceo",
            "cfo",
            "executive",
            "leadership",
        ],
        "Analyst": [
            "upgrade",
            "downgrade",
            "analyst",
            "price target",
        ],
        "Regulatory": [
            "sec",
            "lawsuit",
            "regulatory",
            "investigation",
            "antitrust",
        ],
        "Technology": [
            "ai",
            "chip",
            "technology",
            "product",
            "launch",
        ],
    }

    for category, words in groups.items():
        if any(word in text for word in words):
            return category

    return "Market"


def news_sentiment(title: str) -> tuple[str, str]:
    text = title.lower()

    positive = [
        "beat",
        "beats",
        "upgrade",
        "surge",
        "growth",
        "record",
        "strong",
        "bullish",
        "approval",
        "approved",
        "wins",
        "buy",
    ]

    negative = [
        "miss",
        "misses",
        "downgrade",
        "fall",
        "falls",
        "drop",
        "weak",
        "loss",
        "bearish",
        "lawsuit",
        "investigation",
        "warning",
        "sell",
    ]

    p = sum(word in text for word in positive)
    n = sum(word in text for word in negative)

    if p > n:
        return "Positive", "🟢"
    if n > p:
        return "Negative", "🔴"
    return "Neutral", "🟡"


@st.cache_data(ttl=300, show_spinner=False)
def fetch_news(ticker: str) -> list[dict[str, Any]]:

    # Provider 1
    url = (
        "https://query1.finance.yahoo.com/"
        "v1/finance/search?"
        f"q={quote(ticker)}"
        "&quotesCount=1"
        "&newsCount=10"
        "&enableFuzzyQuery=false"
    )

    payload = http_json(url)
    results = []

    if payload:
        for item in payload.get("news", []):
            if not isinstance(item, dict):
                continue

            title = safe_text(
                item.get("title"),
                "",
            )
            link = safe_text(
                item.get("link"),
                "",
            )

            if not title or not link:
                continue

            sentiment, icon = news_sentiment(title)

            published = "Recent"

            try:
                timestamp = item.get(
                    "providerPublishTime"
                )

                if timestamp:
                    published = relative_time(
                        datetime.fromtimestamp(
                            float(timestamp),
                            tz=timezone.utc,
                        )
                    )
            except Exception:
                pass

            results.append(
                {
                    "title": title,
                    "link": link,
                    "publisher": safe_text(
                        item.get(
                            "publisher",
                            "Yahoo Finance",
                        ),
                        "Yahoo Finance",
                    ),
                    "published": published,
                    "category": news_category(title),
                    "sentiment": sentiment,
                    "icon": icon,
                }
            )

    if results:
        return results[:10]

    # Provider 2
    query = f'"{ticker}" stock when:2d'

    rss_url = (
        "https://news.google.com/rss/search?"
        f"q={quote(query)}"
        "&hl=en-US&gl=US&ceid=US:en"
    )

    request = Request(
        rss_url,
        headers={
            "User-Agent": "Mozilla/5.0 HaViQuant",
        },
    )

    try:
        with urlopen(
            request,
            timeout=12,
        ) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)

        for item in root.findall(".//item"):

            title_node = item.find("title")
            link_node = item.find("link")
            date_node = item.find("pubDate")
            source_node = item.find("source")

            title = safe_text(
                title_node.text if title_node is not None else None,
                "",
            )
            link = safe_text(
                link_node.text if link_node is not None else None,
                "",
            )

            if not title or not link:
                continue

            sentiment, icon = news_sentiment(title)

            published = "Recent"

            try:
                if date_node is not None and date_node.text:
                    published = relative_time(
                        parsedate_to_datetime(
                            date_node.text
                        )
                    )
            except Exception:
                pass

            results.append(
                {
                    "title": title,
                    "link": link,
                    "publisher": safe_text(
                        source_node.text
                        if source_node is not None
                        else None,
                        "Google News",
                    ),
                    "published": published,
                    "category": news_category(title),
                    "sentiment": sentiment,
                    "icon": icon,
                }
            )

            if len(results) >= 10:
                break

    except Exception:
        return []

    return results



def render_price_move_explanation(ticker: str, df: pd.DataFrame, sector: Optional[str] = None):
    """Explain the current move without pretending to prove causation."""
    try:
        articles = fetch_news(ticker)
        from app.market_move_intelligence import explain_move as _explain_move
        info = _explain_move(ticker, df, articles=articles, sector=sector)
    except Exception as exc:
        st.warning(f"Move intelligence unavailable: {exc}")
        return

    direction = info.get("direction", "FLAT")
    move = float(info.get("move_pct") or 0)
    icon = "🟢" if direction == "UP" else "🔴" if direction == "DOWN" else "🟡"
    title = "Why the stock moved UP" if direction == "UP" else "Why the stock moved DOWN" if direction == "DOWN" else "Why the stock is FLAT"

    st.markdown('<div class="hq-card">', unsafe_allow_html=True)
    st.markdown(f"### {icon} {title}")
    st.caption(info.get("explanation", "Evidence-based attribution layer."))
    a,b,c,d = st.columns(4)
    with a:
        st.metric("Today", f"{move:+.2f}%")
    with b:
        m = info.get("market_5d")
        st.metric("SPY recent", f"{m:+.2f}%" if m is not None else "N/A")
    with c:
        s = info.get("sector_5d")
        st.metric("Sector recent", f"{s:+.2f}%" if s is not None else "N/A")
    with d:
        vr = info.get("volume_ratio")
        st.metric("Volume", f"{vr:.2f}×" if vr is not None else "N/A")

    drivers = info.get("drivers", [])
    risks = info.get("risks", [])
    left,right = st.columns(2)
    with left:
        st.markdown("**Likely contributors**")
        if drivers:
            for item in drivers:
                st.markdown(f"🟢 **{item.get('label','Signal')}** — {item.get('evidence','')}")
        else:
            st.info("No strong positive contributor was independently confirmed.")
    with right:
        st.markdown("**Opposing / risk evidence**")
        if risks:
            for item in risks:
                st.markdown(f"🔴 **{item.get('label','Risk')}** — {item.get('evidence','')}")
        else:
            st.info("No strong opposing evidence was independently confirmed.")

    news_info=info.get("news", {})
    st.caption(
        f"News: {news_info.get('label','N/A')} · "
        f"Sector: {info.get('sector','Unknown')} · "
        f"Attribution confidence: {info.get('confidence','LOW')}"
    )

    # Recent headline evidence is kept compact and separate from the price chart.
    articles = fetch_news(ticker)
    if articles:
        with st.expander("📰 Headline evidence behind the explanation", expanded=False):
            for item in articles[:5]:
                st.markdown(f"**{item.get('icon','📰')} {item.get('title','')}**")
                st.caption(f"{item.get('publisher','')} · {item.get('published','')} · {item.get('category','')} · {item.get('sentiment','')}")
    st.markdown("</div>", unsafe_allow_html=True)


def render_news(ticker: str):

    articles = fetch_news(ticker)

    st.markdown(
        '<div class="hq-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        "### 📰 Live Market News"
    )

    st.caption(
        "Recent company-specific headlines · display-only"
    )

    if not articles:
        st.info(
            "No recent news returned by the available public feeds."
        )
    else:
        with st.container(
            height=335,
            border=False,
        ):
            for item in articles:

                st.markdown(
                    f"**{item['icon']} "
                    f"[{item['title']}]({item['link']})**"
                )

                st.caption(
                    f"{item['publisher']} · "
                    f"{item['published']} · "
                    f"{item['category']} · "
                    f"{item['sentiment']}"
                )

                st.divider()

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# ==================================================================
# INSIDER INTELLIGENCE
# ==================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def sec_company_cik(ticker: str) -> Optional[str]:

    payload = http_json(
        "https://www.sec.gov/files/company_tickers.json"
    )

    if not payload:
        return None

    for item in payload.values():
        if (
            safe_text(
                item.get("ticker"),
                "",
            ).upper()
            == ticker.upper()
        ):
            cik = item.get("cik_str")
            if cik is not None:
                return str(
                    int(cik)
                ).zfill(10)

    return None


def sec_get_xml(
    cik: str,
    accession: str,
    document: str,
) -> Optional[ET.Element]:

    clean = accession.replace(
        "-",
        "",
    )

    url = (
        "https://www.sec.gov/Archives/"
        f"edgar/data/{int(cik)}/"
        f"{clean}/{document}"
    )

    request = Request(
        url,
        headers={
            "User-Agent":
                "HaViQuant research contact@example.com",
        },
    )

    try:
        with urlopen(
            request,
            timeout=15,
        ) as response:
            return ET.fromstring(
                response.read()
            )
    except Exception:
        return None


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_insider_transactions(
    ticker: str,
) -> list[dict[str, Any]]:

    cik = sec_company_cik(
        ticker
    )

    if not cik:
        return []

    submissions_url = (
        "https://data.sec.gov/submissions/"
        f"CIK{cik}.json"
    )

    payload = http_json(
        submissions_url
    )

    if not payload:
        return []

    recent = payload.get(
        "filings",
        {},
    ).get(
        "recent",
        {},
    )

    forms = recent.get(
        "form",
        [],
    )

    accessions = recent.get(
        "accessionNumber",
        [],
    )

    documents = recent.get(
        "primaryDocument",
        [],
    )

    filing_dates = recent.get(
        "filingDate",
        [],
    )

    results = []

    for i, form in enumerate(forms):

        if form not in {"4", "4/A"}:
            continue

        if i >= len(accessions):
            continue

        xml_root = sec_get_xml(
            cik,
            accessions[i],
            documents[i] if i < len(documents) else "",
        )

        if xml_root is None:
            continue

        # XML namespaces vary. Search by local-name.
        def find_all_local(name: str):
            return [
                node
                for node in xml_root.iter()
                if node.tag.split("}")[-1] == name
            ]

        owners = find_all_local(
            "reportingOwner"
        )

        owner_name = "Insider"

        role = "Officer / Director"

        if owners:
            owner = owners[0]

            for node in owner.iter():
                local = node.tag.split("}")[-1]

                if local == "rptOwnerName":
                    if node.text:
                        owner_name = node.text.strip()

                if local == "officerTitle":
                    if node.text:
                        role = node.text.strip()

        transactions = []

        for node in find_all_local(
            "nonDerivativeTransaction"
        ):

            def child_text(
                parent,
                wanted,
            ):
                for child in parent.iter():
                    if (
                        child.tag.split("}")[-1]
                        == wanted
                    ):
                        return (
                            child.text.strip()
                            if child.text
                            else None
                        )
                return None

            code = child_text(
                node,
                "transactionCode",
            )

            shares = opt_float(
                child_text(
                    node,
                    "transactionShares",
                )
            )

            price = opt_float(
                child_text(
                    node,
                    "transactionPricePerShare",
                )
            )

            transaction_date = (
                child_text(
                    node,
                    "transactionDate",
                )
            )

            if code not in {
                "P",
                "S",
            }:
                continue

            value = (
                shares * price
                if shares is not None
                and price is not None
                else None
            )

            transactions.append(
                {
                    "owner": owner_name,
                    "role": role,
                    "code": code,
                    "action": (
                        "BUY"
                        if code == "P"
                        else "SELL"
                    ),
                    "shares": shares,
                    "price": price,
                    "value": value,
                    "transaction_date":
                        transaction_date,
                    "filing_date":
                        filing_dates[i]
                        if i < len(filing_dates)
                        else "N/A",
                }
            )

        results.extend(
            transactions
        )

        if len(results) >= 20:
            break

    return results[:20]


def render_insiders(ticker: str):

    transactions = (
        fetch_insider_transactions(
            ticker
        )
    )

    buys = [
        x for x in transactions
        if x["action"] == "BUY"
    ]

    sells = [
        x for x in transactions
        if x["action"] == "SELL"
    ]

    buy_value = sum(
        safe_float(x["value"])
        for x in buys
    )

    sell_value = sum(
        safe_float(x["value"])
        for x in sells
    )

    net = buy_value - sell_value

    st.markdown(
        '<div class="hq-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        "### 👔 Insider Intelligence"
    )

    st.caption(
        "Confirmed open-market Form 4 transactions only. "
        "Awards, gifts, tax withholding and option exercises are excluded."
    )

    if not transactions:

        st.info(
            "No usable open-market Form 4 transactions were returned."
        )

        st.caption(
            "No data returned does not prove that no insider traded."
        )

    else:

        signal = (
            "🟢 NET BUYING"
            if net > 0
            else "🔴 NET SELLING"
            if net < 0
            else "🟡 BALANCED"
        )

        st.markdown(
            f"### {signal}"
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "Open-market buys",
                money(buy_value),
            )

        with c2:
            st.metric(
                "Open-market sells",
                money(sell_value),
            )

        with c3:
            st.metric(
                "Net flow",
                money(net),
            )

        for item in transactions[:8]:

            action_icon = (
                "🟢"
                if item["action"] == "BUY"
                else "🔴"
            )

            value_text = money(
                item["value"]
            )

            shares_text = (
                f"{item['shares']:,.0f} shares"
                if item["shares"] is not None
                else "Shares N/A"
            )

            price_text = (
                f" @ ${item['price']:,.2f}"
                if item["price"] is not None
                else ""
            )

            st.markdown(
                f"**{action_icon} {item['owner']}**  \n"
                f"{item['role']} · "
                f"**{item['action']}** · "
                f"{shares_text}{price_text} · "
                f"**{value_text}**"
            )

            st.caption(
                f"Trade: {item['transaction_date']} · "
                f"Filed: {item['filing_date']}"
            )

            st.divider()

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# ==================================================================
# FAIR VALUE
# ==================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def get_fundamentals(
    ticker: str,
) -> dict[str, Any]:

    if yf is None:
        return {}

    try:
        t = yf.Ticker(ticker)

        info = t.info

        if not isinstance(info, dict):
            return {}

        return info

    except Exception:
        return {}


def fair_value_model(
    ticker: str,
) -> dict[str, Any]:

    info = get_fundamentals(
        ticker
    )

    if not info:
        return {
            "available": False,
            "reason": (
                "Fundamental provider did not return usable data."
            ),
        }

    current = opt_float(
        info.get(
            "currentPrice"
        )
        or info.get(
            "regularMarketPrice"
        )
    )

    forward_eps = opt_float(
        info.get(
            "forwardEps"
        )
    )

    trailing_eps = opt_float(
        info.get(
            "trailingEps"
        )
    )

    revenue_growth = opt_float(
        info.get(
            "revenueGrowth"
        )
    )

    target_mean = opt_float(
        info.get(
            "targetMeanPrice"
        )
    )

    free_cash_flow = opt_float(
        info.get(
            "freeCashflow"
        )
    )

    shares = opt_float(
        info.get(
            "sharesOutstanding"
        )
    )

    methods = {}

    # Analyst reference is NOT a fundamental intrinsic value.
    # It is shown separately and never silently blended as fact.
    if target_mean is not None and target_mean > 0:
        methods["Analyst reference"] = target_mean

    eps = (
        forward_eps
        if forward_eps is not None
        else trailing_eps
    )

    if eps is not None and eps > 0:

        growth = (
            revenue_growth
            if revenue_growth is not None
            else .05
        )

        multiple = min(
            35,
            max(
                12,
                18 + growth * 100 * .50,
            ),
        )

        methods["Growth-adjusted P/E"] = (
            eps * multiple
        )

    if (
        free_cash_flow is not None
        and free_cash_flow > 0
        and shares is not None
        and shares > 0
    ):

        fcf_per_share = (
            free_cash_flow / shares
        )

        methods["FCF yield reference"] = (
            fcf_per_share / .045
        )

    fundamental_methods = [
        value
        for name, value in methods.items()
        if name != "Analyst reference"
        and value is not None
        and value > 0
    ]

    if not fundamental_methods:

        return {
            "available": False,
            "reason": (
                "Usable EPS or free-cash-flow inputs were not "
                "available for a transparent fundamental estimate."
            ),
            "current": current,
            "methods": methods,
        }

    base = float(
        np.median(
            fundamental_methods
        )
    )

    bear = base * .80
    bull = base * 1.20

    upside = (
        (base / current - 1) * 100
        if current is not None
        and current > 0
        else None
    )

    confidence = (
        "High"
        if len(fundamental_methods) >= 2
        else "Moderate"
    )

    return {
        "available": True,
        "current": current,
        "bear": bear,
        "base": base,
        "bull": bull,
        "upside": upside,
        "confidence": confidence,
        "methods": methods,
        "eps": eps,
        "revenue_growth": revenue_growth,
        "free_cash_flow": free_cash_flow,
    }


def render_fair_value(
    ticker: str,
):

    valuation = fair_value_model(
        ticker
    )

    st.markdown(
        '<div class="hq-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        "### 💰 HaViQuant Fair Value"
    )

    st.caption(
        "Fundamental valuation. Chart data is not used to manufacture fair value."
    )

    if not valuation.get(
        "available",
        False,
    ):

        st.info(
            valuation.get(
                "reason",
                "Fair value unavailable.",
            )
        )

        if valuation.get("current") is not None:
            st.metric(
                "Current Price",
                f"${valuation['current']:,.2f}",
            )

        methods = valuation.get(
            "methods",
            {},
        )

        if methods:

            st.markdown(
                "#### Available reference values"
            )

            for name, value in methods.items():

                st.write(
                    f"**{name}:** "
                    f"${value:,.2f}"
                    if value is not None
                    else f"**{name}:** N/A"
                )

    else:

        c1, c2 = st.columns(2)

        with c1:
            st.metric(
                "Base Fair Value",
                f"${valuation['base']:,.2f}",
            )

        with c2:
            upside = valuation.get(
                "upside"
            )

            st.metric(
                "Upside / Downside",
                (
                    f"{upside:+.1f}%"
                    if upside is not None
                    else "N/A"
                ),
            )

        a, b, c = st.columns(3)

        with a:
            st.metric(
                "Bear",
                f"${valuation['bear']:,.2f}",
            )

        with b:
            st.metric(
                "Base",
                f"${valuation['base']:,.2f}",
            )

        with c:
            st.metric(
                "Bull",
                f"${valuation['bull']:,.2f}",
            )

        st.caption(
            f"Confidence: {valuation['confidence']}"
        )

        st.markdown(
            "#### Model Inputs"
        )

        i1, i2, i3 = st.columns(3)

        with i1:
            st.metric(
                "EPS",
                (
                    f"${valuation['eps']:.2f}"
                    if valuation.get("eps") is not None
                    else "N/A"
                ),
            )

        with i2:
            growth = valuation.get(
                "revenue_growth"
            )

            st.metric(
                "Revenue Growth",
                (
                    f"{growth*100:.1f}%"
                    if growth is not None
                    else "N/A"
                ),
            )

        with i3:
            st.metric(
                "Free Cash Flow",
                money(
                    valuation.get(
                        "free_cash_flow"
                    )
                ),
            )

        st.markdown(
            "#### Valuation References"
        )

        for name, value in valuation["methods"].items():

            st.write(
                f"**{name}:** "
                + (
                    f"${value:,.2f}"
                    if value is not None
                    else "N/A"
                )
            )

    st.caption(
        "Fair value is an estimate. It is not a guaranteed price target."
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# ==================================================================
# SIGNAL DASHBOARD
# ==================================================================

def render_signal_dashboard(
    signals: dict[str, Any],
    decision: Any,
):

    st.subheader(
        "🎯 HaViQuant Signal Intelligence"
    )

    st.caption(
        "The signal map expands technical diagnostics. "
        "The production Decision Engine remains authoritative for BUY / SELL."
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Technical Score",
            (
                f"{signals['technical_score']:.0f}/100"
                if signals["technical_score"] is not None
                else "N/A"
            ),
        )

    with c2:
        st.metric(
            "Trend",
            f"{signals['trend_score']:.0f}/100",
        )

    with c3:
        st.metric(
            "Momentum",
            f"{signals['momentum_score']:.0f}/100",
        )

    with c4:
        st.metric(
            "Volume",
            f"{signals['volume_score']:.0f}/100",
        )

    st.markdown(
        f"""
        <div class="hq-signal">
            <div class="hq-title">
                {signals['setup_icon']} {signals['setup']}
            </div>
            <div class="hq-sub">
                Supplemental technical setup. Not a replacement
                for the production Decision Engine.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Support",
            (
                f"${signals['support']:,.2f}"
                if signals["support"] is not None
                else "N/A"
            ),
        )

    with c2:
        st.metric(
            "Resistance",
            (
                f"${signals['resistance']:,.2f}"
                if signals["resistance"] is not None
                else "N/A"
            ),
        )

    with c3:
        st.metric(
            "RSI 14",
            (
                f"{signals['rsi']:.1f}"
                if signals["rsi"] is not None
                else "N/A"
            ),
        )

    with c4:
        st.metric(
            "Relative Volume",
            (
                f"{signals['relative_volume']:.2f}x"
                if signals["relative_volume"] is not None
                else "N/A"
            ),
        )

    st.markdown(
        "#### Risk / Reward Map"
    )

    r1, r2, r3, r4 = st.columns(4)

    with r1:
        st.metric(
            "Potential Buy Zone",
            (
                f"${signals['buy_zone_low']:,.2f} – "
                f"${signals['buy_zone_high']:,.2f}"
                if signals["buy_zone_low"] is not None
                else "N/A"
            ),
        )

    with r2:
        st.metric(
            "Target 1",
            (
                f"${signals['target1']:,.2f}"
                if signals["target1"] is not None
                else "N/A"
            ),
        )

    with r3:
        st.metric(
            "Target 2",
            (
                f"${signals['target2']:,.2f}"
                if signals["target2"] is not None
                else "N/A"
            ),
        )

    with r4:
        st.metric(
            "Invalidation",
            (
                f"${signals['invalidation']:,.2f}"
                if signals["invalidation"] is not None
                else "N/A"
            ),
        )

    patterns = detect_patterns(
        st.session_state._hq_df
    )

    st.markdown(
        "#### Recent Pattern Scan"
    )

    pcols = st.columns(
        min(4, len(patterns))
    )

    for col, pattern in zip(
        pcols,
        patterns[:4],
    ):

        with col:

            icon = (
                "🟢"
                if pattern["signal"] == "BULLISH"
                else "🔴"
                if pattern["signal"] == "BEARISH"
                else "🟡"
            )

            st.write(
                f"{icon} **{pattern['name']}**"
            )

            st.caption(
                pattern["detail"]
            )


# ==================================================================
# EXISTING DECISION DISPLAY
# ==================================================================

def render_production_decision(
    decision: Any,
):

    signal = safe_text(
        first_value(
            decision,
            ["signal"],
            "UNKNOWN",
        )
    )

    score = opt_float(
        first_value(
            decision,
            [
                "score",
                "technical_score",
            ],
        )
    )

    st.subheader(
        "🧠 Production Decision Engine"
    )

    if "BUY" in signal.upper():
        st.success(
            f"🟢 {signal.upper()}"
        )
    elif "SELL" in signal.upper():
        st.error(
            f"🔴 {signal.upper()}"
        )
    elif "INSUFFICIENT" in signal.upper():
        st.warning(
            "⚠️ INSUFFICIENT DATA"
        )
    else:
        st.info(
            f"🟡 {signal.upper()}"
        )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Technical Score",
            (
                f"{score:.0f}/100"
                if score is not None
                else "N/A"
            ),
        )

    with c2:
        st.metric(
            "Trend",
            safe_text(
                first_value(
                    decision,
                    ["trend"],
                    "N/A",
                )
            ),
        )

    with c3:
        st.metric(
            "Setup",
            safe_text(
                first_value(
                    decision,
                    ["setup"],
                    "N/A",
                )
            ),
        )

    reasons = first_value(
        decision,
        ["reasons"],
        [],
    )

    if reasons:
        with st.expander(
            "Why the existing engine decided this",
            expanded=False,
        ):
            for reason in reasons:
                st.write(
                    f"• {reason}"
                )

    st.caption(
        "News, insider activity, fair value and supplemental pattern analysis "
        "do not alter this production decision."
    )


# ==================================================================
# TECHNICAL CONTEXT
# ==================================================================

def render_technical_context(
    technical: Any,
    df: pd.DataFrame,
):

    st.subheader(
        "Technical Context"
    )

    rsi = opt_float(
        first_value(
            technical,
            ["rsi"],
        )
    )

    macd = opt_float(
        first_value(
            technical,
            ["macd"],
        )
    )

    macd_signal = opt_float(
        first_value(
            technical,
            [
                "macd_signal",
                "macdSignal",
            ],
        )
    )

    volume = opt_float(
        first_value(
            technical,
            ["volume"],
        )
    )

    avg_volume = opt_float(
        first_value(
            technical,
            [
                "avg_volume_20",
                "average_volume_20",
            ],
        )
    )

    ratio = (
        volume / avg_volume
        if volume is not None
        and avg_volume is not None
        and avg_volume > 0
        else None
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.metric(
            "RSI",
            f"{rsi:.2f}" if rsi is not None else "N/A",
        )

    with c2:
        st.metric(
            "MACD",
            f"{macd:.2f}" if macd is not None else "N/A",
        )

    with c3:
        st.metric(
            "MACD Signal",
            (
                f"{macd_signal:.2f}"
                if macd_signal is not None
                else "N/A"
            ),
        )

    with c4:
        st.metric(
            "Volume",
            (
                f"{ratio:.2f}x"
                if ratio is not None
                else "N/A"
            ),
        )

    with c5:
        st.metric(
            "ATR",
            (
                f"${safe_float(df['ATR14'].iloc[-1]):.2f}"
                if "ATR14" in df.columns
                else "N/A"
            ),
        )


# ==================================================================
# PREMIUM COMMAND HEADER
# ==================================================================

def render_command_header(page: str, ticker: str):
    now = datetime.now().strftime("%H:%M:%S")
    refresh_state = "LIVE" if st.session_state.get("auto_refresh") else "MANUAL"
    st.markdown(f"""
    <div class="hq-command">
      <div class="hq-command-left">
        <div class="hq-brand-mark">HQ</div>
        <div>
          <div class="hq-command-ticker">{ticker}</div>
          <div class="hq-command-page">{page} · HaViQuant Intelligence Terminal</div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <span class="hq-chip">Market Data</span>
        <span class="hq-chip">Decision Engine</span>
        <span class="hq-status"><span class="hq-dot"></span>{refresh_state} · {now}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ==================================================================
# SIDEBAR
# ==================================================================

def render_sidebar() -> tuple[str, str]:
    """Stable premium navigation. Never trusts a stale session-state page value."""
    nav_map = {
        "📊 Dashboard": "Dashboard",
        "📈 Stock Analysis": "Stock Analysis",
        "💼 Portfolio": "Portfolio",
        "🔥 Opportunity Radar": "Opportunity Radar",
        "🧪 Backtesting": "Backtesting",
        "🔬 Evidence Research": "Evidence Research",
    }
    nav_options = list(nav_map.keys())

    current_page = st.session_state.get("page", "Dashboard")
    if current_page not in nav_map.values():
        current_page = "Dashboard"
        st.session_state.page = current_page

    # Prevent a stale widget value from crashing Streamlit after an app update.
    if st.session_state.get("hq_navigation") not in nav_options:
        st.session_state.pop("hq_navigation", None)

    with st.sidebar:
        logo = Path(__file__).resolve().parent / "assets" / "haviquant_logo.png"
        if logo.exists():
            st.image(str(logo), width=190)
        else:
            st.markdown("# 📈 HaViQuant")

        st.markdown(
            "<div class='hq-page-kicker'>Intelligent Market Analysis</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='color:#60788f;font-size:10px;line-height:1.5;'>Market · Macro · Technical · Portfolio · Opportunity Intelligence</div>",
            unsafe_allow_html=True,
        )
        st.write("")

        selected_label = st.radio(
            "Workspace",
            nav_options,
            index=next(i for i, label in enumerate(nav_options) if nav_map[label] == current_page),
            key="hq_navigation",
            label_visibility="collapsed",
        )
        page = nav_map[selected_label]

        ticker = st.text_input(
            "Ticker",
            value=st.session_state.get("ticker", DEFAULT_TICKER),
            max_chars=12,
            placeholder="NVDA",
            key="hq_ticker_input",
        ).strip().upper() or DEFAULT_TICKER

        st.session_state.ticker = ticker
        st.session_state.page = page

        st.divider()
        st.markdown("**LIVE ENGINE**")
        st.checkbox("Live refresh", key="auto_refresh")
        st.slider(
            "Refresh interval",
            min_value=2, max_value=30,
            value=5, step=1, key="refresh_seconds",
        )

        if st.button("↻ Refresh Market Data", width="stretch"):
            for fn in (load_market_data, run_existing_analysis, fetch_live_quote, fetch_news, fetch_insider_transactions, get_fundamentals):
                try:
                    fn.clear()
                except Exception:
                    pass
            st.rerun()

        st.divider()
        st.markdown("<div class='small-note'>HaViQuant · Premium Intelligence Terminal<br>Research / validation remains isolated from production decisions.</div>", unsafe_allow_html=True)

    return page, ticker


def render_portfolio_tape(rows):
    items=[]
    for r in rows:
        price=r.get("price")
        pct=r.get("pnl_pct")
        if price is None:
            items.append(f"<span class='hq-tape-item'><b>{r['ticker']}</b> N/A</span>")
        else:
            cls="hq-positive" if (r.get("change_pct") or 0)>=0 else "hq-negative"
            items.append(f"<span class='hq-tape-item'><b>{r['ticker']}</b> ${price:,.2f} <span class='{cls}'>{_fmt_pct(r.get('change_pct'))}</span></span>")
    if not items:
        return
    html="".join(items*2)
    st.markdown(f"<div class='hq-tape'><div class='hq-tape-track'>{html}</div></div>", unsafe_allow_html=True)


def render_portfolio():
    st.title("💼 HaViQuant Portfolio Intelligence")
    st.caption("Live portfolio valuation + portfolio doctor + risk diagnosis + new-money guidance. Missing quotes are never treated as zero.")
    portfolio=load_portfolio(); positions=portfolio.get("positions",[])
    rows=portfolio_rows(portfolio)
    render_portfolio_tape(rows)
    doctor=portfolio_doctor(portfolio, rows)
    cash=float(portfolio.get("cash",0) or 0)
    total=doctor["total_value"]; cost=doctor["total_cost"]; pnl=doctor["pnl"]
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Portfolio Value", money(total+cash))
    c2.metric("Invested", money(cost))
    c3.metric("Unrealized P/L", money(pnl), _fmt_pct(doctor["pnl_pct"]))
    if doctor.get("valuation_coverage",100) < 100:
        st.warning(f"Live valuation coverage: {doctor['valuation_coverage']:.1f}%. Positions without a valid quote are excluded from P/L rather than treated as a loss.")
    c4.metric("Cash", money(cash))
    c5.metric("Portfolio Health", f"{doctor['health']:.0f}/100")

    st.subheader("🩺 Portfolio Doctor")
    a,b=st.columns([1,2],gap="large")
    with a:
        st.metric("Health", f"{doctor['health']:.0f}/100")
        st.caption("Diagnostic score; not a guarantee of future returns.")
    with b:
        if doctor["issues"]:
            for issue in doctor["issues"]:
                icon="🔴" if issue["severity"]=="HIGH" else "🟠"
                st.markdown(f"**{icon} {issue['title']}** — {issue['detail']}")
        else:
            st.success("No major structural portfolio issue detected from the available data.")

    st.subheader("📊 Sector Exposure")
    sw=doctor["sector_weights"]
    if sw:
        sdf=pd.DataFrame(sorted(sw.items(),key=lambda x:x[1],reverse=True),columns=["Sector","Weight %"])
        st.dataframe(sdf.style.format({"Weight %":"{:.1f}%"}),width="stretch",hide_index=True)

    st.subheader("🎯 What Should I Correct?")
    if doctor["missing_sectors"]:
        st.info("Underrepresented sectors for new money: " + ", ".join(doctor["missing_sectors"]))
    for issue in doctor["issues"]:
        st.markdown(f"• **{issue['title']}** — {issue['detail']}")

    st.subheader("💰 Position Intelligence")
    if rows:
        display=[]
        for r in rows:
            display.append({
                "Ticker":r["ticker"],"Shares":r["shares"],"Avg Cost":r["average_cost"],
                "Live Price":r["price"],"Value":r["market_value"],"P/L":r["pnl"],"P/L %":r["pnl_pct"],
                "Data":r["quote_status"],"Source":r["quote_source"] or "—",
            })
        st.dataframe(pd.DataFrame(display),width="stretch",hide_index=True)
        for r in rows:
            if r["price"] is None:
                st.warning(f"{r['ticker']}: live price unavailable. Portfolio value/P&L is shown as N/A, not as a loss.")
    else:
        st.info("Your portfolio is empty. Add positions below.")

    st.subheader("✏️ Customize Portfolio")
    edit_rows=[{"Ticker":p.get("ticker",""),"Shares":float(p.get("shares",0)),"Average Cost":float(p.get("average_cost",0)),"Stop Loss":float(p.get("stop_loss",0)),"Take Profit":float(p.get("take_profit",0)),"Notes":p.get("notes","")} for p in positions]
    if not edit_rows: edit_rows=[{"Ticker":"NVDA","Shares":0.0,"Average Cost":0.0,"Stop Loss":0.0,"Take Profit":0.0,"Notes":""}]
    edited=st.data_editor(pd.DataFrame(edit_rows),num_rows="dynamic",width="stretch",key="portfolio_editor_v2")
    cash_new=st.number_input("Cash / uninvested balance",min_value=0.0,value=cash,step=100.0,key="portfolio_cash_v2")
    if st.button("💾 Save Portfolio",type="primary",width="stretch"):
        portfolio["cash"]=float(cash_new); portfolio["positions"]=normalize_positions(edited); save_portfolio(portfolio); st.success("Portfolio saved."); st.rerun()

    st.subheader("🔔 Mobile Alert Center")
    settings=portfolio.get("settings",{})
    enabled=st.toggle("Enable portfolio alerts",value=bool(settings.get("portfolio_alerts_enabled",False)),key="alerts_enabled_v2")
    daily_loss=st.number_input("Daily loss alert (%)",min_value=-50.0,max_value=-0.1,value=float(settings.get("daily_loss_threshold_pct",-3.0)),step=.5,key="daily_loss_v2")
    drawdown=st.number_input("Drawdown alert (%)",min_value=-90.0,max_value=-0.5,value=float(settings.get("portfolio_drawdown_threshold_pct",-5.0)),step=.5,key="drawdown_v2")
    decision_alert=st.checkbox("Decision change alerts",value=bool(settings.get("decision_change_alert",True)),key="decision_alert_v2")
    price_alerts=st.checkbox("Stop / target alerts",value=bool(settings.get("price_alerts",True)),key="price_alerts_v2")
    channel=st.selectbox("Mobile provider",["Telegram","Pushover"],index=0,key="alert_channel_v2")
    if channel=="Telegram": st.code("export HAVIQ_TELEGRAM_BOT_TOKEN='your-token'\nexport HAVIQ_TELEGRAM_CHAT_ID='your-chat-id'",language="bash")
    else: st.code("export HAVIQ_PUSHOVER_TOKEN='your-token'\nexport HAVIQ_PUSHOVER_USER='your-user'",language="bash")
    if st.button("💾 Save Alert Settings",key="save_alerts_v2"):
        portfolio["settings"].update({"portfolio_alerts_enabled":enabled,"daily_loss_threshold_pct":daily_loss,"portfolio_drawdown_threshold_pct":drawdown,"decision_change_alert":decision_alert,"price_alerts":price_alerts,"mobile_provider":channel}); save_portfolio(portfolio); st.success("Alert settings saved.")
    if st.button("📲 Send Test Mobile Alert",key="test_alert_v2"):
        ok=send_telegram("HaViQuant test alert — mobile notification is working.") if channel=="Telegram" else send_pushover("HaViQuant test alert — mobile notification is working.")
        st.success("Test alert sent.") if ok else st.error("Could not send. Check environment variables.")


def render_opportunity_radar():
    st.title("🔥 HaViQuant Opportunity Radar")
    st.caption("Market-wide discovery using technical state, historical analogs, risk/reward and macro/sector context. Research first; no profit guarantee.")
    macro=macro_snapshot(); sectors=sector_rotation(); impacts=sector_impact_map(macro,sectors)
    with st.expander("🌎 Macro & Cross-Asset Regime",expanded=True):
        cols=st.columns(min(4,max(1,len([k for k in macro if k!='regime']))))
        keys=[k for k in macro if k!="regime"]
        for i,k in enumerate(keys):
            with cols[i%len(cols)]:
                d=macro[k]; st.metric(k,f"{d['value']:.2f}",_fmt_pct(d.get('change_5d_pct')))
        st.info(f"Risk appetite: **{macro.get('regime',{}).get('risk_appetite','UNKNOWN')}** · Rates: **{macro.get('regime',{}).get('rates_trend','UNKNOWN')}**")
    if sectors:
        st.subheader("🔄 Sector Rotation")
        st.dataframe(pd.DataFrame(sectors).rename(columns={"return_5d":"5D %","return_20d":"20D %","score":"Rotation Score"}).style.format({"5D %":"{:.2f}%","20D %":"{:.2f}%","Rotation Score":"{:.0f}"}),width="stretch",hide_index=True)
    if impacts:
        st.subheader("🔁 Cross-Sector Impact & Potential Beneficiaries")
        idf=pd.DataFrame(impacts)[["sector","impact_score","direction","reasons"]].copy()
        idf["reasons"]=idf["reasons"].apply(lambda x:"; ".join(x) if x else "market confirmation needed")
        st.dataframe(idf.rename(columns={"sector":"Sector","impact_score":"Impact","direction":"Scenario","reasons":"Why"}).style.format({"Impact":"{:+.0f}"}),width="stretch",hide_index=True)
    if st.button("🔎 Scan Opportunity Universe",type="primary",width="stretch",key="scan_opps"):
        with st.spinner("Scanning technical setups and historical analogs..."):
            results=scan_opportunities(limit=12)
        st.session_state["hq_opportunities"]=results
    results=st.session_state.get("hq_opportunities",[])
    if results:
        st.subheader("🏆 Ranked Opportunities")
        df=pd.DataFrame([{k:r.get(k) for k in ["ticker","sector","signal","score","technical_score","historical_win_rate","prob_up_3","risk_reward","price"]} for r in results])
        st.dataframe(df.rename(columns={"ticker":"Ticker","sector":"Sector","signal":"Signal","score":"Opportunity","technical_score":"Technical","historical_win_rate":"Historical Win %","prob_up_3":"P(+3%)","risk_reward":"R/R","price":"Price"}),width="stretch",hide_index=True)
        ticker=st.selectbox("Open opportunity",[r["ticker"] for r in results],key="opp_selected")
        chosen=next(r for r in results if r["ticker"]==ticker)
        st.subheader(f"🎯 {ticker} Trade Plan")
        p=chosen.get("trade_plan",{})
        a,b,c,d,e=st.columns(5)
        a.metric("Entry",f"${p.get('entry_low',0):,.2f}–${p.get('entry_high',0):,.2f}")
        b.metric("Stop",f"${p.get('stop',0):,.2f}" if p.get('stop') else "N/A")
        c.metric("Target 1",f"${p.get('target1',0):,.2f}" if p.get('target1') else "N/A")
        d.metric("Target 2",f"${p.get('target2',0):,.2f}" if p.get('target2') else "N/A")
        e.metric("Risk/Reward",f"{p.get('risk_reward',0):.2f}:1" if p.get('risk_reward') else "N/A")
        st.warning("A BUY/STRONG BUY label is not a promise of profit. The plan defines entry, invalidation and targets so the thesis can be monitored.")


def render_dashboard_home(ticker: str):
    st.markdown("<div class='hq-page-kicker'>Market Command Center</div>", unsafe_allow_html=True)
    st.markdown("<div class='hq-page-title'>Turn Market Data Into Decisions</div>", unsafe_allow_html=True)
    st.markdown("<div class='hq-page-subtitle'>Live price action, production decision, technical context and evidence-backed move intelligence — optimized for a fast daily workflow.</div>", unsafe_allow_html=True)

    try:
        result = run_existing_analysis(ticker)
        df = normalize_market_dataframe(result["data"])
        if df is None or df.empty:
            st.error("Dashboard market data could not be loaded.")
            return
        st.session_state._hq_df = df
        signals = build_signal_map(df, result["technical"], result["decision"])

        render_live_header(ticker, df)
        st.markdown(f"""<div class="hq-card" style="padding:10px 12px;margin-bottom:12px;">
          <span class="hq-chip">Trend · {signals.get('setup','N/A')}</span>
          <span class="hq-chip">RSI · {_fmt_number(signals.get('rsi'),1)}</span>
          <span class="hq-chip">Rel Volume · {_fmt_number(signals.get('relative_volume'),2)}x</span>
          <span class="hq-chip">Support · {money(signals.get('support')) if signals.get('support') else 'N/A'}</span>
          <span class="hq-chip">Resistance · {money(signals.get('resistance')) if signals.get('resistance') else 'N/A'}</span>
        </div>""", unsafe_allow_html=True)
        render_chart(ticker, df, signals)

        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Production Signal", safe_text(first_value(result["decision"],["signal"],"UNKNOWN")))
        c2.metric("Technical", f"{signals['technical_score']:.0f}/100" if signals['technical_score'] is not None else "N/A")
        c3.metric("RSI", f"{signals['rsi']:.1f}" if signals['rsi'] is not None else "N/A")
        c4.metric("Support", f"${signals['support']:,.2f}" if signals['support'] else "N/A")
        c5.metric("Resistance", f"${signals['resistance']:,.2f}" if signals['resistance'] else "N/A")

        left, right = st.columns([1.15, .85], gap="large")
        with left:
            render_price_move_explanation(ticker, df)
        with right:
            st.markdown("<div class='hq-card'><div class='hq-title'>Quick Decision</div>", unsafe_allow_html=True)
            render_production_decision(result["decision"])
            st.markdown("</div>", unsafe_allow_html=True)

    except Exception as error:
        st.error("Dashboard market data could not be loaded.")
        st.exception(error)


# ==================================================================
# STOCK INTELLIGENCE HELPERS
# ==================================================================

@st.cache_data(ttl=300, show_spinner=False)
def get_stock_event_snapshot(ticker: str) -> dict[str, Any]:
    """Best-effort event/fundamental snapshot. Missing provider fields stay N/A."""
    if yf is None:
        return {}
    try:
        t = yf.Ticker(ticker)
        info = t.info if isinstance(t.info, dict) else {}
        calendar = {}
        try:
            raw = t.calendar
            if hasattr(raw, "to_dict"):
                calendar = raw.to_dict()
            elif isinstance(raw, dict):
                calendar = raw
        except Exception:
            calendar = {}

        earnings = None
        for key in ("Earnings Date", "earningsDate"):
            value = calendar.get(key) if isinstance(calendar, dict) else None
            if isinstance(value, (list, tuple)) and value:
                value = value[0]
            if value is not None:
                earnings = str(value)
                break

        return {
            "company": info.get("longName") or info.get("shortName") or ticker,
            "sector": info.get("sector") or "N/A",
            "industry": info.get("industry") or "N/A",
            "market_cap": info.get("marketCap"),
            "beta": info.get("beta"),
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "profit_margin": info.get("profitMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "dividend_yield": info.get("dividendYield"),
            "target_mean": info.get("targetMeanPrice"),
            "target_high": info.get("targetHighPrice"),
            "target_low": info.get("targetLowPrice"),
            "recommendation": info.get("recommendationKey") or info.get("recommendationMean"),
            "short_ratio": info.get("shortRatio"),
            "short_percent": info.get("shortPercentOfFloat"),
            "fifty_two_high": info.get("fiftyTwoWeekHigh"),
            "fifty_two_low": info.get("fiftyTwoWeekLow"),
            "earnings_date": earnings,
        }
    except Exception:
        return {}


def stock_relative_performance(df: pd.DataFrame, ticker: str) -> dict[str, Any]:
    out = {"1D": None, "5D": None, "1M": None, "3M": None, "SPY_5D": None, "SPY_1M": None}
    if df is None or df.empty or "Close" not in df.columns:
        return out
    close = pd.to_numeric(df["Close"], errors="coerce").dropna()
    if close.empty:
        return out
    for label, periods in (("1D",1),("5D",5),("1M",21),("3M",63)):
        if len(close) > periods:
            out[label] = (float(close.iloc[-1]) / float(close.iloc[-1-periods]) - 1) * 100
    if yf is not None:
        try:
            spy = yf.download("SPY", period="3mo", interval="1d", progress=False, auto_adjust=False, threads=False)
            if isinstance(spy, pd.DataFrame) and not spy.empty:
                if isinstance(spy.columns, pd.MultiIndex):
                    spy_close = spy["Close"].iloc[:,0]
                else:
                    spy_close = spy["Close"]
                spy_close = pd.to_numeric(spy_close, errors="coerce").dropna()
                for label, periods in (("SPY_5D",5),("SPY_1M",21)):
                    if len(spy_close) > periods:
                        out[label] = (float(spy_close.iloc[-1]) / float(spy_close.iloc[-1-periods]) - 1) * 100
        except Exception:
            pass
    return out


def render_analysis_cockpit(ticker: str, df: pd.DataFrame, result: dict[str, Any], signals: dict[str, Any]):
    info = get_stock_event_snapshot(ticker)
    perf = stock_relative_performance(df, ticker)
    signal = safe_text(first_value(result.get("decision"), ["signal"], "UNKNOWN"))
    score = opt_float(first_value(result.get("decision"), ["score", "technical_score"]))
    current = signals.get("current")
    fair = fair_value_model(ticker)
    fair_base = opt_float(fair.get("base"))

    st.markdown("<div class='hq-section'>Decision Cockpit</div>", unsafe_allow_html=True)
    cards = st.columns(6)
    cards[0].metric("Decision", signal)
    cards[1].metric("Score", f"{score:.0f}/100" if score is not None else "N/A")
    cards[2].metric("1D", _fmt_pct(perf["1D"]))
    cards[3].metric("5D", _fmt_pct(perf["5D"]))
    cards[4].metric("Vs SPY 5D", _fmt_pct((perf["5D"] - perf["SPY_5D"]) if perf["5D"] is not None and perf["SPY_5D"] is not None else None))
    cards[5].metric("Fair Value", f"${fair_base:,.2f}" if fair_base else "N/A")

    st.markdown("<div class='hq-section'>What Matters Right Now</div>", unsafe_allow_html=True)
    left, mid, right = st.columns([1.1, 1.1, 1.0], gap="large")
    with left:
        st.markdown("<div class='hq-card'><div class='hq-title'>🎯 Trade Setup</div>", unsafe_allow_html=True)
        rows = [
            ("Entry zone", f"${signals['buy_zone_low']:,.2f} – ${signals['buy_zone_high']:,.2f}" if signals.get("buy_zone_low") else "N/A"),
            ("Target 1", f"${signals['target1']:,.2f}" if signals.get("target1") else "N/A"),
            ("Target 2", f"${signals['target2']:,.2f}" if signals.get("target2") else "N/A"),
            ("Invalidation", f"${signals['invalidation']:,.2f}" if signals.get("invalidation") else "N/A"),
            ("Support", f"${signals['support']:,.2f}" if signals.get("support") else "N/A"),
            ("Resistance", f"${signals['resistance']:,.2f}" if signals.get("resistance") else "N/A"),
        ]
        for k,v in rows: st.markdown(f"**{k}** · {v}")
        st.markdown("</div>", unsafe_allow_html=True)
    with mid:
        st.markdown("<div class='hq-card'><div class='hq-title'>🧭 Market Position</div>", unsafe_allow_html=True)
        vals = [
            ("Trend", signals.get("setup", "N/A")),
            ("RSI 14", _fmt_number(signals.get("rsi"),1)),
            ("Relative volume", f"{_fmt_number(signals.get('relative_volume'),2)}x"),
            ("Sector", info.get("sector", "N/A")),
            ("Industry", info.get("industry", "N/A")),
            ("Beta", _fmt_number(info.get("beta"),2)),
        ]
        for k,v in vals: st.markdown(f"**{k}** · {v}")
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown("<div class='hq-card'><div class='hq-title'>📅 Upcoming / Key Data</div>", unsafe_allow_html=True)
        vals = [
            ("Earnings", info.get("earnings_date") or "Not returned"),
            ("Analyst reference", f"${info['target_mean']:,.2f}" if info.get("target_mean") else "N/A"),
            ("52W range", f"${info['fifty_two_low']:,.2f} – ${info['fifty_two_high']:,.2f}" if info.get("fifty_two_low") and info.get("fifty_two_high") else "N/A"),
            ("Recommendation", str(info.get("recommendation") or "N/A").upper()),
            ("Dividend yield", f"{float(info['dividend_yield'])*100:.2f}%" if info.get("dividend_yield") is not None else "N/A"),
        ]
        for k,v in vals: st.markdown(f"**{k}** · {v}")
        st.markdown("</div>", unsafe_allow_html=True)


def render_risk_scenarios(df: pd.DataFrame, signals: dict[str, Any], info: dict[str, Any]):
    st.markdown("<div class='hq-section'>Risk & Scenario Map</div>", unsafe_allow_html=True)
    current = opt_float(signals.get("current")); atr = opt_float(signals.get("atr"))
    beta = opt_float(info.get("beta"))
    rows = []
    if current:
        rows.append({"Scenario":"Normal pullback","Move":"-1 ATR","Estimated price": current-atr if atr else None,"Interpretation":"Watch support / thesis"})
        rows.append({"Scenario":"Moderate selloff","Move":"-5%","Estimated price": current*.95,"Interpretation":"Reassess momentum"})
        rows.append({"Scenario":"Moderate upside","Move":"+5%","Estimated price": current*1.05,"Interpretation":"Check resistance / profit"})
        rows.append({"Scenario":"Strong upside","Move":"+10%","Estimated price": current*1.10,"Interpretation":"Check extension / targets"})
    if beta is not None:
        st.caption(f"Beta: {beta:.2f}. Scenario prices are sensitivity illustrations, not forecasts.")
    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


@st.cache_data(ttl=900, show_spinner=False)
def load_company_intelligence(ticker: str, quarters: int, competitors_csv: str) -> dict[str, Any]:
    competitors = [x.strip().upper() for x in competitors_csv.split(",") if x.strip()]
    return build_company_intelligence(ticker, quarters=quarters, competitors=competitors)




def _havi_safe_status(item: Any, default: str = "UNKNOWN") -> str:
    """Safely normalize Company Intelligence status values."""
    if isinstance(item, dict):
        value = item.get(
            "status",
            item.get(
                "classification",
                item.get(
                    "verdict",
                    item.get("validation", default),
                ),
            ),
        )
        return str(value).strip().upper() if value is not None else default
    if isinstance(item, str):
        return item.strip().upper()
    return default


def render_company_intelligence(ticker: str):
    """
    360° Company Intelligence UI.

    Defensive UI layer:
    - Accepts dictionary/string records from the intelligence engine.
    - Never assumes every governance/risk item is a dictionary.
    - Missing data remains visible as N/A rather than crashing the dashboard.
    - Does not modify production BUY/SELL decisions.
    """

    st.markdown(
        "<div class='hq-page-kicker'>360° Company Intelligence · Evidence First</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"<div class='hq-page-title'>{ticker.upper()} "
        "<span style='color:#4b6b86;'>/ Company Intelligence</span></div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='hq-page-subtitle'>"
        "Company history, business model, products, demand, financial history, "
        "earnings, backlog, competition, governance, scenarios and stock-level "
        "context. Missing data stays missing."
        "</div>",
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([1, 2])

    with c1:
        quarters = st.selectbox(
            "Historical quarters",
            [4, 6, 8, 10, 12, 20],
            index=3,
            key="company_quarters",
        )

    with c2:
        competitors_csv = st.text_input(
            "Competitors (optional, comma-separated)",
            value="",
            placeholder="AMD, AVGO, MSFT",
            key="company_competitors",
        )

    # ------------------------------------------------------------
    # LOAD COMPANY INTELLIGENCE
    # ------------------------------------------------------------

    try:
        data = load_company_intelligence(
            ticker,
            int(quarters),
            competitors_csv,
        )

    except Exception as exc:
        st.error(
            f"Company Intelligence could not load for {ticker}."
        )
        st.exception(exc)
        return

    if not isinstance(data, dict):
        st.error(
            "Company Intelligence returned an unexpected data format."
        )
        st.write(
            {
                "received_type": type(data).__name__,
                "received_value": str(data)[:500],
            }
        )
        return

    if not data.get("available"):
        st.error(
            data.get(
                "error",
                "Company data unavailable.",
            )
        )
        return

    # ------------------------------------------------------------
    # SAFE TOP-LEVEL DATA EXTRACTION
    # ------------------------------------------------------------

    profile = data.get("profile") or {}
    scores = data.get("scores") or {}
    val = data.get("valuation") or {}
    stock = data.get("stock_level") or {}

    if not isinstance(profile, dict):
        profile = {}

    if not isinstance(scores, dict):
        scores = {}

    if not isinstance(val, dict):
        val = {}

    if not isinstance(stock, dict):
        stock = {}

    sources = data.get("sources") or {}

    if not isinstance(sources, dict):
        sources = {}

    profile_name = profile.get(
        "name",
        ticker.upper(),
    )

    profile_sector = profile.get(
        "sector",
        "Unknown",
    )

    profile_industry = profile.get(
        "industry",
        "Unknown",
    )

    profile_country = profile.get(
        "country",
        "Unknown",
    )

    st.markdown(
        f"**{profile_name}** · "
        f"{profile_sector} · "
        f"{profile_industry} · "
        f"{profile_country}"
    )

    st.caption(
        f"Data snapshot: "
        f"{data.get('as_of', 'N/A')} · "
        f"{sources.get('market_data', 'Provider data')}"
    )

    # ------------------------------------------------------------
    # SCORE CARDS
    # ------------------------------------------------------------

    cards = st.columns(6)

    business_quality = scores.get(
        "business_quality"
    )

    financial_strength = scores.get(
        "financial_strength"
    )

    demand_proxy = scores.get(
        "demand_proxy"
    )

    current_price = val.get(
        "current_price"
    )

    reference_upside = val.get(
        "reference_upside_pct"
    )

    beta = stock.get(
        "beta"
    )

    cards[0].metric(
        "Business Quality",
        (
            f"{business_quality}/100"
            if business_quality is not None
            else "N/A"
        ),
    )

    cards[1].metric(
        "Financial Strength",
        (
            f"{financial_strength}/100"
            if financial_strength is not None
            else "N/A"
        ),
    )

    cards[2].metric(
        "Demand Proxy",
        (
            f"{demand_proxy}/100"
            if demand_proxy is not None
            else "N/A"
        ),
    )

    cards[3].metric(
        "Current Price",
        (
            f"${current_price:,.2f}"
            if isinstance(
                current_price,
                (int, float),
            )
            else "N/A"
        ),
    )

    cards[4].metric(
        "Reference Upside",
        _fmt_pct(reference_upside),
    )

    cards[5].metric(
        "Beta",
        _fmt_number(beta, 2),
    )

    # ------------------------------------------------------------
    # TABS
    # ------------------------------------------------------------

    tabs = st.tabs(
        [
            "🏢 Business",
            "📊 Quarters",
            "🔥 Demand Timeline",
            "📦 Orders & Backlog",
            "🆚 Competition",
            "⚖️ Ethics & Risk",
            "📅 Earnings",
            "💎 Valuation",
            "🧩 Stock Level",
            "🧪 Evidence",
        ]
    )

    # ============================================================
    # TAB 0 — BUSINESS
    # ============================================================

    with tabs[0]:

        st.subheader("Business Overview")

        business = data.get(
            "business",
            {},
        )

        if not isinstance(
            business,
            dict,
        ):
            business = {}

        description = business.get(
            "description"
        )

        if description:
            st.write(description)
        else:
            st.info(
                "No detailed business description was returned."
            )

        products = business.get(
            "products",
            [],
        )

        if products:

            st.markdown(
                "### Products & Business Lines"
            )

            if isinstance(
                products,
                list,
            ):

                for product in products:

                    if isinstance(
                        product,
                        dict,
                    ):

                        name = product.get(
                            "name",
                            "Product",
                        )

                        detail = product.get(
                            "description",
                            product.get(
                                "detail",
                                "",
                            ),
                        )

                        st.markdown(
                            f"**{name}**"
                        )

                        if detail:
                            st.caption(
                                str(detail)
                            )

                    else:

                        st.markdown(
                            f"**{str(product)}**"
                        )

        business_model = business.get(
            "business_model"
        )

        if business_model:
            st.markdown(
                "### Business Model"
            )
            st.write(
                business_model
            )

    # ============================================================
    # TAB 1 — QUARTERS
    # ============================================================

    with tabs[1]:

        st.subheader(
            f"Last {data.get('quarter_count', quarters)} Reported Quarters"
        )

        qrows = data.get(
            "quarters",
            [],
        )

        if isinstance(
            qrows,
            list,
        ) and qrows:

            qdf = pd.DataFrame(
                qrows
            )

            for col in [
                "revenue",
                "gross_profit",
                "operating_income",
                "net_income",
                "free_cash_flow",
            ]:

                if col in qdf.columns:

                    qdf[col] = qdf[
                        col
                    ].map(
                        _fmt_money
                    )

            for col in [
                "revenue_yoy_pct",
                "revenue_qoq_pct",
                "gross_margin_pct",
                "operating_margin_pct",
            ]:

                if col in qdf.columns:

                    qdf[col] = qdf[
                        col
                    ].map(
                        lambda x: _fmt_pct(x)
                    )

            qdf = qdf.rename(
                columns={
                    "quarter": "Quarter",
                    "revenue": "Revenue",
                    "revenue_yoy_pct": "Revenue YoY",
                    "revenue_qoq_pct": "Revenue QoQ",
                    "gross_profit": "Gross Profit",
                    "gross_margin_pct": "Gross Margin",
                    "operating_income": "Operating Income",
                    "operating_margin_pct": "Operating Margin",
                    "net_income": "Net Income",
                    "eps": "EPS",
                    "free_cash_flow": "Free Cash Flow",
                }
            )

            st.dataframe(
                qdf,
                width="stretch",
                hide_index=True,
            )

            st.caption(
                "Quarterly data comes from the market-data provider. "
                "Some companies expose fewer quarters or different accounting fields."
            )

        else:

            st.warning(
                "No quarterly financial data was returned."
            )

    # ============================================================
    # TAB 2 — DEMAND
    # ============================================================

    with tabs[2]:

        st.subheader(
            "Current + Future Demand"
        )

        products_demand = data.get(
            "products_demand",
            {},
        )

        if not isinstance(
            products_demand,
            dict,
        ):
            products_demand = {}

        st.metric(
            "Current demand proxy",
            products_demand.get(
                "current_demand_proxy",
                "N/A",
            ),
        )

        future_demand = products_demand.get(
            "future_demand",
            [],
        )

        if not isinstance(
            future_demand,
            list,
        ):
            future_demand = []

        for d in future_demand:

            if not isinstance(
                d,
                dict,
            ):
                st.markdown(
                    f"• {str(d)}"
                )
                continue

            status = str(
                d.get(
                    "status",
                    "UNKNOWN",
                )
            ).upper()

            icon = (
                "🟢"
                if status == "POSITIVE"
                else "🔴"
                if status == "NEGATIVE"
                else "🟡"
            )

            driver = d.get(
                "driver",
                "Demand Driver",
            )

            confidence = d.get(
                "confidence",
                "UNKNOWN",
            )

            value = d.get(
                "value",
                "N/A",
            )

            timeline = d.get(
                "timeline",
                "N/A",
            )

            st.markdown(
                f"**{icon} {driver}** · "
                f"{status} · "
                f"{confidence} confidence"
            )

            st.caption(
                f"{value} · Timeline: {timeline}"
            )

        st.warning(
            "Future-demand statements are proxies unless supported by "
            "company guidance, customer orders, industry data or other cited evidence. "
            "HaViQuant does not convert them into guaranteed forecasts."
        )

    # ============================================================
    # TAB 3 — BACKLOG
    # ============================================================

    with tabs[3]:

        st.subheader(
            "Orders, Backlog & Revenue Visibility"
        )

        backlog = data.get(
            "backlog",
            {},
        )

        if not isinstance(
            backlog,
            dict,
        ):
            backlog = {}

        backlog_status = str(
            backlog.get(
                "status",
                "UNAVAILABLE",
            )
        )

        st.metric(
            "Backlog",
            (
                backlog.get(
                    "value"
                )
                if backlog.get(
                    "value"
                ) is not None
                else "N/A"
            ),
        )

        st.warning(
            f"{backlog_status}."
        )

        st.write(
            backlog.get(
                "note",
                "No backlog information was returned.",
            )
        )

        st.markdown(
            "**Required evidence for a company-specific backlog model:** "
            "orders/bookings, backlog or RPO definition, cancellation terms, "
            "expected conversion, book-to-bill where applicable, and customer concentration."
        )

    # ============================================================
    # TAB 4 — COMPETITION
    # ============================================================

    with tabs[4]:

        st.subheader(
            "Competitor Comparison"
        )

        rows = data.get(
            "competition",
            [],
        )

        if isinstance(
            rows,
            list,
        ) and rows:

            safe_rows = [
                r
                for r in rows
                if isinstance(
                    r,
                    dict,
                )
            ]

            if safe_rows:

                cdf = pd.DataFrame(
                    safe_rows
                )

                for col in [
                    "Market Cap"
                ]:

                    if col in cdf.columns:
                        cdf[col] = cdf[
                            col
                        ].map(
                            _fmt_money
                        )

                for col in [
                    "Revenue Growth",
                    "Gross Margin",
                ]:

                    if col in cdf.columns:
                        cdf[col] = cdf[
                            col
                        ].map(
                            lambda x: _fmt_pct(x)
                        )

                st.dataframe(
                    cdf,
                    width="stretch",
                    hide_index=True,
                )

                st.caption(
                    "Competitors are user-supplied in this version. "
                    "Backlog is not compared unless the underlying source definitions "
                    "are available and normalized."
                )

            else:

                st.info(
                    "Competitor data was returned in an unsupported format."
                )

        else:

            st.info(
                "Enter competitor tickers above to build a comparable market-data table."
            )

    # ============================================================
    # TAB 5 — ETHICS / GOVERNANCE / RISK
    # ============================================================

    with tabs[5]:

        st.subheader(
            "Ethics, Governance & Risk Review"
        )

        st.caption(
            "A review queue is safer than inventing allegations. "
            "Items below require evidence verification."
        )

        governance_items = data.get(
            "governance_ethics",
            [],
        )

        if not isinstance(
            governance_items,
            list,
        ):
            governance_items = []

        for item in governance_items:

            # ----------------------------------------------------
            # THIS IS THE FIX
            # ----------------------------------------------------

            if isinstance(
                item,
                dict,
            ):

                topic = str(
                    item.get(
                        "topic",
                        item.get(
                            "label",
                            item.get(
                                "title",
                                "Governance / Ethics Item",
                            ),
                        ),
                    )
                )

                status = str(
                    item.get(
                        "status",
                        item.get(
                            "classification",
                            item.get(
                                "verdict",
                                item.get(
                                    "validation",
                                    "UNKNOWN",
                                ),
                            ),
                        ),
                    )
                )

                evidence = str(
                    item.get(
                        "evidence",
                        item.get(
                            "detail",
                            item.get(
                                "note",
                                "",
                            ),
                        ),
                    )
                )

            elif isinstance(
                item,
                str,
            ):

                topic = item
                status = "AVAILABLE"
                evidence = ""

            else:

                topic = "Governance / Ethics Item"
                status = "UNKNOWN"
                evidence = str(item)

            status_upper = status.strip().upper()

            icon = (
                "🟢"
                if status_upper
                in {
                    "AVAILABLE",
                    "POSITIVE",
                    "PASS",
                    "CLEAR",
                    "OK",
                }
                else "🟡"
            )

            st.markdown(
                f"**{icon} {topic}** · {status}"
            )

            if evidence:
                st.caption(
                    evidence
                )

        st.markdown(
            "### Current risk flags"
        )

        risks = data.get(
            "risks",
            [],
        )

        if not isinstance(
            risks,
            list,
        ):
            risks = []

        for r in risks:

            if not isinstance(
                r,
                dict,
            ):

                st.markdown(
                    f"🟡 **Risk item** — {str(r)}"
                )
                continue

            level = str(
                r.get(
                    "level",
                    "LOW",
                )
            ).upper()

            icon = (
                "🔴"
                if level == "HIGH"
                else "🟠"
                if level == "MEDIUM"
                else "🟢"
            )

            title = r.get(
                "title",
                "Risk",
            )

            detail = r.get(
                "detail",
                "",
            )

            st.markdown(
                f"**{icon} {title}** — {detail}"
            )

        if not risks:

            st.info(
                "No automated risk flag was triggered from the available provider data. "
                "This is not proof that no risk exists."
            )

    # ============================================================
    # TAB 6 — EARNINGS
    # ============================================================

    with tabs[6]:

        st.subheader(
            "Earnings & Catalyst Timing"
        )

        earnings = data.get(
            "earnings",
            {},
        )

        if not isinstance(
            earnings,
            dict,
        ):
            earnings = {}

        e1, e2 = st.columns(2)

        with e1:
            st.metric(
                "Next earnings",
                str(
                    earnings.get(
                        "next_earnings",
                        "N/A",
                    )
                ),
            )

        with e2:
            st.metric(
                "Last fiscal year end",
                str(
                    earnings.get(
                        "last_earnings",
                        "N/A",
                    )
                ),
            )

        st.caption(
            "Earnings dates are provider data and can change. "
            "Verify against the company's investor-relations calendar "
            "before trading around the event."
        )

    # ============================================================
    # TAB 7 — VALUATION
    # ============================================================

    with tabs[7]:

        st.subheader(
            "Valuation Reference"
        )

        v1, v2, v3, v4 = st.columns(4)

        v1.metric(
            "Forward P/E",
            _fmt_number(
                val.get(
                    "forward_pe"
                ),
                2,
            ),
        )

        v2.metric(
            "Trailing P/E",
            _fmt_number(
                val.get(
                    "trailing_pe"
                ),
                2,
            ),
        )

        v3.metric(
            "P/S",
            _fmt_number(
                val.get(
                    "price_to_sales"
                ),
                2,
            ),
        )

        v4.metric(
            "P/B",
            _fmt_number(
                val.get(
                    "price_to_book"
                ),
                2,
            ),
        )

        valuation_note = val.get(
            "note",
            "Valuation reference data is provider-dependent.",
        )

        st.info(
            valuation_note
        )

        target_mean = val.get(
            "target_mean"
        )

        if target_mean is not None:

            try:

                st.metric(
                    "Analyst reference target",
                    f"${float(target_mean):,.2f}",
                )

            except (
                TypeError,
                ValueError,
            ):

                st.metric(
                    "Analyst reference target",
                    str(target_mean),
                )

    # ============================================================
    # TAB 8 — STOCK LEVEL
    # ============================================================

    with tabs[8]:

        st.subheader(
            "Stock-Level Context"
        )

        a, b, c, d = st.columns(4)

        low_52 = stock.get(
            "fifty_two_week_low"
        )

        high_52 = stock.get(
            "fifty_two_week_high"
        )

        average_volume = stock.get(
            "average_volume"
        )

        shares_outstanding = stock.get(
            "shares_outstanding"
        )

        a.metric(
            "52W Low",
            (
                f"${float(low_52):,.2f}"
                if low_52 is not None
                else "N/A"
            ),
        )

        b.metric(
            "52W High",
            (
                f"${float(high_52):,.2f}"
                if high_52 is not None
                else "N/A"
            ),
        )

        c.metric(
            "Avg Volume",
            (
                f"{float(average_volume):,.0f}"
                if average_volume is not None
                else "N/A"
            ),
        )

        d.metric(
            "Shares",
            (
                f"{float(shares_outstanding):,.0f}"
                if shares_outstanding is not None
                else "N/A"
            ),
        )

        st.info(
            "Technical BUY/SELL decisions remain in the existing Decision Engine. "
            "Company Intelligence does not override the production signal."
        )

    # ============================================================
    # TAB 9 — EVIDENCE
    # ============================================================

    with tabs[9]:

        st.subheader(
            "Evidence & Completeness"
        )

        earnings_data = data.get(
            "earnings",
            {},
        )

        if not isinstance(
            earnings_data,
            dict,
        ):
            earnings_data = {}

        products_demand_data = data.get(
            "products_demand",
            {},
        )

        if not isinstance(
            products_demand_data,
            dict,
        ):
            products_demand_data = {}

        backlog_data = data.get(
            "backlog",
            {},
        )

        if not isinstance(
            backlog_data,
            dict,
        ):
            backlog_data = {}

        governance_data = data.get(
            "governance_ethics",
            [],
        )

        competition_data = data.get(
            "competition",
            [],
        )

        checklist = [
            (
                "Company identity",
                bool(
                    profile.get(
                        "name"
                    )
                ),
            ),
            (
                "Quarterly financials",
                bool(
                    data.get(
                        "quarters"
                    )
                ),
            ),
            (
                "Earnings timing",
                bool(
                    earnings_data.get(
                        "next_earnings"
                    )
                ),
            ),
            (
                "Demand proxy",
                bool(
                    products_demand_data.get(
                        "future_demand"
                    )
                ),
            ),
            (
                "Backlog source",
                str(
                    backlog_data.get(
                        "status",
                        "",
                    )
                ).upper()
                == "AVAILABLE",
            ),
            (
                "Governance review",
                bool(
                    governance_data
                ),
            ),
            (
                "Competitor comparison",
                bool(
                    competition_data
                ),
            ),
        ]

        for label, ok in checklist:

            st.markdown(
                f"{'🟢' if ok else '🟡'} **{label}**"
            )

        st.caption(
            "A green item means the module returned data, not that the underlying "
            "investment conclusion is correct. Missing information is explicitly "
            "surfaced rather than guessed."
        )

def render_stock_analysis_page(ticker: str):
    """Deep single-ticker workspace without duplicating the Dashboard chart."""
    st.markdown("<div class='hq-page-kicker'>Deep Intelligence · No Duplicate Chart</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='hq-page-title'>{ticker.upper()} <span style='color:#4b6b86;'>/ Decision Terminal</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='hq-page-subtitle'>A decision terminal, not another chart. This workspace prioritizes what changed, what matters next, valuation, catalysts, portfolio fit, risk and trade management.</div>", unsafe_allow_html=True)

    try:
        result = run_existing_analysis(ticker)
        df = normalize_market_dataframe(result["data"])
        if df is None or df.empty:
            st.error(f"No usable market data returned for {ticker}.")
            return
        st.session_state._hq_df = df
        signals = build_signal_map(df, result["technical"], result["decision"])
        info = get_stock_event_snapshot(ticker)

        render_live_header(ticker, df)
        render_analysis_cockpit(ticker, df, result, signals)

        tabs = st.tabs([
            "🧠 Decision", "📐 Technical", "🔎 Why It Moved", "📰 News",
            "👔 Insiders", "💰 Fair Value", "📅 Events", "⚠️ Risk", "🏢 Company Intelligence", "🧪 Evidence"
        ])
        with tabs[0]:
            render_production_decision(result["decision"])
        with tabs[1]:
            render_technical_context(result["technical"], df)
        with tabs[2]:
            render_price_move_explanation(ticker, df)
        with tabs[3]:
            render_news(ticker)
        with tabs[4]:
            render_insiders(ticker)
        with tabs[5]:
            render_fair_value(ticker)
        with tabs[6]:
            st.subheader("📅 Company Events & Key Metrics")
            a,b,c,d = st.columns(4)
            a.metric("Earnings", info.get("earnings_date") or "N/A")
            b.metric("Forward P/E", _fmt_number(info.get("forward_pe")))
            c.metric("Revenue Growth", f"{float(info['revenue_growth'])*100:.1f}%" if info.get("revenue_growth") is not None else "N/A")
            d.metric("Dividend Yield", f"{float(info['dividend_yield'])*100:.2f}%" if info.get("dividend_yield") is not None else "N/A")
            st.caption("Event fields depend on the live market-data provider and may be unavailable for some symbols.")
        with tabs[7]:
            render_risk_scenarios(df, signals, info)
            st.warning("Risk scenarios are sensitivity tools, not guaranteed outcomes. A production BUY/SELL decision remains separate from this research layer.")
        with tabs[8]:
            render_company_intelligence(ticker)
        with tabs[9]:
            st.info("Evidence/validation remains separate from the production BUY/SELL engine.")
            st.code("python app/main.py", language="bash")
            st.caption("Run the full Phase 3.8 → 3.9 → 3.9.1 research pipeline from Terminal for the complete validation report.")
    except Exception as error:
        st.error(f"Stock analysis failed for {ticker}.")
        st.exception(error)



def _safe_num(value):
    try:
        x = float(value)
        return x if np.isfinite(x) else None
    except Exception:
        return None


def render_backtest_summary(results: dict[str, Any], ticker: str):
    """Turn the BacktestEngine's nested result dictionary into a customer-readable report."""
    st.markdown(f"### {ticker.upper()} · Historical Validation Report")
    st.caption("Research/validation only. Historical results do not guarantee future performance.")

    obs = results.get("observations") or results.get("valid_signal_rows") or 0
    failures = results.get("analysis_failures", 0)
    benchmark = results.get("benchmark") or {}
    outcomes = results.get("outcome_statistics") or {}
    signal_perf = results.get("signal_performance") or {}
    score_perf = results.get("score_performance") or {}
    relative = results.get("benchmark_relative") or {}

    # Find the primary 5D outcome if available; otherwise use the first horizon.
    horizon_keys = [k for k in outcomes.keys() if str(k).endswith("D")]
    preferred = "5D" if "5D" in outcomes else (horizon_keys[0] if horizon_keys else None)
    primary = outcomes.get(preferred, {}) if preferred else {}

    win_rate = _safe_num(primary.get("win_rate"))
    avg_return = _safe_num(primary.get("average_return"))

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Historical Signals", f"{int(obs):,}")
    c2.metric("Valid Outcomes", f"{int(primary.get('valid_outcomes', 0)):,}")
    c3.metric("Win Rate", f"{win_rate:.1f}%" if win_rate is not None else "N/A")
    c4.metric("Average Return", f"{avg_return:+.2f}%" if avg_return is not None else "N/A")

    if failures:
        st.warning(f"{int(failures):,} historical rows could not be analyzed. They are excluded rather than treated as losses.")
    else:
        st.success("All eligible historical rows were analyzed successfully.")

    st.markdown("#### 📊 Outcome by Holding Period")
    rows=[]
    for key in horizon_keys:
        d=outcomes.get(key) or {}
        rows.append({
            "Horizon": key,
            "Valid": int(d.get("valid_outcomes",0) or 0),
            "Wins": int(d.get("wins",0) or 0),
            "Losses": int(d.get("losses",0) or 0),
            "Win Rate": f"{_safe_num(d.get('win_rate')):.1f}%" if _safe_num(d.get('win_rate')) is not None else "N/A",
            "Avg Return": f"{_safe_num(d.get('average_return')):+.2f}%" if _safe_num(d.get('average_return')) is not None else "N/A",
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    st.markdown("#### ⚖️ Signal vs. Passive Benchmark")
    # Backtest engine returns nested benchmark/signal dictionaries. Flatten common horizons.
    compare_rows=[]
    for key in horizon_keys:
        sp = signal_perf.get(key) or {}
        br = benchmark.get(key) or {}
        rr = relative.get(key) or {}
        def first_num(d, keys):
            for k in keys:
                v=_safe_num(d.get(k)) if isinstance(d,dict) else None
                if v is not None: return v
            return None
        sr=first_num(sp,["average_return","signal_return","return"])
        bret=first_num(br,["average_return","benchmark_return","return"])
        ex=first_num(rr,["excess_return","excess"])
        compare_rows.append({"Horizon":key,
                             "Signal Avg Return":f"{sr:+.2f}%" if sr is not None else "N/A",
                             "Benchmark":f"{bret:+.2f}%" if bret is not None else "N/A",
                             "Excess Return":f"{ex:+.2f}%" if ex is not None else "N/A"})
    if compare_rows:
        st.dataframe(pd.DataFrame(compare_rows), width="stretch", hide_index=True)
    else:
        st.info("Benchmark comparison data was not returned in a displayable format.")

    st.markdown("#### 🧠 Score Performance")
    if isinstance(score_perf, dict) and score_perf:
        score_rows=[]
        for k,v in score_perf.items():
            if isinstance(v,dict):
                row={"Score / Bucket":str(k)}
                for field,label in [("count","Observations"),("average_return","Avg Return"),("win_rate","Win Rate")]:
                    val=_safe_num(v.get(field))
                    row[label]=int(val) if field=="count" and val is not None else (f"{val:+.2f}%" if field=="average_return" and val is not None else (f"{val:.1f}%" if val is not None else "N/A"))
                score_rows.append(row)
        if score_rows:
            st.dataframe(pd.DataFrame(score_rows), width="stretch", hide_index=True)
        else:
            st.info("Score-level statistics are available in the raw research output but could not be normalized for the summary view.")
    else:
        st.info("No score-level statistics were returned.")

    with st.expander("🔬 Methodology & Raw Research Details"):
        st.write("The validation engine evaluates historical signals at multiple holding periods and compares signal performance with a passive benchmark. Failed rows are excluded from performance calculations rather than counted as losses.")
        st.json(results)

def render_backtesting_page(ticker: str):
    st.title("🧪 Backtesting Lab")
    st.caption("Historical signal validation. This page is intentionally separate from the live dashboard.")
    if BacktestEngine is None:
        st.error("BacktestEngine is not available.")
        return
    if st.button("▶ Run Backtest", type="primary"):
        try:
            data = load_market_data(ticker)
            engine = BacktestEngine()
            results = engine.run(data)
            if isinstance(results, dict):
                render_backtest_summary(results, ticker)
            else:
                st.write(results)
        except Exception as error:
            st.exception(error)
    else:
        st.info("Choose a ticker in the sidebar and press Run Backtest.")


def render_evidence_page(ticker: str):
    st.title("🔬 Evidence Research")
    st.caption("Phase 3.8 → 3.9 → 3.9.1 research/validation. It never changes the production BUY/SELL decision.")
    st.info("This workspace exposes research validation separately so evidence does not silently influence the production signal.")
    if st.button("▶ Run Evidence Research", type="primary"):
        try:
            from app.main import main as research_main
            st.warning("The full CLI research pipeline is designed for terminal execution. Run `python app/main.py` for the complete report.")
            st.code("python app/main.py", language="bash")
        except Exception as error:
            st.exception(error)


# ==================================================================
# MAIN
# ==================================================================

def main():
    inject_theme()
    page, ticker = render_sidebar()
    render_command_header(page, ticker)

    if page == "Dashboard":
        render_dashboard_home(ticker)
    elif page == "Stock Analysis":
        render_stock_analysis_page(ticker)
    elif page == "Portfolio":
        render_portfolio()
    elif page == "Opportunity Radar":
        render_opportunity_radar()
    elif page == "Backtesting":
        render_backtesting_page(ticker)
    elif page == "Evidence Research":
        render_evidence_page(ticker)

    st.divider()
    st.caption("HaViQuant · Turn Market Data Into Decisions · Independent intelligence architecture")

    # Performance-first: avoid blocking the whole Streamlit process with sleep().
    # Live refresh remains user-controlled through the sidebar refresh button.
    if st.session_state.auto_refresh and page in {"Dashboard", "Stock Analysis", "Portfolio"}:
        st.caption(f"Live refresh enabled · click ↻ Refresh Market Data for the latest snapshot · interval preference {st.session_state.refresh_seconds}s")


if __name__ == "__main__":
    main()
