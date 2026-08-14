"""
StockMarketApp
Premium Streamlit Dashboard

IMPORTANT:
This file is UI ONLY.

It does not modify:
    - DecisionEngine
    - TechnicalAnalysisEngine
    - BacktestEngine
    - Evidence Model
    - Phase 3.7
    - Phase 3.8
    - Phase 3.9

Run:

    cd /Users/harimittapalli/StockMarketApp
    source .venv/bin/activate
    python -m streamlit run app/ui/dashboard.py
"""

from __future__ import annotations

# ============================================================
# PROJECT PATH
# ============================================================

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT / "app"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


# ============================================================
# IMPORTS
# ============================================================

from typing import Any, Optional

import numpy as np
import pandas as pd

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import streamlit as st


# ============================================================
# BACKEND IMPORTS
# ============================================================

from app.data.market_data import MarketDataService
from app.analysis.technical_analysis import TechnicalAnalysisEngine
from app.analysis.decision_engine import DecisionEngine


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="StockMarketApp",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CONSTANTS
# ============================================================

DEFAULT_TICKER = "NVDA"

HISTORY_PERIOD = "5y"

CHART_RANGES = {
    "1M": 22,
    "3M": 66,
    "6M": 132,
    "1Y": 252,
    "5Y": 1260,
}


# ============================================================
# SESSION STATE
# ============================================================

def initialize_state() -> None:

    defaults = {
        "ticker": DEFAULT_TICKER,
        "loaded_ticker": DEFAULT_TICKER,
        "navigation": "Dashboard",
        "chart_range": "6M",
        "analysis_result": None,
        "analysis_ticker": None,
        "watchlist": [
            "NVDA",
            "SPCX",
            "AMD",
            "GOOGL",
            "AVGO",
        ],
    }

    for key, value in defaults.items():

        if key not in st.session_state:

            st.session_state[key] = value


initialize_state()


# ============================================================
# PREMIUM CSS
# ============================================================

def inject_css() -> None:

    st.markdown(
        """
        <style>

        /* ====================================================
           GLOBAL
           ==================================================== */

        .stApp {

            background:
                radial-gradient(
                    circle at 15% 0%,
                    rgba(41, 196, 132, 0.045),
                    transparent 28%
                ),
                radial-gradient(
                    circle at 90% 0%,
                    rgba(65, 135, 255, 0.04),
                    transparent 30%
                ),
                #050c14;

            color: #f4f7fb;
        }


        .main .block-container {

            max-width: 1800px;

            padding-top: 0.65rem;
            padding-bottom: 2rem;
            padding-left: 1.25rem;
            padding-right: 1.25rem;
        }


        /* ====================================================
           REMOVE DEFAULT STREAMLIT ELEMENTS
           ==================================================== */

        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }

        header {
            background: transparent !important;
        }


        /* ====================================================
           SIDEBAR
           ==================================================== */

        section[data-testid="stSidebar"] {

            background:
                linear-gradient(
                    180deg,
                    #07111c 0%,
                    #040a11 100%
                );

            border-right:
                1px solid
                rgba(255,255,255,0.055);
        }


        section[data-testid="stSidebar"] > div {

            padding-top: 1rem;
            padding-left: .85rem;
            padding-right: .85rem;
        }


        /* ====================================================
           SIDEBAR BRAND
           ==================================================== */

        .app-brand {

            padding:
                .2rem .3rem 1rem .3rem;
        }


        .app-brand-title {

            color: #ffffff;

            font-size: 1.35rem;

            font-weight: 900;

            letter-spacing: -0.05em;
        }


        .app-brand-subtitle {

            color: #61758b;

            font-size: .54rem;

            font-weight: 800;

            letter-spacing: .16em;

            margin-top: .18rem;
        }


        .market-online {

            display: flex;

            align-items: center;

            gap: .45rem;

            padding:
                .55rem .7rem;

            border-radius:
                .65rem;

            background:
                rgba(35, 211, 137, .045);

            border:
                1px solid
                rgba(35, 211, 137, .12);

            color:
                #20d58a;

            font-size: .56rem;

            font-weight: 850;

            margin-bottom: 1rem;
        }


        .market-dot {

            width: 6px;
            height: 6px;

            border-radius: 50%;

            background:
                #20d58a;

            box-shadow:
                0 0 10px
                rgba(32,213,138,.9);
        }


        .sidebar-section {

            color: #52667b;

            font-size: .55rem;

            font-weight: 850;

            letter-spacing: .14em;

            text-transform: uppercase;

            margin:
                1rem .25rem .35rem;
        }


        /* ====================================================
           SIDEBAR RADIO
           ==================================================== */

        div[role="radiogroup"] {

            gap: .15rem;
        }


        div[role="radiogroup"] > label {

            min-height: 37px;

            padding:
                .35rem .55rem !important;

            border-radius:
                .55rem;

            color:
                #8394a8 !important;

            transition:
                all .15s ease;
        }


        div[role="radiogroup"] > label:hover {

            background:
                rgba(255,255,255,.035);

            color:
                #ffffff !important;
        }


        /* ====================================================
           INPUTS
           ==================================================== */

        div[data-testid="stTextInput"] input {

            background:
                #091723 !important;

            color:
                #ffffff !important;

            border:
                1px solid
                rgba(255,255,255,.075) !important;

            border-radius:
                .6rem !important;
        }


        div[data-testid="stTextInput"] input:focus {

            border-color:
                rgba(32,213,138,.4) !important;

            box-shadow:
                0 0 0 1px
                rgba(32,213,138,.08) !important;
        }


        /* ====================================================
           BUTTONS
           ==================================================== */

        .stButton > button {

            min-height:
                37px;

            border-radius:
                .6rem;

            background:
                #0b1927;

            border:
                1px solid
                rgba(255,255,255,.07);

            color:
                #bdc8d5;

            font-weight:
                750;
        }


        .stButton > button:hover {

            background:
                #102436;

            border-color:
                rgba(32,213,138,.25);

            color:
                #ffffff;
        }


        /* ====================================================
           TOP HEADER
           ==================================================== */

        .top-header {

            display:
                flex;

            align-items:
                center;

            justify-content:
                space-between;

            min-height:
                64px;

            padding:
                .7rem 1rem;

            margin-bottom:
                .7rem;

            background:
                rgba(8,21,33,.94);

            border:
                1px solid
                rgba(255,255,255,.055);

            border-radius:
                .85rem;

            box-shadow:
                0 14px 45px
                rgba(0,0,0,.15);
        }


        .top-header-title {

            color:
                #ffffff;

            font-size:
                1rem;

            font-weight:
                900;
        }


        .top-header-subtitle {

            color:
                #66788d;

            font-size:
                .57rem;

            margin-top:
                .12rem;
        }


        .live-pill {

            display:
                inline-flex;

            align-items:
                center;

            gap:
                .38rem;

            padding:
                .35rem .55rem;

            border-radius:
                999px;

            background:
                rgba(32,213,138,.045);

            border:
                1px solid
                rgba(32,213,138,.12);

            color:
                #20d58a;

            font-size:
                .55rem;

            font-weight:
                850;
        }


        /* ====================================================
           STOCK HERO
           ==================================================== */

        .stock-hero {

            display:
                flex;

            justify-content:
                space-between;

            align-items:
                center;

            padding:
                1rem 1.2rem;

            margin-bottom:
                .7rem;

            border:
                1px solid
                rgba(255,255,255,.055);

            border-radius:
                .85rem;

            background:
                linear-gradient(
                    135deg,
                    rgba(14,31,47,.98),
                    rgba(7,17,27,.98)
                );
        }


        .stock-ticker {

            font-size:
                2rem;

            font-weight:
                950;

            letter-spacing:
                -.06em;

            color:
                #ffffff;
        }


        .stock-description {

            color:
                #6f8196;

            font-size:
                .58rem;

            margin-top:
                .15rem;
        }


        .stock-price {

            text-align:
                right;

            font-size:
                1.85rem;

            font-weight:
                950;

            letter-spacing:
                -.05em;

            color:
                #ffffff;
        }


        .stock-change {

            text-align:
                right;

            margin-top:
                .15rem;

            font-size:
                .62rem;

            font-weight:
                850;
        }


        .positive {
            color:
                #20d58a !important;
        }


        .negative {
            color:
                #ff5d73 !important;
        }


        /* ====================================================
           SECTION
           ==================================================== */

        .section-heading {

            margin-top:
                .9rem;

            margin-bottom:
                .25rem;

            color:
                #ffffff;

            font-size:
                .88rem;

            font-weight:
                900;
        }


        .section-caption {

            color:
                #617389;

            font-size:
                .57rem;

            margin-bottom:
                .5rem;
        }


        /* ====================================================
           CARDS
           ==================================================== */

        .card {

            background:
                linear-gradient(
                    145deg,
                    rgba(13,30,46,.98),
                    rgba(7,17,27,.98)
                );

            border:
                1px solid
                rgba(255,255,255,.055);

            border-radius:
                .8rem;

            padding:
                .85rem;

            box-shadow:
                0 10px 35px
                rgba(0,0,0,.11);
        }


        .metric-label {

            color:
                #718298;

            font-size:
                .51rem;

            font-weight:
                850;

            letter-spacing:
                .12em;

            text-transform:
                uppercase;
        }


        .metric-value {

            color:
                #ffffff;

            font-size:
                1.2rem;

            font-weight:
                900;

            margin-top:
                .35rem;
        }


        .metric-description {

            color:
                #5e7187;

            font-size:
                .54rem;

            margin-top:
                .15rem;
        }


        /* ====================================================
           DECISION
           ==================================================== */

        .decision-card {

            min-height:
                220px;

            padding:
                1.15rem;

            border:
                1px solid
                rgba(32,213,138,.16);

            border-radius:
                .85rem;

            background:
                radial-gradient(
                    circle at 90% 0%,
                    rgba(32,213,138,.11),
                    transparent 35%
                ),
                linear-gradient(
                    145deg,
                    #0d251d,
                    #071319
                );
        }


        .decision-label {

            color:
                #668578;

            font-size:
                .54rem;

            font-weight:
                850;

            letter-spacing:
                .14em;
        }


        .decision-signal {

            font-size:
                1.5rem;

            font-weight:
                950;

            margin-top:
                .35rem;
        }


        .decision-score {

            color:
                #ffffff;

            font-size:
                3rem;

            line-height:
                1;

            font-weight:
                950;

            letter-spacing:
                -.06em;

            margin-top:
                .45rem;
        }


        .decision-score-label {

            color:
                #668578;

            font-size:
                .54rem;
        }


        .decision-note {

            color:
                #738b80;

            font-size:
                .57rem;

            line-height:
                1.5;

            margin-top:
                .8rem;
        }


        /* ====================================================
           EVIDENCE
           ==================================================== */

        .evidence-card {

            min-height:
                220px;

            padding:
                1.15rem;

            border:
                1px solid
                rgba(75,156,255,.12);

            border-radius:
                .85rem;

            background:
                linear-gradient(
                    145deg,
                    rgba(13,30,47,.98),
                    rgba(7,17,27,.98)
                );
        }


        .evidence-title {

            color:
                #ffffff;

            font-size:
                .9rem;

            font-weight:
                900;
        }


        .research-badge {

            display:
                inline-block;

            margin-top:
                .4rem;

            padding:
                .27rem .42rem;

            border-radius:
                .35rem;

            background:
                rgba(239,198,91,.045);

            border:
                1px solid
                rgba(239,198,91,.11);

            color:
                #d8b650;

            font-size:
                .5rem;

            font-weight:
                850;
        }


        .evidence-text {

            color:
                #74879c;

            font-size:
                .59rem;

            line-height:
                1.6;

            margin-top:
                .7rem;
        }


        /* ====================================================
           INFO / WARNING
           ==================================================== */

        .info-box {

            padding:
                .65rem .75rem;

            background:
                rgba(75,156,255,.035);

            border:
                1px solid
                rgba(75,156,255,.1);

            border-radius:
                .6rem;

            color:
                #7890a9;

            font-size:
                .57rem;

            line-height:
                1.5;
        }


        .warning-box {

            padding:
                .65rem .75rem;

            background:
                rgba(239,198,91,.035);

            border:
                1px solid
                rgba(239,198,91,.1);

            border-radius:
                .6rem;

            color:
                #c2a554;

            font-size:
                .57rem;

            line-height:
                1.5;
        }


        /* ====================================================
           PLOTLY
           ==================================================== */

        div[data-testid="stPlotlyChart"] {

            background:
                #08131f;

            border:
                1px solid
                rgba(255,255,255,.05);

            border-radius:
                .85rem;

            overflow:
                hidden;

            box-shadow:
                0 16px 50px
                rgba(0,0,0,.18);
        }


        /* ====================================================
           TABS
           ==================================================== */

        button[data-baseweb="tab"] {

            color:
                #718298;
        }


        button[data-baseweb="tab"][aria-selected="true"] {

            color:
                #20d58a;
        }


        /* ====================================================
           DATAFRAME
           ==================================================== */

        div[data-testid="stDataFrame"] {

            border-radius:
                .7rem;

            overflow:
                hidden;
        }


        /* ====================================================
           FOOTER
           ==================================================== */

        .footer-text {

            text-align:
                center;

            color:
                #3d5064;

            font-size:
                .5rem;

            margin-top:
                1.8rem;

            padding-top:
                .8rem;

            border-top:
                1px solid
                rgba(255,255,255,.035);
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SAFE HELPERS
# ============================================================

def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:

        if value is None:
            return default

        result = float(value)

        if not np.isfinite(result):
            return default

        return result

    except Exception:

        return default


def safe_text(
    value: Any,
    default: str = "N/A",
) -> str:

    if value is None:
        return default

    text = str(value).strip()

    if not text:
        return default

    return text


def get_value(
    obj: Any,
    key: str,
    default: Any = None,
) -> Any:

    if isinstance(obj, dict):

        return obj.get(
            key,
            default,
        )

    return getattr(
        obj,
        key,
        default,
    )


# ============================================================
# MARKET DATA
# ============================================================

@st.cache_data(
    ttl=300,
    show_spinner=False,
)
def load_market_data(
    ticker: str,
) -> pd.DataFrame:

    service = MarketDataService()

    data = service.get_history(
        ticker,
        period=HISTORY_PERIOD,
    )

    if data is None:
        raise RuntimeError(
            f"No market data returned for {ticker}."
        )

    if data.empty:
        raise RuntimeError(
            f"Market data returned empty data for {ticker}."
        )

    return data


# ============================================================
# TECHNICAL + DECISION ENGINE
# ============================================================

@st.cache_data(
    ttl=300,
    show_spinner=False,
)
def run_current_analysis(
    ticker: str,
):

    data = load_market_data(
        ticker
    )

    # --------------------------------------------------------
    # Existing Technical Engine
    # --------------------------------------------------------

    technical_engine = (
        TechnicalAnalysisEngine()
    )

    analysis = (
        technical_engine.analyze(
            data
        )
    )

    # --------------------------------------------------------
    # Existing Decision Engine
    # --------------------------------------------------------

    decision_engine = (
        DecisionEngine()
    )

    decision = None

    if hasattr(
        decision_engine,
        "evaluate",
    ):

        decision = (
            decision_engine.evaluate(
                analysis
            )
        )

    elif hasattr(
        decision_engine,
        "decide",
    ):

        try:

            decision = (
                decision_engine.decide(
                    analysis
                )
            )

        except TypeError:

            decision = (
                decision_engine.decide(
                    None,
                    analysis,
                )
            )

    else:

        raise RuntimeError(
            "DecisionEngine has neither "
            "evaluate() nor decide()."
        )

    return {
        "ticker": ticker,
        "data": data,
        "analysis": analysis,
        "decision": decision,
    }


# ============================================================
# CHART DATA
# ============================================================

def prepare_chart_data(
    data: pd.DataFrame,
) -> Optional[pd.DataFrame]:

    if data is None:
        return None

    if data.empty:
        return None

    df = data.copy()

    # --------------------------------------------------------
    # Flatten MultiIndex
    # --------------------------------------------------------

    if isinstance(
        df.columns,
        pd.MultiIndex,
    ):

        flattened = []

        for column in df.columns:

            if isinstance(
                column,
                tuple,
            ):

                flattened.append(
                    column[0]
                )

            else:

                flattened.append(
                    column
                )

        df.columns = flattened

    # --------------------------------------------------------
    # Normalize columns
    # --------------------------------------------------------

    rename_map = {}

    for column in df.columns:

        name = (
            str(column)
            .strip()
            .lower()
        )

        if name == "open":
            rename_map[column] = "Open"

        elif name == "high":
            rename_map[column] = "High"

        elif name == "low":
            rename_map[column] = "Low"

        elif name == "close":
            rename_map[column] = "Close"

        elif name in (
            "adj close",
            "adjusted close",
        ):
            rename_map[column] = "Adj Close"

        elif name == "volume":
            rename_map[column] = "Volume"

    df = df.rename(
        columns=rename_map
    )

    required = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:

        raise RuntimeError(
            "Market data missing columns: "
            + ", ".join(missing)
        )

    # --------------------------------------------------------
    # Numeric conversion
    # --------------------------------------------------------

    for column in required:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = df.dropna(
        subset=[
            "Open",
            "High",
            "Low",
            "Close",
        ]
    )

    if df.empty:
        return None

    # --------------------------------------------------------
    # Date index
    # --------------------------------------------------------

    try:

        df.index = pd.to_datetime(
            df.index
        )

    except Exception:
        pass

    df = df.sort_index()

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # These SMA values are ONLY for chart display.
    #
    # They do NOT modify the Decision Engine.
    # --------------------------------------------------------

    df["SMA20"] = (
        df["Close"]
        .rolling(
            20,
            min_periods=1,
        )
        .mean()
    )

    df["SMA50"] = (
        df["Close"]
        .rolling(
            50,
            min_periods=1,
        )
        .mean()
    )

    df["SMA200"] = (
        df["Close"]
        .rolling(
            200,
            min_periods=1,
        )
        .mean()
    )

    return df


# ============================================================
# PRICE CHART
# ============================================================

def build_price_chart(
    data: pd.DataFrame,
    ticker: str,
) -> go.Figure:

    chart = prepare_chart_data(
        data
    )

    if chart is None:

        raise RuntimeError(
            "Unable to prepare chart data."
        )

    # --------------------------------------------------------
    # SUBPLOTS
    # --------------------------------------------------------

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.025,
        row_heights=[
            0.82,
            0.18,
        ],
    )

    # --------------------------------------------------------
    # CANDLESTICK
    # --------------------------------------------------------

    fig.add_trace(
        go.Candlestick(

            x=chart.index,

            open=chart["Open"],

            high=chart["High"],

            low=chart["Low"],

            close=chart["Close"],

            name=ticker,

            increasing=dict(
                line=dict(
                    color="#20d58a",
                    width=1,
                ),
                fillcolor="#20d58a",
            ),

            decreasing=dict(
                line=dict(
                    color="#ff5d73",
                    width=1,
                ),
                fillcolor="#ff5d73",
            ),

            whiskerwidth=.5,

            hovertemplate=(
                "<b>%{x|%b %d, %Y}</b>"
                "<br>Open: $%{open:,.2f}"
                "<br>High: $%{high:,.2f}"
                "<br>Low: $%{low:,.2f}"
                "<br>Close: $%{close:,.2f}"
                "<extra></extra>"
            ),
        ),
        row=1,
        col=1,
    )

    # --------------------------------------------------------
    # SMA 20
    # --------------------------------------------------------

    fig.add_trace(
        go.Scatter(

            x=chart.index,

            y=chart["SMA20"],

            name="SMA 20",

            mode="lines",

            line=dict(
                color="#4b9cff",
                width=1.6,
            ),

            hovertemplate=(
                "SMA20: $%{y:,.2f}"
                "<extra></extra>"
            ),
        ),
        row=1,
        col=1,
    )

    # --------------------------------------------------------
    # SMA 50
    # --------------------------------------------------------

    fig.add_trace(
        go.Scatter(

            x=chart.index,

            y=chart["SMA50"],

            name="SMA 50",

            mode="lines",

            line=dict(
                color="#efc65b",
                width=1.6,
            ),

            hovertemplate=(
                "SMA50: $%{y:,.2f}"
                "<extra></extra>"
            ),
        ),
        row=1,
        col=1,
    )

    # --------------------------------------------------------
    # SMA 200
    # --------------------------------------------------------

    fig.add_trace(
        go.Scatter(

            x=chart.index,

            y=chart["SMA200"],

            name="SMA 200",

            mode="lines",

            line=dict(
                color="#a97aff",
                width=1.6,
            ),

            hovertemplate=(
                "SMA200: $%{y:,.2f}"
                "<extra></extra>"
            ),
        ),
        row=1,
        col=1,
    )

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    volume_colors = np.where(
        chart["Close"] >= chart["Open"],
        "rgba(32,213,138,.38)",
        "rgba(255,93,115,.34)",
    )

    fig.add_trace(
        go.Bar(

            x=chart.index,

            y=chart["Volume"],

            name="Volume",

            marker_color=volume_colors,

            hovertemplate=(
                "Volume: %{y:,.0f}"
                "<extra></extra>"
            ),
        ),
        row=2,
        col=1,
    )

    # --------------------------------------------------------
    # LAYOUT
    # --------------------------------------------------------

    fig.update_layout(

        height=700,

        paper_bgcolor="#08131f",

        plot_bgcolor="#08131f",

        margin=dict(
            l=5,
            r=10,
            t=45,
            b=10,
        ),

        font=dict(
            color="#8192a7",
            size=10,
        ),

        hovermode="x unified",

        dragmode="pan",

        showlegend=True,

        legend=dict(

            orientation="h",

            yanchor="bottom",

            y=1.01,

            xanchor="left",

            x=.01,

            font=dict(
                size=9,
            ),
        ),

        xaxis_rangeslider_visible=False,

        modebar=dict(
            bgcolor="rgba(0,0,0,0)",
            color="#73859a",
            activecolor="#20d58a",
        ),
    )

    # --------------------------------------------------------
    # AXES
    # --------------------------------------------------------

    fig.update_xaxes(

        showgrid=False,

        zeroline=False,

        showline=False,

        rangeslider_visible=False,
    )

    fig.update_yaxes(

        row=1,

        col=1,

        side="right",

        showgrid=True,

        gridcolor=
        "rgba(255,255,255,.045)",

        zeroline=False,

        showline=False,

        tickfont=dict(
            size=9,
        ),
    )

    fig.update_yaxes(

        row=2,

        col=1,

        side="right",

        showgrid=False,

        zeroline=False,

        showline=False,

        tickfont=dict(
            size=8,
        ),
    )

    return fig


# ============================================================
# SIDEBAR
# ============================================================

def render_sidebar() -> str:

    with st.sidebar:

        st.markdown(
            """
            <div class="app-brand">

                <div class="app-brand-title">
                    StockMarketApp
                </div>

                <div class="app-brand-subtitle">
                    INTELLIGENT MARKET TERMINAL
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="market-online">

                <span class="market-dot"></span>

                MARKET DATA ONLINE

            </div>
            """,
            unsafe_allow_html=True,
        )

        # ----------------------------------------------------
        # NAVIGATION
        # ----------------------------------------------------

        st.markdown(
            """
            <div class="sidebar-section">
                Navigation
            </div>
            """,
            unsafe_allow_html=True,
        )

        page = st.radio(
            "Navigation",

            [
                "Dashboard",
                "Stock Analysis",
                "Backtesting",
                "Evidence Research",
                "Watchlist",
            ],

            key="navigation",

            label_visibility="collapsed",
        )

        # ----------------------------------------------------
        # TICKER
        # ----------------------------------------------------

        st.markdown(
            """
            <div class="sidebar-section">
                Market
            </div>
            """,
            unsafe_allow_html=True,
        )

        ticker_input = st.text_input(
            "Ticker Symbol",

            value=st.session_state.get(
                "ticker",
                DEFAULT_TICKER,
            ),

            max_chars=12,

            key="ticker_input",

            label_visibility="collapsed",

            placeholder="Enter ticker e.g. NVDA",
        )

        ticker = (
            ticker_input
            .strip()
            .upper()
        )

        if not ticker:

            ticker = DEFAULT_TICKER

        # ----------------------------------------------------
        # ANALYZE
        # ----------------------------------------------------

        if st.button(
            "↻  Analyze Ticker",
            key="analyze_button",
            use_container_width=True,
        ):

            st.session_state.ticker = ticker

            st.session_state.loaded_ticker = ticker

            st.session_state.analysis_result = None

            st.rerun()

        # ----------------------------------------------------
        # CURRENT SYMBOL
        # ----------------------------------------------------

        st.markdown(
            """
            <div class="sidebar-section">
                Current Symbol
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="info-box">
                <b>{ticker}</b>
                <br>
                Current analysis target
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ----------------------------------------------------
        # SYSTEM
        # ----------------------------------------------------

        st.markdown(
            """
            <div class="sidebar-section">
                System
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption(
            "Technical Decision Engine active"
        )

        st.caption(
            "Evidence Model research-only"
        )

    st.session_state.ticker = ticker

    return page


# ============================================================
# TOP HEADER
# ============================================================

def render_top_header() -> None:

    left, right = st.columns(
        [7, 2],
        vertical_alignment="center",
    )

    with left:

        st.markdown(
            """
            <div class="top-header">

                <div>

                    <div class="top-header-title">
                        StockMarketApp
                    </div>

                    <div class="top-header-subtitle">
                        Intelligent Market Analysis Terminal
                    </div>

                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:

        st.markdown(
            """
            <div style="
                display:flex;
                justify-content:flex-end;
                align-items:center;
                height:64px;
            ">

                <div class="live-pill">

                    <span class="market-dot"></span>

                    MARKET DATA LIVE

                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# STOCK HERO
# ============================================================

def render_stock_hero(
    ticker: str,
    data: pd.DataFrame,
) -> None:

    latest = safe_float(
        data["Close"].iloc[-1]
    )

    if len(data) >= 2:

        previous = safe_float(
            data["Close"].iloc[-2]
        )

    else:

        previous = latest

    change = (
        latest
        - previous
    )

    change_pct = (
        change
        / previous
        * 100
        if previous
        else 0
    )

    positive = (
        change_pct >= 0
    )

    sign = (
        "+"
        if positive
        else ""
    )

    css_class = (
        "positive"
        if positive
        else "negative"
    )

    st.markdown(
        f"""
        <div class="stock-hero">

            <div>

                <div class="stock-ticker">
                    {ticker}
                </div>

                <div class="stock-description">
                    Intelligent Technical Market Analysis
                </div>

            </div>

            <div>

                <div class="stock-price">
                    ${latest:,.2f}
                </div>

                <div class="stock-change {css_class}">
                    {sign}{change_pct:.2f}%
                    &nbsp;&nbsp;
                    ({sign}${abs(change):,.2f})
                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# TECHNICAL CARDS
# ============================================================

def render_technical_cards(
    analysis: Any,
) -> None:

    price = safe_float(
        get_value(
            analysis,
            "price",
            0,
        )
    )

    sma20 = safe_float(
        get_value(
            analysis,
            "sma_20",
            0,
        )
    )

    sma50 = safe_float(
        get_value(
            analysis,
            "sma_50",
            0,
        )
    )

    sma200 = safe_float(
        get_value(
            analysis,
            "sma_200",
            0,
        )
    )

    rsi = safe_float(
        get_value(
            analysis,
            "rsi",
            50,
        ),
        50,
    )

    macd = safe_float(
        get_value(
            analysis,
            "macd",
            0,
        )
    )

    macd_signal = safe_float(
        get_value(
            analysis,
            "macd_signal",
            0,
        )
    )

    volume = safe_float(
        get_value(
            analysis,
            "volume",
            0,
        )
    )

    avg_volume = safe_float(
        get_value(
            analysis,
            "avg_volume_20",
            0,
        )
    )

    volume_ratio = (
        volume / avg_volume
        if avg_volume
        else 0
    )

    # --------------------------------------------------------
    # Trend
    # --------------------------------------------------------

    if (
        price > sma20
        and sma20 > sma50
        and sma50 > sma200
    ):

        trend = "Bullish"

        trend_class = "positive"

    elif (
        price < sma20
        and sma20 < sma50
        and sma50 < sma200
    ):

        trend = "Bearish"

        trend_class = "negative"

    else:

        trend = "Mixed"

        trend_class = ""

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------

    if macd >= macd_signal:

        momentum = "Positive"

        momentum_class = "positive"

    else:

        momentum = "Negative"

        momentum_class = "negative"

    cards = [

        (
            "RSI",
            f"{rsi:.2f}",
            "14-period momentum",
            "",
        ),

        (
            "MACD",
            f"{macd:.2f}",
            "vs signal line",
            momentum_class,
        ),

        (
            "Volume",
            f"{volume_ratio:.2f}x",
            "vs 20D average",
            "",
        ),

        (
            "Trend",
            trend,
            "SMA structure",
            trend_class,
        ),

        (
            "Momentum",
            momentum,
            "MACD structure",
            momentum_class,
        ),
    ]

    columns = st.columns(
        5,
        gap="small",
    )

    for column, card in zip(
        columns,
        cards,
    ):

        label, value, description, css_class = card

        with column:

            st.markdown(
                f"""
                <div class="card">

                    <div class="metric-label">
                        {label}
                    </div>

                    <div class="metric-value {css_class}">
                        {value}
                    </div>

                    <div class="metric-description">
                        {description}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# DECISION DATA
# ============================================================

def extract_decision(
    decision: Any,
):

    signal = safe_text(
        get_value(
            decision,
            "signal",
            "UNKNOWN",
        )
    )

    score = get_value(
        decision,
        "technical_score",
        None,
    )

    if score is None:

        score = get_value(
            decision,
            "score",
            0,
        )

    score = safe_float(
        score
    )

    return signal, score


# ============================================================
# DECISION CARD
# ============================================================

def render_decision_card(
    decision: Any,
) -> None:

    signal, score = (
        extract_decision(
            decision
        )
    )

    signal_upper = signal.upper()

    if "BUY" in signal_upper:

        css_class = "positive"

    elif "SELL" in signal_upper:

        css_class = "negative"

    else:

        css_class = ""

    st.markdown(
        f"""
        <div class="decision-card">

            <div class="decision-label">
                TECHNICAL DECISION
            </div>

            <div class="decision-signal {css_class}">
                {signal_upper}
            </div>

            <div class="decision-score">
                {score:.0f}
            </div>

            <div class="decision-score-label">
                Technical Score / 100
            </div>

            <div class="decision-note">
                Decision supplied directly by the existing
                Decision Engine. The UI does not recalculate
                or modify the production decision.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# EVIDENCE CARD
# ============================================================

def render_evidence_card() -> None:

    st.markdown(
        """
        <div class="evidence-card">

            <div class="evidence-title">
                Evidence Model
            </div>

            <div class="research-badge">
                RESEARCH / VALIDATION ONLY
            </div>

            <div class="evidence-text">

                The Evidence Model is isolated from the
                production BUY / SELL Decision Engine.

                <br><br>

                Phase 3.7 performs feature diagnostics.
                Phase 3.8 performs robustness validation.
                Phase 3.9 / 3.9.1 evaluate the frozen research
                model.

            </div>

            <div class="info-box"
                 style="margin-top:.8rem;">

                Evidence does not modify BUY / SELL decisions.

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# COMPONENT SCORES
# ============================================================

def render_component_scores(
    decision: Any,
) -> None:

    component_scores = (
        get_value(
            decision,
            "component_scores",
            None,
        )
    )

    if not isinstance(
        component_scores,
        dict,
    ):

        component_scores = {}

        mappings = {
            "Trend": "trend_score",
            "Momentum": "momentum_score",
            "MACD": "macd_score",
            "Volume": "volume_score",
            "Price Action": "price_action_score",
        }

        for label, key in mappings.items():

            value = get_value(
                decision,
                key,
                None,
            )

            if value is not None:

                component_scores[
                    label
                ] = value

    if not component_scores:

        return

    st.markdown(
        '<div class="section-heading">Decision Components</div>',
        unsafe_allow_html=True,
    )

    columns = st.columns(
        len(component_scores)
    )

    for column, (
        label,
        value,
    ) in zip(
        columns,
        component_scores.items(),
    ):

        with column:

            st.markdown(
                f"""
                <div class="card">

                    <div class="metric-label">
                        {str(label).upper()}
                    </div>

                    <div class="metric-value">
                        {safe_float(value):.0f}
                    </div>

                    <div class="metric-description">
                        Engine component
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# REASONS
# ============================================================

def render_reasons(
    decision: Any,
) -> None:

    reasons = get_value(
        decision,
        "reasons",
        [],
    )

    if not reasons:
        return

    st.markdown(
        '<div class="section-heading">Decision Reasons</div>',
        unsafe_allow_html=True,
    )

    for reason in reasons:

        st.markdown(
            f"""
            <div class="info-box"
                 style="margin-bottom:.3rem;">
                • {safe_text(reason)}
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# CHART RANGE
# ============================================================

def render_chart(
    ticker: str,
    data: pd.DataFrame,
) -> None:

    st.markdown(
        '<div class="section-heading">Price Chart</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-caption">
            Candlestick price action · SMA 20 · SMA 50 ·
            SMA 200 · Volume
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_range = st.segmented_control(
        "Chart Range",

        [
            "1M",
            "3M",
            "6M",
            "1Y",
            "5Y",
        ],

        default=st.session_state.get(
            "chart_range",
            "6M",
        ),

        key="chart_range_control",

        label_visibility="collapsed",
    )

    if selected_range is None:

        selected_range = "6M"

    st.session_state.chart_range = (
        selected_range
    )

    prepared = prepare_chart_data(
        data
    )

    if prepared is None:

        st.warning(
            f"No chart data available for {ticker}."
        )

        return

    number_of_rows = CHART_RANGES.get(
        selected_range,
        132,
    )

    visible = prepared.tail(
        min(
            number_of_rows,
            len(prepared),
        )
    )

    fig = build_price_chart(
        visible,
        ticker,
    )

    st.plotly_chart(
        fig,

        use_container_width=True,

        config={
            "displaylogo": False,
            "responsive": True,
            "scrollZoom": True,
            "displayModeBar": True,
        },
    )


# ============================================================
# BACKTEST IMPORT
# ============================================================

def load_backtest_engine():

    """
    Lazy import.

    The Dashboard does NOT import or execute the backtest
    engine until the Backtesting page is selected.

    The app directory is already added to sys.path above so
    legacy imports such as `import analysis` can resolve.
    """

    try:

        from app.backtesting.backtest_engine import (
            BacktestEngine,
        )

        return BacktestEngine

    except Exception:

        # Legacy fallback
        from backtesting.backtest_engine import (
            BacktestEngine,
        )

        return BacktestEngine


# ============================================================
# BACKTEST
# ============================================================

@st.cache_data(
    ttl=1800,
    show_spinner=True,
)
def run_backtest(
    ticker: str,
):

    data = load_market_data(
        ticker
    )

    BacktestEngine = (
        load_backtest_engine()
    )

    engine = BacktestEngine()

    # --------------------------------------------------------
    # Different project versions may expose different names.
    # --------------------------------------------------------

    if hasattr(
        engine,
        "run",
    ):

        return engine.run(
            data
        )

    if hasattr(
        engine,
        "run_backtest",
    ):

        return engine.run_backtest(
            data
        )

    if hasattr(
        engine,
        "backtest",
    ):

        return engine.backtest(
            data
        )

    raise RuntimeError(
        "BacktestEngine does not expose "
        "run(), run_backtest(), or backtest()."
    )


# ============================================================
# BACKTEST DISPLAY
# ============================================================

def render_backtest_results(
    results: Any,
) -> None:

    if results is None:

        st.warning(
            "No backtest results returned."
        )

        return

    # --------------------------------------------------------
    # Dictionary result
    # --------------------------------------------------------

    if isinstance(
        results,
        dict,
    ):

        benchmark = results.get(
            "benchmark",
            None,
        )

        if isinstance(
            benchmark,
            dict,
        ):

            st.markdown(
                '<div class="section-heading">Historical Benchmark</div>',
                unsafe_allow_html=True,
            )

            cards = []

            for horizon in [
                5,
                10,
                20,
                60,
            ]:

                row = benchmark.get(
                    horizon,
                    benchmark.get(
                        str(horizon),
                        {},
                    ),
                )

                if not isinstance(
                    row,
                    dict,
                ):

                    row = {}

                win_rate = row.get(
                    "win_rate"
                )

                avg_return = row.get(
                    "average_return"
                )

                cards.append(
                    (
                        f"{horizon}D",
                        (
                            "N/A"
                            if win_rate is None
                            else
                            f"{safe_float(win_rate):.2f}%"
                        ),
                        (
                            "Avg N/A"
                            if avg_return is None
                            else
                            f"Avg {safe_float(avg_return):+.2f}%"
                        ),
                    )
                )

            columns = st.columns(
                4
            )

            for column, (
                label,
                value,
                description,
            ) in zip(
                columns,
                cards,
            ):

                with column:

                    st.markdown(
                        f"""
                        <div class="card">

                            <div class="metric-label">
                                {label} WIN RATE
                            </div>

                            <div class="metric-value">
                                {value}
                            </div>

                            <div class="metric-description">
                                {description}
                            </div>

                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        # ----------------------------------------------------
        # Show useful nested data
        # ----------------------------------------------------

        for key in [
            "outcomes",
            "results",
            "summary",
            "metrics",
        ]:

            value = results.get(
                key
            )

            if value is not None:

                st.markdown(
                    f"### {str(key).title()}"
                )

                if isinstance(
                    value,
                    pd.DataFrame,
                ):

                    st.dataframe(
                        value,
                        use_container_width=True,
                        hide_index=True,
                    )

                elif isinstance(
                    value,
                    list,
                ):

                    st.dataframe(
                        pd.DataFrame(value),
                        use_container_width=True,
                        hide_index=True,
                    )

                elif isinstance(
                    value,
                    dict,
                ):

                    st.json(
                        value
                    )

                else:

                    st.write(
                        value
                    )

        return

    # --------------------------------------------------------
    # DataFrame result
    # --------------------------------------------------------

    if isinstance(
        results,
        pd.DataFrame,
    ):

        st.dataframe(
            results,
            use_container_width=True,
            hide_index=True,
        )

        return

    # --------------------------------------------------------
    # Generic object
    # --------------------------------------------------------

    st.write(
        results
    )


# ============================================================
# WATCHLIST
# ============================================================

def render_watchlist() -> None:

    st.markdown(
        '<div class="section-heading">Watchlist</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-caption">
            Add symbols and analyze them without changing
            the production Decision Engine.
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns(
        [4, 1],
        vertical_alignment="bottom",
    )

    with left:

        new_symbol = st.text_input(
            "Add ticker",
            placeholder="NVDA",
            key="watchlist_input",
        )

    with right:

        if st.button(
            "Add",
            key="watchlist_add",
            use_container_width=True,
        ):

            symbol = (
                new_symbol
                .strip()
                .upper()
            )

            if (
                symbol
                and symbol
                not in st.session_state.watchlist
            ):

                st.session_state.watchlist.append(
                    symbol
                )

                st.rerun()

    st.divider()

    for symbol in st.session_state.watchlist:

        col1, col2 = st.columns(
            [6, 1.5],
            vertical_alignment="center",
        )

        with col1:

            st.markdown(
                f"""
                <div class="card">

                    <div class="metric-label">
                        WATCHLIST
                    </div>

                    <div class="metric-value">
                        {symbol}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

        with col2:

            if st.button(
                "Analyze",
                key=f"watch_{symbol}",
                use_container_width=True,
            ):

                st.session_state.ticker = symbol

                st.session_state.loaded_ticker = symbol

                st.session_state.navigation = (
                    "Dashboard"
                )

                st.session_state.analysis_result = None

                st.rerun()


# ============================================================
# DASHBOARD PAGE
# ============================================================

def render_dashboard_page(
    result: dict,
) -> None:

    ticker = result["ticker"]

    data = result["data"]

    analysis = result["analysis"]

    decision = result["decision"]

    # --------------------------------------------------------
    # HERO
    # --------------------------------------------------------

    render_stock_hero(
        ticker,
        data,
    )

    # --------------------------------------------------------
    # CHART
    # --------------------------------------------------------

    render_chart(
        ticker,
        data,
    )

    # --------------------------------------------------------
    # TECHNICAL
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-heading">Technical Context</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-caption">
            Current market state calculated by the existing
            Technical Analysis Engine.
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_technical_cards(
        analysis
    )

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-heading">Decision Intelligence</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns(
        [1, 1],
        gap="large",
    )

    with left:

        render_decision_card(
            decision
        )

    with right:

        render_evidence_card()

    # --------------------------------------------------------
    # COMPONENTS
    # --------------------------------------------------------

    render_component_scores(
        decision
    )

    render_reasons(
        decision
    )


# ============================================================
# STOCK ANALYSIS PAGE
# ============================================================

def render_stock_analysis_page(
    result: dict,
) -> None:

    ticker = result["ticker"]

    data = result["data"]

    analysis = result["analysis"]

    decision = result["decision"]

    st.markdown(
        '<div class="section-heading">Stock Analysis</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-caption">
            Detailed technical analysis for the selected ticker.
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_stock_hero(
        ticker,
        data,
    )

    render_technical_cards(
        analysis
    )

    st.markdown(
        '<div class="section-heading">Decision</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns(
        [1, 1],
        gap="large",
    )

    with left:

        render_decision_card(
            decision
        )

    with right:

        render_component_scores(
            decision
        )

    render_reasons(
        decision
    )

    render_chart(
        ticker,
        data,
    )


# ============================================================
# BACKTEST PAGE
# ============================================================

def render_backtesting_page(
    ticker: str,
) -> None:

    st.markdown(
        '<div class="section-heading">Historical Backtesting</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-caption">
            The existing Backtest Engine is executed only on
            this page. Opening Dashboard does not trigger the
            historical 934-signal calculation.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="warning-box">
            Backtesting can take longer because the existing
            engine evaluates historical market windows.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    if st.button(
        f"▶  Run {ticker} Backtest",
        key="run_backtest_button",
        use_container_width=False,
    ):

        try:

            with st.spinner(
                f"Running historical backtest for {ticker}..."
            ):

                results = run_backtest(
                    ticker
                )

            st.success(
                "Backtest completed."
            )

            render_backtest_results(
                results
            )

        except Exception as error:

            st.error(
                "Backtest could not be executed."
            )

            st.code(
                repr(error)
            )

            st.info(
                "The production analysis engine was not changed."
            )


# ============================================================
# EVIDENCE PAGE
# ============================================================

def render_evidence_page() -> None:

    st.markdown(
        '<div class="section-heading">Evidence Research</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-caption">
            Research and validation information remains
            separate from the production technical decision.
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_evidence_card()

    st.write("")

    st.markdown(
        """
        <div class="warning-box">

            Evidence Model status is research/validation only.

            <br><br>

            It is not connected to the final BUY / SELL
            Decision Engine.

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# ERROR PAGE
# ============================================================

def render_analysis_error(
    ticker: str,
    error: Exception,
) -> None:

    st.error(
        f"Unable to analyze {ticker}."
    )

    st.markdown(
        """
        <div class="warning-box">

            The dashboard could not load the current
            analysis result.

            <br><br>

            Your production backend has not been modified.

        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander(
        "Technical details"
    ):

        st.code(
            repr(error)
        )


# ============================================================
# LOAD PAGE DATA
# ============================================================

def get_analysis_result(
    ticker: str,
):

    cached = st.session_state.get(
        "analysis_result"
    )

    cached_ticker = st.session_state.get(
        "analysis_ticker"
    )

    if (
        cached is not None
        and cached_ticker == ticker
    ):

        return cached

    result = run_current_analysis(
        ticker
    )

    st.session_state.analysis_result = (
        result
    )

    st.session_state.analysis_ticker = (
        ticker
    )

    return result


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    inject_css()

    # --------------------------------------------------------
    # Sidebar
    # --------------------------------------------------------

    page = render_sidebar()

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    render_top_header()

    # --------------------------------------------------------
    # Watchlist
    # --------------------------------------------------------

    if page == "Watchlist":

        render_watchlist()

        st.markdown(
            """
            <div class="footer-text">
                StockMarketApp · Intelligent Market Terminal
            </div>
            """,
            unsafe_allow_html=True,
        )

        return

    # --------------------------------------------------------
    # Evidence
    # --------------------------------------------------------

    if page == "Evidence Research":

        render_evidence_page()

        st.markdown(
            """
            <div class="footer-text">
                StockMarketApp · Evidence Model Research
            </div>
            """,
            unsafe_allow_html=True,
        )

        return

    # --------------------------------------------------------
    # Backtesting
    #
    # IMPORTANT:
    # Do NOT execute this when Dashboard opens.
    # --------------------------------------------------------

    if page == "Backtesting":

        ticker = st.session_state.get(
            "ticker",
            DEFAULT_TICKER,
        )

        render_backtesting_page(
            ticker
        )

        st.markdown(
            """
            <div class="footer-text">
                StockMarketApp · Historical Backtesting
            </div>
            """,
            unsafe_allow_html=True,
        )

        return

    # --------------------------------------------------------
    # Current analysis
    # --------------------------------------------------------

    ticker = st.session_state.get(
        "ticker",
        DEFAULT_TICKER,
    )

    try:

        with st.spinner(
            f"Loading {ticker} analysis..."
        ):

            result = get_analysis_result(
                ticker
            )

    except Exception as error:

        render_analysis_error(
            ticker,
            error,
        )

        return

    # --------------------------------------------------------
    # Dashboard / Stock Analysis
    # --------------------------------------------------------

    if page == "Dashboard":

        render_dashboard_page(
            result
        )

    elif page == "Stock Analysis":

        render_stock_analysis_page(
            result
        )

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="footer-text">

            StockMarketApp · Premium Market Analysis Terminal

            <br>

            Technical Decision Engine active ·
            Evidence Model research-only

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# ENTRY
# ============================================================

if __name__ == "__main__":

    main()