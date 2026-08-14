from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ============================================================
# PROJECT PATH
# ============================================================

APP_DIR = Path(__file__).resolve().parent

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


# ============================================================
# EXISTING ENGINE
# ============================================================

import analysis_pipeline as engine


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
# CONFIGURATION
# ============================================================

DEFAULT_TICKER = "NVDA"

HISTORY_PERIOD = "5y"


# ============================================================
# PREMIUM UI
# ============================================================

def inject_css():

    st.markdown(
        """
        <style>

        /* =====================================================
           GLOBAL
        ===================================================== */

        :root {
            --bg: #06101b;
            --bg2: #091522;
            --panel: #0c1927;
            --panel2: #102234;
            --border: rgba(255,255,255,.075);
            --text: #f5f7fa;
            --muted: #7d8da1;
            --green: #21d58a;
            --red: #ff5d73;
            --blue: #4b9cff;
            --yellow: #efc65b;
            --purple: #a97aff;
        }

        html, body {
            background: var(--bg);
        }

        .stApp {
            background:
                radial-gradient(
                    circle at 12% 0%,
                    rgba(33,213,138,.055),
                    transparent 28%
                ),
                radial-gradient(
                    circle at 90% 0%,
                    rgba(75,156,255,.055),
                    transparent 30%
                ),
                var(--bg);
        }

        .main .block-container {
            max-width: 1800px;
            padding-top: 1rem;
            padding-bottom: 3rem;
        }

        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }

        [data-testid="stToolbar"] {
            visibility: hidden;
        }

        /* =====================================================
           SIDEBAR
        ===================================================== */

        section[data-testid="stSidebar"] {
            background:
                linear-gradient(
                    180deg,
                    #07131f 0%,
                    #050d16 100%
                );
            border-right: 1px solid rgba(255,255,255,.06);
        }

        section[data-testid="stSidebar"] > div {
            padding: 1rem .85rem;
        }

        .brand {
            padding: .35rem .4rem 1rem;
        }

        .brand-title {
            color: white;
            font-size: 1.35rem;
            font-weight: 900;
            letter-spacing: -.04em;
        }

        .brand-subtitle {
            color: #64768a;
            font-size: .58rem;
            margin-top: .15rem;
            letter-spacing: .13em;
        }

        .market-live {
            padding: .72rem .8rem;
            border-radius: .75rem;
            background: rgba(33,213,138,.06);
            border: 1px solid rgba(33,213,138,.15);
            color: var(--green);
            font-size: .66rem;
            font-weight: 800;
            margin-bottom: 1rem;
        }

        .side-label {
            color: #536579;
            font-size: .58rem;
            font-weight: 850;
            letter-spacing: .15em;
            text-transform: uppercase;
            margin: .8rem .3rem .35rem;
        }

        /* =====================================================
           TOP BAR
        ===================================================== */

        .topbar {
            min-height: 66px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0 1.2rem;
            border: 1px solid var(--border);
            border-radius: 1rem;
            background: rgba(12,25,39,.94);
            margin-bottom: .85rem;
            box-shadow: 0 18px 50px rgba(0,0,0,.15);
        }

        .top-title {
            color: white;
            font-size: 1.05rem;
            font-weight: 850;
        }

        .top-subtitle {
            color: var(--muted);
            font-size: .62rem;
            margin-top: .12rem;
        }

        .live {
            display: flex;
            align-items: center;
            gap: .4rem;
            color: var(--green);
            background: rgba(33,213,138,.06);
            border: 1px solid rgba(33,213,138,.14);
            padding: .4rem .65rem;
            border-radius: 99px;
            font-size: .6rem;
            font-weight: 850;
        }

        .live-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--green);
            box-shadow: 0 0 9px rgba(33,213,138,.9);
        }

        /* =====================================================
           STOCK HEADER
        ===================================================== */

        .stock-header {
            border: 1px solid var(--border);
            border-radius: 1rem;
            background:
                linear-gradient(
                    135deg,
                    rgba(16,34,52,.98),
                    rgba(8,20,32,.98)
                );
            padding: 1.15rem 1.3rem;
            margin-bottom: .85rem;
        }

        .symbol {
            color: white;
            font-size: 1.85rem;
            line-height: 1;
            font-weight: 950;
            letter-spacing: -.06em;
        }

        .company {
            color: var(--muted);
            font-size: .64rem;
            margin-top: .2rem;
        }

        .price {
            color: white;
            font-size: 2rem;
            line-height: 1;
            font-weight: 950;
            letter-spacing: -.055em;
            text-align: right;
        }

        .change {
            font-size: .68rem;
            font-weight: 850;
            text-align: right;
            margin-top: .25rem;
        }

        .green {
            color: var(--green);
        }

        .red {
            color: var(--red);
        }

        /* =====================================================
           SECTION
        ===================================================== */

        .section-title {
            color: white;
            font-size: .9rem;
            font-weight: 850;
            margin: 1rem 0 .4rem;
        }

        .section-subtitle {
            color: #64768b;
            font-size: .62rem;
            margin-bottom: .6rem;
        }

        /* =====================================================
           METRIC CARD
        ===================================================== */

        .metric-card {
            min-height: 108px;
            padding: .9rem;
            border: 1px solid var(--border);
            border-radius: .85rem;
            background:
                linear-gradient(
                    145deg,
                    rgba(15,32,49,.97),
                    rgba(8,20,32,.97)
                );
            box-shadow: 0 10px 30px rgba(0,0,0,.12);
        }

        .metric-label {
            color: #708197;
            font-size: .56rem;
            font-weight: 850;
            letter-spacing: .13em;
            text-transform: uppercase;
        }

        .metric-value {
            color: white;
            font-size: 1.35rem;
            font-weight: 900;
            margin-top: .38rem;
        }

        .metric-description {
            color: #617389;
            font-size: .59rem;
            margin-top: .2rem;
        }

        /* =====================================================
           DECISION
        ===================================================== */

        .decision-card {
            min-height: 245px;
            padding: 1.25rem;
            border-radius: 1rem;
            border: 1px solid rgba(33,213,138,.2);
            background:
                radial-gradient(
                    circle at 90% 8%,
                    rgba(33,213,138,.13),
                    transparent 32%
                ),
                linear-gradient(
                    145deg,
                    #10271f,
                    #08161b
                );
            box-shadow: 0 18px 45px rgba(0,0,0,.17);
        }

        .decision-label {
            color: #6e8b7d;
            font-size: .58rem;
            font-weight: 850;
            letter-spacing: .15em;
        }

        .decision-value {
            color: var(--green);
            font-size: 1.65rem;
            font-weight: 950;
            margin-top: .45rem;
        }

        .decision-score {
            color: white;
            font-size: 3.5rem;
            line-height: .95;
            font-weight: 950;
            margin-top: .55rem;
        }

        .decision-caption {
            color: #6d867b;
            font-size: .6rem;
            margin-top: .15rem;
        }

        .decision-note {
            color: #7c9188;
            font-size: .63rem;
            line-height: 1.55;
            margin-top: .9rem;
        }

        /* =====================================================
           EVIDENCE
        ===================================================== */

        .evidence-card {
            min-height: 245px;
            padding: 1.25rem;
            border-radius: 1rem;
            border: 1px solid rgba(75,156,255,.16);
            background:
                linear-gradient(
                    145deg,
                    rgba(14,31,48,.98),
                    rgba(7,18,29,.98)
                );
        }

        .evidence-title {
            color: white;
            font-size: .95rem;
            font-weight: 900;
        }

        .research-badge {
            display: inline-block;
            margin-top: .5rem;
            padding: .35rem .5rem;
            border-radius: .4rem;
            color: var(--yellow);
            background: rgba(239,198,91,.06);
            border: 1px solid rgba(239,198,91,.13);
            font-size: .55rem;
            font-weight: 850;
        }

        .evidence-body {
            color: #7d8fa3;
            font-size: .64rem;
            line-height: 1.6;
            margin-top: .75rem;
        }

        /* =====================================================
           NOTICE
        ===================================================== */

        .notice {
            padding: .7rem .8rem;
            border-radius: .65rem;
            color: #7d96b3;
            background: rgba(75,156,255,.045);
            border: 1px solid rgba(75,156,255,.12);
            font-size: .6rem;
            line-height: 1.5;
        }

        .warning {
            padding: .7rem .8rem;
            border-radius: .65rem;
            color: #c5a957;
            background: rgba(239,198,91,.045);
            border: 1px solid rgba(239,198,91,.12);
            font-size: .6rem;
            line-height: 1.5;
        }

        /* =====================================================
           STREAMLIT BUTTONS
        ===================================================== */

        .stButton > button {
            width: 100%;
            border-radius: .65rem;
            min-height: 38px;
            border: 1px solid rgba(255,255,255,.07);
            background: #0d1c2b;
            color: #cbd5e1;
            font-weight: 750;
        }

        .stButton > button:hover {
            color: white;
            background: #122638;
            border-color: rgba(33,213,138,.25);
        }

        /* =====================================================
           TEXT INPUT
        ===================================================== */

        div[data-testid="stTextInput"] input {
            background: #0b1927 !important;
            color: white !important;
            border: 1px solid rgba(255,255,255,.08) !important;
            border-radius: .65rem !important;
        }

        /* =====================================================
           RADIO
        ===================================================== */

        div[role="radiogroup"] {
            gap: .15rem;
        }

        div[role="radiogroup"] label {
            padding: .5rem .55rem !important;
            border-radius: .6rem;
        }

        div[role="radiogroup"] label:hover {
            background: rgba(255,255,255,.035);
        }

        /* =====================================================
           PLOTLY
        ===================================================== */

        div[data-testid="stPlotlyChart"] {
            border: 1px solid rgba(255,255,255,.065);
            border-radius: 1rem;
            overflow: hidden;
            background: #091624;
            box-shadow: 0 18px 50px rgba(0,0,0,.18);
        }

        /* =====================================================
           FOOTER
        ===================================================== */

        .footer {
            text-align: center;
            color: #405267;
            font-size: .55rem;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid rgba(255,255,255,.035);
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SAFE HELPERS
# ============================================================

def sf(value, default=0.0):

    try:

        result = float(value)

        if not np.isfinite(result):
            return default

        return result

    except Exception:
        return default


def si(value, default=0):

    try:
        return int(float(value))

    except Exception:
        return default


def text(value, default="N/A"):

    if value is None:
        return default

    value = str(value).strip()

    return value if value else default


# ============================================================
# ENGINE EXECUTION
# ============================================================

@st.cache_data(
    ttl=300,
    show_spinner=False,
)
def run_analysis(ticker: str):

    """
    Runs the EXISTING StockMarketApp engine.

    We do not calculate a second decision model here.
    """

    # --------------------------------------------------------
    # Existing market-data service
    # --------------------------------------------------------

    market_data = engine.MarketDataService()

    data = market_data.get_history(
        ticker,
        period=engine.HISTORY_PERIOD,
    )

    if data is None or data.empty:

        raise RuntimeError(
            f"No market data returned for {ticker}."
        )

    # --------------------------------------------------------
    # Technical Analysis
    # --------------------------------------------------------

    technical_engine = (
        engine.TechnicalAnalysisEngine()
    )

    technical = technical_engine.analyze(
        data
    )

    # --------------------------------------------------------
    # Existing Decision Engine
    # --------------------------------------------------------

    decision_engine = (
        engine.DecisionEngine()
    )

    try:

        decision = (
            decision_engine.evaluate(
                technical
            )
        )

    except AttributeError:

        try:

            decision = (
                decision_engine.decide(
                    technical
                )
            )

        except Exception:

            decision = (
                engine.run_decision_engine(
                    technical
                )
            )

    # --------------------------------------------------------
    # Backtest
    # --------------------------------------------------------

    backtest = None

    try:

        backtest_engine = (
            engine.BacktestEngine()
        )

        backtest = (
            backtest_engine.run(
                data
            )
        )

    except Exception:
        backtest = None

    # --------------------------------------------------------
    # Feature Engineering
    # --------------------------------------------------------

    feature_engineering = (
        engine.FeatureEngineeringEngine(
            data
        )
    )

    feature_data = (
        feature_engineering.build_features()
    )

    current_features = (
        feature_engineering
        .build_current_features(
            data
        )
    )

    # --------------------------------------------------------
    # Evidence Model
    # --------------------------------------------------------

    evidence_engine = (
        engine.EvidenceEngine(
            feature_data=feature_data
        )
    )

    # --------------------------------------------------------
    # Evidence evaluation
    # --------------------------------------------------------

    current_evidence = None
    evidence_test_results = None
    evidence_statistics = None

    try:

        result = engine.evaluate_evidence(
            evidence_engine,
            current_features,
            feature_data,
        )

        if isinstance(result, tuple):

            if len(result) >= 1:
                current_evidence = result[0]

            if len(result) >= 2:
                evidence_test_results = result[1]

            if len(result) >= 3:
                evidence_statistics = result[2]

    except Exception:

        # Evidence remains optional for UI.
        current_evidence = None

    return {
        "ticker": ticker,
        "data": data,
        "technical": technical,
        "decision": decision,
        "backtest": backtest,
        "feature_data": feature_data,
        "current_features": current_features,
        "evidence_engine": evidence_engine,
        "current_evidence": current_evidence,
        "evidence_test_results": evidence_test_results,
        "evidence_statistics": evidence_statistics,
    }


# ============================================================
# CHART
# ============================================================

def normalize_dataframe(data):

    if data is None:
        return None

    if not isinstance(data, pd.DataFrame):
        return None

    df = data.copy()

    if isinstance(df.columns, pd.MultiIndex):

        df.columns = [
            str(column[0])
            for column in df.columns
        ]

    rename = {}

    for column in df.columns:

        key = str(column).lower().strip()

        if key == "open":
            rename[column] = "Open"

        elif key == "high":
            rename[column] = "High"

        elif key == "low":
            rename[column] = "Low"

        elif key == "close":
            rename[column] = "Close"

        elif key == "volume":
            rename[column] = "Volume"

    df = df.rename(
        columns=rename
    )

    required = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]

    if not all(
        column in df.columns
        for column in required
    ):
        return None

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

    df["SMA20"] = (
        df["Close"]
        .rolling(20)
        .mean()
    )

    df["SMA50"] = (
        df["Close"]
        .rolling(50)
        .mean()
    )

    df["SMA200"] = (
        df["Close"]
        .rolling(200)
        .mean()
    )

    return df


def build_chart(
    data,
    ticker,
):

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=.025,
        row_heights=[
            .80,
            .20,
        ],
    )

    # --------------------------------------------------------
    # Candles
    # --------------------------------------------------------

    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name=ticker,

            increasing=dict(
                line=dict(
                    color="#21d58a",
                    width=1,
                ),
                fillcolor="#21d58a",
            ),

            decreasing=dict(
                line=dict(
                    color="#ff5d73",
                    width=1,
                ),
                fillcolor="#ff5d73",
            ),
        ),
        row=1,
        col=1,
    )

    # --------------------------------------------------------
    # SMA
    # --------------------------------------------------------

    for name, column, color in [
        (
            "SMA 20",
            "SMA20",
            "#4b9cff",
        ),
        (
            "SMA 50",
            "SMA50",
            "#efc65b",
        ),
        (
            "SMA 200",
            "SMA200",
            "#a97aff",
        ),
    ]:

        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data[column],
                name=name,
                mode="lines",
                line=dict(
                    color=color,
                    width=1.35,
                ),
            ),
            row=1,
            col=1,
        )

    # --------------------------------------------------------
    # Volume
    # --------------------------------------------------------

    volume_colors = np.where(
        data["Close"] >= data["Open"],
        "rgba(33,213,138,.32)",
        "rgba(255,93,115,.30)",
    )

    fig.add_trace(
        go.Bar(
            x=data.index,
            y=data["Volume"],
            name="Volume",
            marker_color=volume_colors,
        ),
        row=2,
        col=1,
    )

    # --------------------------------------------------------
    # Layout
    # --------------------------------------------------------

    fig.update_layout(
        height=650,
        paper_bgcolor="#091624",
        plot_bgcolor="#091624",
        margin=dict(
            l=8,
            r=8,
            t=35,
            b=8,
        ),
        font=dict(
            color="#7d8da1",
            family="Inter, sans-serif",
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
            font=dict(
                size=9
            ),
        ),

        xaxis_rangeslider_visible=False,

        modebar=dict(
            bgcolor="rgba(0,0,0,0)",
            color="#718398",
            activecolor="#21d58a",
        ),
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showline=False,
        fixedrange=False,
    )

    fig.update_yaxes(
        row=1,
        col=1,
        side="right",
        showgrid=True,
        gridcolor="rgba(255,255,255,.045)",
        zeroline=False,
        showline=False,
        fixedrange=False,
        tickfont=dict(size=9),
    )

    fig.update_yaxes(
        row=2,
        col=1,
        side="right",
        showgrid=False,
        zeroline=False,
        showline=False,
        fixedrange=False,
        tickfont=dict(size=8),
    )

    return fig


# ============================================================
# SIDEBAR
# ============================================================

def render_sidebar():

    with st.sidebar:

        st.markdown(
            """
            <div class="brand">

                <div class="brand-title">
                    StockMarketApp
                </div>

                <div class="brand-subtitle">
                    INTELLIGENT MARKET ANALYSIS TERMINAL
                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="market-live">
                ● MARKET DATA ONLINE
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="side-label">Navigation</div>',
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
            label_visibility="collapsed",
            key="navigation",
        )

        st.markdown(
            '<div class="side-label">Ticker</div>',
            unsafe_allow_html=True,
        )

        ticker = st.text_input(
            "Ticker",
            value=st.session_state.get(
                "ticker",
                DEFAULT_TICKER,
            ),
            max_chars=12,
            label_visibility="collapsed",
            key="ticker_input",
        )

        ticker = (
            ticker
            .strip()
            .upper()
        )

        if not ticker:
            ticker = DEFAULT_TICKER

        st.session_state.ticker = ticker

        st.markdown("---")

        st.markdown(
            """
            <div class="side-label">
                Research Status
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.caption(
            "Phase 3.9 evidence remains research-only."
        )

        return page, ticker


# ============================================================
# TOP BAR
# ============================================================

def render_topbar():

    left, right = st.columns(
        [7, 2],
        vertical_alignment="center",
    )

    with left:

        st.markdown(
            """
            <div class="top-title">
                StockMarketApp
            </div>

            <div class="top-subtitle">
                Intelligent market analysis terminal
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:

        st.markdown(
            """
            <div class="live">
                <span class="live-dot"></span>
                MARKET DATA LIVE
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# STOCK HEADER
# ============================================================

def render_stock_header(
    ticker,
    data,
    technical,
):

    latest_price = sf(
        technical.get(
            "price",
            data["Close"].iloc[-1],
        )
    )

    previous_price = sf(
        data["Close"].iloc[-2]
        if len(data) > 1
        else latest_price
    )

    change = (
        latest_price
        - previous_price
    )

    change_pct = (
        change
        / previous_price
        * 100
        if previous_price
        else 0
    )

    css_class = (
        "green"
        if change_pct >= 0
        else "red"
    )

    sign = "+" if change_pct >= 0 else ""

    left, right = st.columns(
        [6, 2],
        vertical_alignment="center",
    )

    with left:

        st.markdown(
            f"""
            <div class="symbol">
                {ticker}
            </div>

            <div class="company">
                Intelligent Market Analysis
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:

        st.markdown(
            f"""
            <div class="price">
                ${latest_price:,.2f}
            </div>

            <div class="change {css_class}">
                {sign}{change_pct:.2f}%
                &nbsp;&nbsp;
                {sign}${abs(change):,.2f}
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# TECHNICAL CONTEXT
# ============================================================

def render_technical(
    technical,
):

    rsi = sf(
        technical.get(
            "rsi"
        ),
        50,
    )

    macd = sf(
        technical.get(
            "macd"
        )
    )

    signal = sf(
        technical.get(
            "macd_signal"
        )
    )

    histogram = sf(
        technical.get(
            "macd_histogram"
        )
    )

    volume = si(
        technical.get(
            "volume"
        )
    )

    avg_volume = si(
        technical.get(
            "avg_volume_20"
        )
    )

    ratio = (
        volume / avg_volume
        if avg_volume > 0
        else 0
    )

    sma20 = sf(
        technical.get(
            "sma_20"
        )
    )

    sma50 = sf(
        technical.get(
            "sma_50"
        )
    )

    price = sf(
        technical.get(
            "price"
        )
    )

    if (
        price > sma20
        and price > sma50
    ):
        trend = "Bullish"

    elif (
        price < sma20
        and price < sma50
    ):
        trend = "Bearish"

    else:
        trend = "Mixed"

    momentum = (
        "Positive"
        if macd >= signal
        else "Negative"
    )

    columns = st.columns(5)

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
            "MACD line",
            "green"
            if macd >= signal
            else "red",
        ),

        (
            "Volume",
            f"{ratio:.2f}x",
            "vs 20D average",
            "",
        ),

        (
            "Trend",
            trend,
            "Moving averages",
            "green"
            if trend == "Bullish"
            else "red"
            if trend == "Bearish"
            else "",
        ),

        (
            "Momentum",
            momentum,
            "MACD vs signal",
            "green"
            if momentum == "Positive"
            else "red",
        ),
    ]

    for column, card in zip(
        columns,
        cards,
    ):

        label, value, description, color = card

        with column:

            st.markdown(
                f"""
                <div class="metric-card">

                    <div class="metric-label">
                        {label}
                    </div>

                    <div class="metric-value {color}">
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
# DECISION CARD
# ============================================================

def render_decision(
    decision,
):

    signal = text(
        decision.get(
            "signal",
            "UNKNOWN",
        )
    )

    score = sf(
        decision.get(
            "technical_score",
            decision.get(
                "score",
                0,
            ),
        )
    )

    upper_signal = signal.upper()

    if "BUY" in upper_signal:
        signal_class = "green"

    elif "SELL" in upper_signal:
        signal_class = "red"

    else:
        signal_class = ""

    st.markdown(
        f"""
        <div class="decision-card">

            <div class="decision-label">
                TECHNICAL DECISION
            </div>

            <div class="decision-value {signal_class}">
                {upper_signal}
            </div>

            <div class="decision-score">
                {score:.0f}
            </div>

            <div class="decision-caption">
                Technical Score / 100
            </div>

            <div class="decision-note">
                This is the existing Technical Decision Engine
                result. The Evidence Model remains isolated and
                does not modify BUY / SELL decisions.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# EVIDENCE CARD
# ============================================================

def render_evidence(
    current_evidence,
):

    if not isinstance(
        current_evidence,
        dict,
    ):

        current_evidence = {}

    summary = current_evidence.get(
        "summary",
        {},
    )

    if not isinstance(
        summary,
        dict,
    ):

        summary = {}

    score = summary.get(
        "score",
        current_evidence.get(
            "score"
        ),
    )

    signal = summary.get(
        "signal",
        current_evidence.get(
            "signal",
            "INSUFFICIENT EVIDENCE",
        ),
    )

    score_text = (
        "N/A"
        if score is None
        else f"{sf(score):.2f}/100"
    )

    st.markdown(
        f"""
        <div class="evidence-card">

            <div class="evidence-title">
                Evidence Model
            </div>

            <div class="research-badge">
                RESEARCH / VALIDATION ONLY
            </div>

            <div class="evidence-body">

                Current Evidence Score:
                <strong>{score_text}</strong>

                <br><br>

                Evidence Signal:
                <strong>{text(signal)}</strong>

                <br><br>

                This model is currently evaluated
                independently from the final BUY / SELL
                Decision Engine.

            </div>

            <div class="notice"
                 style="margin-top:.8rem;">

                Phase 3.9 / 3.9.1 does not automatically
                modify evidence weights or BUY / SELL.

            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# BACKTEST
# ============================================================

def render_backtest(
    backtest,
):

    if not isinstance(
        backtest,
        dict,
    ):

        st.markdown(
            """
            <div class="warning">
                Backtest results are not available.
            </div>
            """,
            unsafe_allow_html=True,
        )

        return

    benchmark = backtest.get(
        "benchmark",
        {},
    )

    if not isinstance(
        benchmark,
        dict,
    ):

        benchmark = {}

    columns = st.columns(4)

    for column, horizon in zip(
        columns,
        [5, 10, 20, 60],
    ):

        row = benchmark.get(
            horizon,
            benchmark.get(
                str(horizon),
                benchmark.get(
                    f"{horizon}d",
                    {},
                ),
            ),
        )

        if not isinstance(
            row,
            dict,
        ):

            row = {}

        win_rate = row.get(
            "win_rate",
            row.get(
                "win_rate_percent"
            ),
        )

        avg_return = row.get(
            "average_return",
            row.get(
                "avg_return"
            ),
        )

        with column:

            if win_rate is None:
                win_display = "N/A"
            else:
                win_display = (
                    f"{sf(win_rate):.2f}%"
                )

            if avg_return is None:
                return_display = "N/A"
            else:
                return_display = (
                    f"{sf(avg_return):+.2f}%"
                )

            st.markdown(
                f"""
                <div class="metric-card">

                    <div class="metric-label">
                        {horizon}D WIN RATE
                    </div>

                    <div class="metric-value">
                        {win_display}
                    </div>

                    <div class="metric-description">
                        Avg return: {return_display}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# DASHBOARD
# ============================================================

def render_dashboard(
    ticker,
    result,
):

    data = result["data"]

    technical = result["technical"]

    decision = result["decision"]

    backtest = result["backtest"]

    current_evidence = (
        result["current_evidence"]
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    render_stock_header(
        ticker,
        data,
        technical,
    )

    # --------------------------------------------------------
    # Chart range
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">Price Chart</div>',
        unsafe_allow_html=True,
    )

    chart_range = st.segmented_control(
        "Chart Range",
        [
            "1D",
            "5D",
            "1M",
            "3M",
            "6M",
            "1Y",
        ],
        default="6M",
        label_visibility="collapsed",
        key="chart_range",
    )

    if chart_range is None:
        chart_range = "6M"

    chart_data = normalize_dataframe(
        data
    )

    if chart_data is not None:

        days = {
            "1D": 2,
            "5D": 7,
            "1M": 25,
            "3M": 70,
            "6M": 135,
            "1Y": 260,
        }

        chart_data = chart_data.tail(
            min(
                days[chart_range],
                len(chart_data),
            )
        )

        chart = build_chart(
            chart_data,
            ticker,
        )

        st.plotly_chart(
            chart,
            use_container_width=True,
            config={
                "displaylogo": False,
                "responsive": True,
                "scrollZoom": True,
                "displayModeBar": True,
            },
            key="main_price_chart",
        )

    else:

        st.markdown(
            """
            <div class="warning">
                Market price data could not be converted
                into a chart.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # --------------------------------------------------------
    # Technical
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">Technical Context</div>',
        unsafe_allow_html=True,
    )

    render_technical(
        technical
    )

    # --------------------------------------------------------
    # Decision
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">Decision Intelligence</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns(
        [1, 1],
        gap="large",
    )

    with left:

        render_decision(
            decision
        )

    with right:

        render_evidence(
            current_evidence
        )

    # --------------------------------------------------------
    # Backtest
    # --------------------------------------------------------

    st.markdown(
        '<div class="section-title">Historical Backtest</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-subtitle">
            Historical results supplied by the existing
            Backtest Engine.
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_backtest(
        backtest
    )


# ============================================================
# STOCK ANALYSIS
# ============================================================

def render_stock_analysis(
    result,
):

    ticker = result["ticker"]

    data = result["data"]

    technical = result["technical"]

    st.markdown(
        '<div class="section-title">Stock Analysis</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="section-subtitle">
            Detailed technical analysis for {ticker}.
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_stock_header(
        ticker,
        data,
        technical,
    )

    render_technical(
        technical
    )

    st.markdown(
        '<div class="section-title">Technical Details</div>',
        unsafe_allow_html=True,
    )

    rows = {
        "Price": sf(
            technical.get("price")
        ),
        "SMA 20": sf(
            technical.get("sma_20")
        ),
        "SMA 50": sf(
            technical.get("sma_50")
        ),
        "SMA 200": sf(
            technical.get("sma_200")
        ),
        "RSI": sf(
            technical.get("rsi")
        ),
        "MACD": sf(
            technical.get("macd")
        ),
        "MACD Signal": sf(
            technical.get("macd_signal")
        ),
        "MACD Histogram": sf(
            technical.get("macd_histogram")
        ),
        "Volume": si(
            technical.get("volume")
        ),
        "Average Volume 20": si(
            technical.get(
                "avg_volume_20"
            )
        ),
    }

    details = pd.DataFrame(
        [
            {
                "Indicator": key,
                "Value": value,
            }
            for key, value in rows.items()
        ]
    )

    st.dataframe(
        details,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# BACKTEST PAGE
# ============================================================

def render_backtest_page(
    result,
):

    st.markdown(
        '<div class="section-title">Backtesting</div>',
        unsafe_allow_html=True,
    )

    render_backtest(
        result["backtest"]
    )

    data = normalize_dataframe(
        result["data"]
    )

    if data is not None:

        chart = build_chart(
            data,
            result["ticker"],
        )

        st.plotly_chart(
            chart,
            use_container_width=True,
            config={
                "displaylogo": False,
                "responsive": True,
                "scrollZoom": True,
            },
            key="backtest_chart",
        )


# ============================================================
# EVIDENCE PAGE
# ============================================================

def render_evidence_page(
    result,
):

    st.markdown(
        '<div class="section-title">Evidence Research</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-subtitle">
            Phase 3.7 / 3.8 / 3.9 / 3.9.1 research diagnostics.
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_evidence(
        result["current_evidence"]
    )

    evidence_statistics = (
        result.get(
            "evidence_statistics"
        )
    )

    if isinstance(
        evidence_statistics,
        dict,
    ):

        st.markdown(
            '<div class="section-title">Evidence Statistics</div>',
            unsafe_allow_html=True,
        )

        rows = []

        for key, value in (
            evidence_statistics.items()
        ):

            rows.append(
                {
                    "Metric": key,
                    "Value": value,
                }
            )

        if rows:

            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# WATCHLIST
# ============================================================

def render_watchlist():

    st.markdown(
        '<div class="section-title">Watchlist</div>',
        unsafe_allow_html=True,
    )

    if "watchlist" not in st.session_state:

        st.session_state.watchlist = [
            "NVDA",
            "SPCX",
            "AMD",
            "GOOGL",
            "AVGO",
        ]

    new_symbol = st.text_input(
        "Add ticker",
        placeholder="NVDA",
        label_visibility="collapsed",
        key="watchlist_input",
    )

    if st.button(
        "Add Ticker",
        key="add_watchlist",
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

    st.markdown(
        '<div class="section-title">Tracked Symbols</div>',
        unsafe_allow_html=True,
    )

    for symbol in st.session_state.watchlist:

        left, right = st.columns(
            [5, 1.5],
            vertical_alignment="center",
        )

        with left:

            st.markdown(
                f"""
                <div class="metric-card">

                    <div class="metric-label">
                        SYMBOL
                    </div>

                    <div class="metric-value">
                        {symbol}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

        with right:

            if st.button(
                "Open",
                key=f"watch_{symbol}",
            ):

                st.session_state.ticker = symbol

                st.session_state.ticker_input = symbol

                st.session_state.navigation = "Dashboard"

                st.rerun()


# ============================================================
# MAIN
# ============================================================

def main():

    inject_css()

    # --------------------------------------------------------
    # Session state
    # --------------------------------------------------------

    if "ticker" not in st.session_state:

        st.session_state.ticker = (
            DEFAULT_TICKER
        )

    # --------------------------------------------------------
    # Sidebar
    # --------------------------------------------------------

    page, ticker = render_sidebar()

    # --------------------------------------------------------
    # Topbar
    # --------------------------------------------------------

    render_topbar()

    # --------------------------------------------------------
    # Watchlist doesn't need analysis
    # --------------------------------------------------------

    if page == "Watchlist":

        render_watchlist()

        st.markdown(
            """
            <div class="footer">
                StockMarketApp · Premium Market Research Terminal
            </div>
            """,
            unsafe_allow_html=True,
        )

        return

    # --------------------------------------------------------
    # Load engine
    # --------------------------------------------------------

    with st.spinner(
        f"Loading {ticker} analysis..."
    ):

        try:

            result = run_analysis(
                ticker
            )

        except Exception as error:

            st.error(
                f"Unable to load {ticker}: {error}"
            )

            st.info(
                "The existing analysis engine is preserved. "
                "Check the terminal for the exact backend error."
            )

            return

    # --------------------------------------------------------
    # Page routing
    # --------------------------------------------------------

    if page == "Dashboard":

        render_dashboard(
            ticker,
            result,
        )

    elif page == "Stock Analysis":

        render_stock_analysis(
            result
        )

    elif page == "Backtesting":

        render_backtest_page(
            result
        )

    elif page == "Evidence Research":

        render_evidence_page(
            result
        )

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="footer">
            StockMarketApp · Premium Market Research Terminal ·
            Evidence Model remains research-only
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()