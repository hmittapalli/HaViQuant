"""
StockMarketApp - Clean Premium Streamlit Dashboard

Important:
- Uses the existing analysis engine.
- Does not modify BUY/SELL logic.
- Does not modify Evidence Model.
- Does not modify backtesting calculations.
- Uses native Streamlit UI components instead of HTML cards.
- Plotly is used only for the price chart.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT / "app"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


# ============================================================
# BACKEND
# ============================================================

from analysis.technical_analysis import (
    TechnicalAnalysisEngine,
)

from analysis.decision_engine import (
    DecisionEngine,
)

from data.market_data import (
    MarketDataService,
)


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="StockMarketApp",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# STATE
# ============================================================

DEFAULT_TICKER = "NVDA"

if "ticker" not in st.session_state:
    st.session_state.ticker = DEFAULT_TICKER

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "chart_range" not in st.session_state:
    st.session_state.chart_range = "6M"

if "watchlist" not in st.session_state:
    st.session_state.watchlist = [
        "NVDA",
        "SPCX",
        "AMD",
        "GOOGL",
        "AVGO",
    ]


# ============================================================
# PREMIUM CSS
#
# IMPORTANT:
# This is the ONLY HTML we use.
# It contains styling only.
# All visible application content below uses
# native Streamlit components.
# ============================================================

def inject_theme():

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
                    rgba(34,214,138,.055),
                    transparent 30%
                ),
                radial-gradient(
                    circle at 90% 0%,
                    rgba(76,156,255,.045),
                    transparent 30%
                ),
                #06101b;
        }

        .main .block-container {
            max-width: 1750px;
            padding-top: .7rem;
            padding-bottom: 2rem;
        }

        #MainMenu {
            visibility: hidden;
        }

        footer {
            visibility: hidden;
        }

        /* ====================================================
           SIDEBAR
        ==================================================== */

        section[data-testid="stSidebar"] {
            background:
                linear-gradient(
                    180deg,
                    #07131f 0%,
                    #040b13 100%
                );

            border-right:
                1px solid
                rgba(255,255,255,.06);
        }

        section[data-testid="stSidebar"] > div {
            padding-top: 1rem;
            padding-left: .85rem;
            padding-right: .85rem;
        }

        /* ====================================================
           BUTTONS
        ==================================================== */

        .stButton > button {
            width: 100%;
            min-height: 40px;

            border-radius: .65rem;

            background:
                #0d1c2b;

            color:
                #d8e0e9;

            border:
                1px solid
                rgba(255,255,255,.08);

            font-weight: 750;
        }

        .stButton > button:hover {
            background:
                #12283b;

            color:
                white;

            border-color:
                rgba(34,214,138,.3);
        }

        /* ====================================================
           INPUT
        ==================================================== */

        div[data-testid="stTextInput"] input {
            background:
                #0b1927 !important;

            color:
                white !important;

            border:
                1px solid
                rgba(255,255,255,.08) !important;

            border-radius:
                .65rem !important;
        }

        /* ====================================================
           RADIO
        ==================================================== */

        div[role="radiogroup"] {
            gap: .2rem;
        }

        div[role="radiogroup"] label {
            border-radius:
                .6rem;

            padding:
                .45rem .55rem !important;
        }

        div[role="radiogroup"] label:hover {
            background:
                rgba(255,255,255,.04);
        }

        /* ====================================================
           METRIC
        ==================================================== */

        div[data-testid="stMetric"] {
            background:
                linear-gradient(
                    145deg,
                    #0d1d2c,
                    #091522
                );

            border:
                1px solid
                rgba(255,255,255,.06);

            border-radius:
                .75rem;

            padding:
                .8rem;

            min-height:
                110px;
        }

        div[data-testid="stMetricLabel"] {
            color:
                #71839a;
        }

        div[data-testid="stMetricValue"] {
            color:
                #f5f7fb;
        }

        /* ====================================================
           PLOTLY
        ==================================================== */

        div[data-testid="stPlotlyChart"] {
            background:
                #08131f;

            border:
                1px solid
                rgba(255,255,255,.055);

            border-radius:
                .9rem;

            overflow:
                hidden;

            box-shadow:
                0 15px 45px
                rgba(0,0,0,.18);
        }

        /* ====================================================
           DATAFRAME
        ==================================================== */

        div[data-testid="stDataFrame"] {
            border-radius:
                .75rem;

            overflow:
                hidden;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# HELPERS
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

    return text if text else default


def first_value(
    source: Dict[str, Any],
    keys: list[str],
    default: Any = None,
) -> Any:

    for key in keys:

        if key in source:

            value = source[key]

            if value is not None:
                return value

    return default


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
        period="5y",
    )

    if data is None:
        raise RuntimeError(
            f"No market data returned for {ticker}."
        )

    if data.empty:
        raise RuntimeError(
            f"Market data is empty for {ticker}."
        )

    return data


# ============================================================
# CURRENT ANALYSIS
# ============================================================

@st.cache_data(
    ttl=300,
    show_spinner=False,
)
def run_analysis(
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

    technical = (
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

    if hasattr(
        decision_engine,
        "evaluate",
    ):

        decision = (
            decision_engine.evaluate(
                technical
            )
        )

    elif hasattr(
        decision_engine,
        "decide",
    ):

        try:

            decision = (
                decision_engine.decide(
                    technical
                )
            )

        except TypeError:

            decision = (
                decision_engine.decide(
                    None,
                    technical,
                )
            )

    else:

        raise RuntimeError(
            "DecisionEngine does not expose "
            "evaluate() or decide()."
        )

    return {
        "ticker": ticker,
        "data": data,
        "technical": technical,
        "decision": decision,
    }


# ============================================================
# CHART DATA
# ============================================================

def normalize_market_dataframe(
    data: Any,
) -> Optional[pd.DataFrame]:

    if data is None:
        return None

    if not isinstance(
        data,
        pd.DataFrame,
    ):

        try:

            data = pd.DataFrame(
                data
            )

        except Exception:

            return None

    if data.empty:
        return None

    df = data.copy()

    # --------------------------------------------------------
    # MultiIndex
    # --------------------------------------------------------

    if isinstance(
        df.columns,
        pd.MultiIndex,
    ):

        df.columns = [
            column[0]
            if isinstance(
                column,
                tuple,
            )
            else column
            for column in df.columns
        ]

    # --------------------------------------------------------
    # Normalize names
    # --------------------------------------------------------

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

        name = (
            str(column)
            .strip()
            .lower()
        )

        if name in mapping:

            rename[column] = mapping[name]

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

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:

        raise RuntimeError(
            "Missing market columns: "
            + ", ".join(missing)
        )

    # --------------------------------------------------------
    # Datetime
    # --------------------------------------------------------

    try:

        df.index = pd.to_datetime(
            df.index
        )

    except Exception:

        pass

    df = df.sort_index()

    # --------------------------------------------------------
    # Numeric
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
    # Chart indicators
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

def build_chart(
    data: pd.DataFrame,
    ticker: str,
) -> go.Figure:

    data = normalize_market_dataframe(
        data
    )

    if data is None:

        raise RuntimeError(
            "Unable to prepare chart data."
        )

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
    # Candlestick
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
                    color="#22d68a",
                    width=1,
                ),
                fillcolor="#22d68a",
            ),

            decreasing=dict(
                line=dict(
                    color="#ff5f73",
                    width=1,
                ),
                fillcolor="#ff5f73",
            ),

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
    # SMA20
    # --------------------------------------------------------

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["SMA20"],
            name="SMA 20",
            mode="lines",
            line=dict(
                color="#4c9cff",
                width=1.5,
            ),
        ),
        row=1,
        col=1,
    )

    # --------------------------------------------------------
    # SMA50
    # --------------------------------------------------------

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["SMA50"],
            name="SMA 50",
            mode="lines",
            line=dict(
                color="#f2c75c",
                width=1.5,
            ),
        ),
        row=1,
        col=1,
    )

    # --------------------------------------------------------
    # SMA200
    # --------------------------------------------------------

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["SMA200"],
            name="SMA 200",
            mode="lines",
            line=dict(
                color="#a978ff",
                width=1.5,
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
        "rgba(34,214,138,.35)",
        "rgba(255,95,115,.32)",
    )

    fig.add_trace(
        go.Bar(
            x=data.index,
            y=data["Volume"],
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
    # Layout
    # --------------------------------------------------------

    fig.update_layout(
        height=680,

        paper_bgcolor="#08131f",

        plot_bgcolor="#08131f",

        margin=dict(
            l=8,
            r=8,
            t=42,
            b=8,
        ),

        font=dict(
            color="#8492a5",
            family=(
                "Inter, "
                "-apple-system, "
                "BlinkMacSystemFont, "
                "sans-serif"
            ),
        ),

        hovermode="x unified",

        dragmode="pan",

        showlegend=True,

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.015,
            xanchor="left",
            x=.01,
            font=dict(
                size=9
            ),
        ),

        xaxis_rangeslider_visible=False,

        modebar=dict(
            bgcolor="rgba(0,0,0,0)",
            color="#718398",
            activecolor="#22d68a",
        ),
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showline=False,
    )

    fig.update_yaxes(
        row=1,
        col=1,
        side="right",
        showgrid=True,
        gridcolor="rgba(255,255,255,.045)",
        zeroline=False,
        showline=False,
        tickfont=dict(size=9),
    )

    fig.update_yaxes(
        row=2,
        col=1,
        side="right",
        showgrid=False,
        zeroline=False,
        showline=False,
        tickfont=dict(size=8),
    )

    return fig


# ============================================================
# SIDEBAR
# ============================================================

def render_sidebar():

    with st.sidebar:

        st.title(
            "📈 StockMarketApp"
        )

        st.caption(
            "INTELLIGENT MARKET TERMINAL"
        )

        st.success(
            "● MARKET DATA ONLINE"
        )

        st.subheader(
            "Navigation"
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
        )

        st.subheader(
            "Market"
        )

        ticker = st.text_input(
            "Ticker",
            value=st.session_state.ticker,
            max_chars=12,
            placeholder="NVDA",
        )

        ticker = (
            ticker
            .strip()
            .upper()
        )

        if not ticker:
            ticker = DEFAULT_TICKER

        st.session_state.ticker = ticker

        st.button(
            "↻ Analyze Ticker",
            width="stretch",
            on_click=clear_analysis_cache,
        )

        st.divider()

        st.caption(
            "Technical Decision Engine active"
        )

        st.caption(
            "Evidence Model research-only"
        )

    return page, ticker


def clear_analysis_cache():

    st.cache_data.clear()


# ============================================================
# HEADER
# ============================================================

def render_header():

    left, right = st.columns(
        [7, 2],
        vertical_alignment="center",
    )

    with left:

        st.title(
            "StockMarketApp"
        )

        st.caption(
            "Intelligent Market Analysis Terminal"
        )

    with right:

        st.success(
            "● MARKET DATA LIVE"
        )


# ============================================================
# STOCK SUMMARY
# ============================================================

def render_stock_summary(
    ticker: str,
    data: pd.DataFrame,
):

    latest = safe_float(
        data["Close"].iloc[-1]
    )

    if len(data) >= 2:

        previous = safe_float(
            data["Close"].iloc[-2]
        )

    else:

        previous = latest

    change = latest - previous

    change_pct = (
        change / previous * 100
        if previous
        else 0
    )

    left, right = st.columns(
        [6, 2],
        vertical_alignment="center",
    )

    with left:

        st.subheader(
            ticker
        )

        st.caption(
            "Intelligent Technical Market Analysis"
        )

    with right:

        st.metric(
            "Current Price",
            f"${latest:,.2f}",
            f"{change_pct:+.2f}%  (${change:+.2f})",
        )


# ============================================================
# TECHNICAL METRICS
# ============================================================

def render_technical_metrics(
    technical: Any,
    decision: Any = None,
):

    def get_value(source, keys, default=None):

        if source is None:
            return default

        if isinstance(source, dict):

            for key in keys:

                if key in source:
                    value = source[key]

                    if value is not None:
                        return value

            return default

        for key in keys:

            value = getattr(
                source,
                key,
                None,
            )

            if value is not None:
                return value

        return default

    # ========================================================
    # READ VALUES SAFELY
    # ========================================================

    rsi = get_value(
        technical,
        ["rsi"],
        None,
    )

    macd = get_value(
        technical,
        ["macd"],
        None,
    )

    macd_signal = get_value(
        technical,
        [
            "macd_signal",
            "macdSignal",
        ],
        None,
    )

    volume = get_value(
        technical,
        ["volume"],
        None,
    )

    avg_volume = get_value(
        technical,
        [
            "avg_volume_20",
            "average_volume_20",
            "avg_volume",
        ],
        None,
    )

    # ========================================================
    # SAFE NUMERIC VALUES
    # ========================================================

    rsi_value = (
        float(rsi)
        if rsi is not None
        else None
    )

    macd_value = (
        float(macd)
        if macd is not None
        else None
    )

    macd_signal_value = (
        float(macd_signal)
        if macd_signal is not None
        else None
    )

    volume_value = (
        float(volume)
        if volume is not None
        else 0.0
    )

    avg_volume_value = (
        float(avg_volume)
        if avg_volume is not None
        else 0.0
    )

    # ========================================================
    # VOLUME RATIO
    # ========================================================

    if avg_volume_value > 0:

        volume_ratio = (
            volume_value
            / avg_volume_value
        )

    else:

        volume_ratio = 0.0

    # ========================================================
    # TREND
    #
    # IMPORTANT:
    # Do not compare SMA values here.
    # Decision Engine is the source of truth.
    # ========================================================

    trend = get_value(
        decision,
        [
            "trend",
            "trend_classification",
            "trend_label",
        ],
        None,
    )

    if trend is None:

        trend = get_value(
            technical,
            [
                "trend",
                "trend_classification",
                "trend_label",
            ],
            "N/A",
        )

    trend = safe_text(
        trend
    )

    # ========================================================
    # MOMENTUM
    # ========================================================

    momentum = get_value(
        decision,
        [
            "momentum",
            "momentum_classification",
            "momentum_label",
        ],
        None,
    )

    if momentum is None:

        if macd_value is None:

            momentum = "N/A"

        elif macd_signal_value is None:

            momentum = "N/A"

        elif macd_value >= macd_signal_value:

            momentum = "Positive"

        else:

            momentum = "Negative"

    momentum = safe_text(
        momentum
    )

    # ========================================================
    # DISPLAY
    # ========================================================

    st.subheader(
        "Technical Context"
    )

    st.caption(
        "Live indicators supplied by the existing Technical Analysis Engine."
    )

    columns = st.columns(
        5
    )

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    with columns[0]:

        st.metric(
            "RSI",

            (
                f"{rsi_value:.2f}"
                if rsi_value is not None
                else "N/A"
            ),

            "14-period",
        )

    # --------------------------------------------------------
    # MACD
    # --------------------------------------------------------

    with columns[1]:

        if macd_value is None:

            macd_display = "N/A"

            macd_help = "Insufficient data"

        else:

            macd_display = (
                f"{macd_value:.2f}"
            )

            if macd_signal_value is not None:

                macd_help = (
                    f"Signal {macd_signal_value:.2f}"
                )

            else:

                macd_help = "Signal unavailable"

        st.metric(
            "MACD",
            macd_display,
            macd_help,
        )

    # --------------------------------------------------------
    # VOLUME
    # --------------------------------------------------------

    with columns[2]:

        if avg_volume_value > 0:

            volume_display = (
                f"{volume_ratio:.2f}x"
            )

            volume_help = (
                "vs 20D average"
            )

        else:

            volume_display = "N/A"

            volume_help = (
                "Average volume unavailable"
            )

        st.metric(
            "Volume",
            volume_display,
            volume_help,
        )

    # --------------------------------------------------------
    # TREND
    # --------------------------------------------------------

    with columns[3]:

        st.metric(
            "Trend",
            trend,
        )

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    with columns[4]:

        st.metric(
            "Momentum",
            momentum,
        )

def render_decision(
    decision: Any,
):

    def value(
        key,
        default=None,
    ):

        if isinstance(
            decision,
            dict,
        ):

            return decision.get(
                key,
                default,
            )

        return getattr(
            decision,
            key,
            default,
        )

    signal = safe_text(
        value(
            "signal",
            "UNKNOWN",
        )
    )

    # ========================================================
    # TECHNICAL SCORE
    #
    # IMPORTANT:
    # Preserve None when the Decision Engine reports
    # INSUFFICIENT_DATA.
    # Never convert missing score to 0.
    # ========================================================

    score = value(
        "technical_score",
        None,
    )

    if score is None:
        score = value(
            "score",
            None,
        )

    if score is not None:
        score = safe_float(score)

    st.subheader(
        "Decision Intelligence"
    )

    left, right = st.columns(
        [1, 1],
        gap="large",
    )

    with left:

        if "BUY" in signal.upper():

            st.success(
                f"🟢 {signal.upper()}"
            )

        elif "SELL" in signal.upper():

            st.error(
                f"🔴 {signal.upper()}"
            )

        else:

            st.warning(
                signal.upper()
            )

        if score is None:

            st.metric(
                "Technical Score",
                "N/A",
            )

            st.caption(
                "Insufficient data for a reliable technical score."
            )

        else:

            st.metric(
                "Technical Score",
                f"{score:.0f} / 100",
            )

        st.caption(
            "This score comes directly from the existing Decision Engine."
        )

    with right:

        st.info(
            "Evidence Model"
        )

        st.caption(
            "RESEARCH / VALIDATION ONLY"
        )

        st.write(
            "Evidence remains isolated from the production BUY / SELL decision."
        )


# ============================================================
# DECISION COMPONENTS
# ============================================================

def render_decision_components(
    decision: Any,
):

    def value(
        key,
        default=None,
    ):

        if isinstance(
            decision,
            dict,
        ):

            return decision.get(
                key,
                default,
            )

        return getattr(
            decision,
            key,
            default,
        )

    component_scores = value(
        "component_scores",
        None,
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

            score = value(
                key,
                None,
            )

            if score is not None:

                component_scores[
                    label
                ] = score

    if not component_scores:

        return

    st.subheader(
        "Decision Components"
    )

    columns = st.columns(
        len(component_scores)
    )

    for column, (
        label,
        score,
    ) in zip(
        columns,
        component_scores.items(),
    ):

        with column:

            st.metric(
                str(label),
                f"{safe_float(score):.0f}",
            )


# ============================================================
# PRICE CHART SECTION
# ============================================================

def render_price_chart(
    ticker: str,
    data: pd.DataFrame,
):

    st.subheader(
        "Price Chart"
    )

    st.caption(
        "Candlestick price action with SMA 20, SMA 50, SMA 200 and volume."
    )

    chart_range = st.segmented_control(
        "Chart Range",

        [
            "1M",
            "3M",
            "6M",
            "1Y",
            "5Y",
        ],

        default="6M",

        key="sm_chart_range",

        label_visibility="collapsed",
    )

    if chart_range is None:

        chart_range = "6M"

    range_map = {
        "1M": 22,
        "3M": 66,
        "6M": 132,
        "1Y": 252,
        "5Y": 1260,
    }

    prepared = normalize_market_dataframe(
        data
    )

    if prepared is None:

        st.warning(
            "Chart data is unavailable."
        )

        return

    visible_rows = range_map.get(
        chart_range,
        132,
    )

    chart_data = prepared.tail(
        min(
            visible_rows,
            len(prepared),
        )
    )

    fig = build_chart(
        chart_data,
        ticker,
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


# ============================================================
# REASONS
# ============================================================

def render_reasons(
    decision: Any,
):

    if isinstance(
        decision,
        dict,
    ):

        reasons = decision.get(
            "reasons",
            [],
        )

    else:

        reasons = getattr(
            decision,
            "reasons",
            [],
        )

    if not reasons:
        return

    st.subheader(
        "Why the Engine Decided This"
    )

    for reason in reasons:

        st.write(
            f"• {safe_text(reason)}"
        )


# ============================================================
# BACKTEST
# ============================================================

def render_backtest(
    analysis: Dict[str, Any],
):

    backtest = analysis.get(
        "backtest",
        {},
    )

    if not isinstance(
        backtest,
        dict,
    ):

        st.info(
            "Backtest data is not available."
        )

        return

    st.subheader(
        "Historical Backtest"
    )

    st.caption(
        "Historical results supplied by the existing backtesting engine."
    )

    columns = st.columns(
        4
    )

    for column, horizon in zip(
        columns,
        [
            "5D",
            "10D",
            "20D",
            "60D",
        ],
    ):

        value = backtest.get(
            horizon
        )

        if value is None:

            value = backtest.get(
                f"win_rate_{horizon.lower()}"
            )

        if value is None:

            display = "N/A"

        else:

            try:

                display = (
                    f"{float(value):.2f}%"
                )

            except Exception:

                display = safe_text(
                    value
                )

        with column:

            st.metric(
                f"{horizon} Win Rate",
                display,
            )


# ============================================================
# WATCHLIST
# ============================================================

def render_watchlist():

    st.subheader(
        "Watchlist"
    )

    st.caption(
        "Track symbols independently from the Decision Engine."
    )

    new_symbol = st.text_input(
        "Add ticker",
        placeholder="NVDA",
        key="watchlist_input",
    )

    if st.button(
        "Add to Watchlist",
        key="watchlist_add",
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

    for symbol in (
        st.session_state.watchlist
    ):

        left, right = st.columns(
            [5, 1],
            vertical_alignment="center",
        )

        with left:

            st.write(
                f"**{symbol}**"
            )

        with right:

            if st.button(
                "Open",
                key=f"open_{symbol}",
            ):

                st.session_state.ticker = (
                    symbol
                )

                st.session_state.page = (
                    "Dashboard"
                )

                st.rerun()


# ============================================================
# EVIDENCE PAGE
# ============================================================

def render_evidence():

    st.subheader(
        "Evidence Research"
    )

    st.caption(
        "Phase 3 evidence diagnostics remain isolated from production BUY / SELL decisions."
    )

    st.info(
        "RESEARCH / VALIDATION ONLY"
    )

    st.write(
        "The Evidence Model is not connected to the final BUY / SELL Decision Engine."
    )

    st.warning(
        "Evidence is not automatically reversed, reweighted, or promoted into the production decision."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    inject_theme()

    # --------------------------------------------------------
    # Sidebar
    # --------------------------------------------------------

    page, ticker = render_sidebar()

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    render_header()

    # --------------------------------------------------------
    # Watchlist
    # --------------------------------------------------------

    if page == "Watchlist":

        render_watchlist()

        return

    # --------------------------------------------------------
    # Evidence
    # --------------------------------------------------------

    if page == "Evidence Research":

        render_evidence()

        return

    # --------------------------------------------------------
    # Backtesting
    # --------------------------------------------------------

    if page == "Backtesting":

        try:

            analysis = run_analysis(
                ticker
            )

            st.subheader(
                f"{ticker} Backtesting"
            )

            st.info(
                "The existing backtesting engine remains unchanged."
            )

            render_backtest(
                analysis
            )

            render_price_chart(
                ticker,
                analysis["data"],
            )

        except Exception as error:

            st.error(
                f"Unable to load {ticker}."
            )

            st.code(
                repr(error)
            )

        return

    # --------------------------------------------------------
    # Current analysis
    # --------------------------------------------------------

    try:

        with st.spinner(
            f"Analyzing {ticker}..."
        ):

            analysis = run_analysis(
                ticker
            )

    except Exception as error:

        st.error(
            f"Unable to analyze {ticker}."
        )

        st.code(
            repr(error)
        )

        return

    # --------------------------------------------------------
    # Dashboard
    # --------------------------------------------------------

    data = analysis["data"]

    render_stock_summary(
        ticker,
        normalize_market_dataframe(data),
    )

    render_price_chart(
        ticker,
        data,
    )

    render_technical_metrics(
        analysis["technical"],
        analysis["decision"],
    )

    render_decision(
        analysis["decision"]
    )

    render_decision_components(
        analysis["decision"]
    )

    render_reasons(
        analysis["decision"]
    )

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    st.divider()

    st.caption(
        "StockMarketApp · Premium Market Analysis Terminal · Evidence Model research-only"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()