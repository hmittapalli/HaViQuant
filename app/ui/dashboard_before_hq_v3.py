
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
if "refresh_seconds" not in st.session_state:
    st.session_state.refresh_seconds = 5
if "chart_range" not in st.session_state:
    st.session_state.chart_range = "6M"
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"


# ==================================================================
# UI THEME
# ==================================================================

def inject_theme():
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at 15% 0%, rgba(34,214,138,.05), transparent 28%),
                radial-gradient(circle at 90% 0%, rgba(76,156,255,.06), transparent 32%),
                #06101b;
        }
        .main .block-container {
            max-width: 1820px;
            padding-top: .65rem;
            padding-bottom: 2rem;
        }
        #MainMenu, footer { visibility: hidden; }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg,#07131f,#040b13);
            border-right: 1px solid rgba(255,255,255,.06);
        }

        .hq-card {
            background: linear-gradient(145deg,#0d1d2c,#081521);
            border: 1px solid rgba(255,255,255,.065);
            border-radius: 15px;
            padding: 15px;
            box-shadow: 0 14px 40px rgba(0,0,0,.18);
        }

        .hq-title {
            font-size: 13px;
            font-weight: 900;
            letter-spacing: .08em;
            text-transform: uppercase;
        }

        .hq-sub {
            font-size: 10px;
            color: #718398;
        }

        .hq-big {
            font-size: 34px;
            font-weight: 900;
            letter-spacing: -.045em;
        }

        .hq-positive { color:#22d68a; }
        .hq-negative { color:#ff5f73; }
        .hq-neutral { color:#f2c75c; }

        .hq-news-scroll {
            height: 335px;
            overflow-y: auto;
            padding-right: 6px;
        }

        .hq-news-scroll::-webkit-scrollbar { width: 5px; }
        .hq-news-scroll::-webkit-scrollbar-thumb {
            background:#28435b;
            border-radius:8px;
        }

        .hq-news-item {
            padding: 9px 2px;
            border-bottom: 1px solid rgba(255,255,255,.055);
        }

        .hq-news-title {
            color:#edf4fa;
            font-size:12px;
            line-height:1.4;
            font-weight:750;
        }

        .hq-news-meta {
            color:#718398;
            font-size:9px;
            margin-top:4px;
        }

        .hq-signal {
            border-radius: 12px;
            padding: 12px;
            background:#091724;
            border:1px solid rgba(255,255,255,.06);
        }

        div[data-testid="stMetric"] {
            background:linear-gradient(145deg,#0d1d2c,#091522);
            border:1px solid rgba(255,255,255,.055);
            border-radius:12px;
            padding:.75rem;
        }

        div[data-testid="stPlotlyChart"] {
            background:#08131f;
            border:1px solid rgba(255,255,255,.06);
            border-radius:15px;
            overflow:hidden;
        }

        .small-note {
            color:#718398;
            font-size:9px;
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

    for axis in [
        "xaxis",
        "xaxis2",
        "xaxis3",
    ]:
        fig.update_xaxes(
            row={
                "xaxis": 1,
                "xaxis2": 2,
                "xaxis3": 3,
            }[axis[-1]],
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
        ["1M", "3M", "6M", "1Y", "5Y"],
        default=st.session_state.chart_range,
        key="hq_chart_range",
        label_visibility="collapsed",
    )

    if selected is None:
        selected = "6M"

    st.session_state.chart_range = selected

    periods = {
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
    if yf is not None:
        try:
            quote = yf.Ticker(ticker).fast_info

            price = opt_float(
                quote.get("last_price")
            )

            previous = opt_float(
                quote.get("previous_close")
            )

            if price is not None:
                change = (
                    price - previous
                    if previous is not None
                    else None
                )

                pct = (
                    change / previous * 100
                    if change is not None
                    and previous
                    else None
                )

                return {
                    "price": price,
                    "previous": previous,
                    "change": change,
                    "change_pct": pct,
                    "source": "Yahoo Finance",
                }

        except Exception:
            pass

    return {}


def render_live_header(
    ticker: str,
    df: pd.DataFrame,
):

    quote = fetch_live_quote(ticker)

    last = safe_float(
        df["Close"].iloc[-1]
    )

    if quote.get("price") is not None:
        price = quote["price"]
    else:
        price = last

    pct = quote.get(
        "change_pct"
    )

    title_col, price_col, status_col = st.columns(
        [5, 2.3, 2.2],
        vertical_alignment="center",
    )

    with title_col:
        st.title(
            f"{ticker} · HaViQuant"
        )
        st.caption(
            "INTELLIGENT MARKET ANALYSIS"
        )

    with price_col:
        st.metric(
            "Live Price",
            f"${price:,.2f}",
            (
                f"{pct:+.2f}%"
                if pct is not None
                else "Market data"
            ),
        )

    with status_col:
        st.success("● MARKET DATA")
        st.caption(
            "Quote refresh: 2s cache"
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
# SIDEBAR
# ==================================================================

def render_sidebar() -> tuple[str, str]:

    with st.sidebar:

        logo = (
            Path(__file__).resolve().parent
            / "assets"
            / "haviquant_logo.png"
        )

        if logo.exists():
            st.image(
                str(logo),
                width=190,
            )
        else:
            st.title(
                "📈 HaViQuant"
            )

        st.caption(
            "INTELLIGENT MARKET ANALYSIS"
        )

        page = st.radio(
            "Navigation",
            [
                "Dashboard",
                "Stock Analysis",
                "Backtesting",
                "Evidence Research",
            ],
            index=[
                "Dashboard",
                "Stock Analysis",
                "Backtesting",
                "Evidence Research",
            ].index(
                st.session_state.page
            ),
        )

        ticker = st.text_input(
            "Ticker",
            value=st.session_state.ticker,
            max_chars=12,
            placeholder="NVDA",
        )

        ticker = (
            ticker.strip().upper()
            or DEFAULT_TICKER
        )

        st.session_state.ticker = ticker
        st.session_state.page = page

        st.divider()

        st.checkbox(
            "Live refresh",
            key="auto_refresh",
        )

        st.slider(
            "Refresh interval",
            min_value=2,
            max_value=30,
            value=st.session_state.refresh_seconds,
            step=1,
            key="refresh_seconds",
        )

        if st.button(
            "↻ Refresh Now",
            width="stretch",
        ):
            load_market_data.clear()
            run_existing_analysis.clear()
            fetch_live_quote.clear()
            fetch_news.clear()
            fetch_insider_transactions.clear()
            get_fundamentals.clear()
            st.rerun()

        st.divider()

        st.caption(
            "Chart = visualization"
        )
        st.caption(
            "Decision Engine = production signal"
        )
        st.caption(
            "News / Insiders / Fair Value = independent intelligence"
        )

    return page, ticker


# ==================================================================
# MAIN
# ==================================================================

def main():

    inject_theme()

    page, ticker = render_sidebar()

    try:

        with st.spinner(
            f"Analyzing {ticker}..."
        ):
            result = run_existing_analysis(
                ticker
            )

    except Exception as error:

        st.error(
            f"Unable to analyze {ticker}."
        )

        st.exception(
            error
        )

        return

    df = normalize_market_dataframe(
        result["data"]
    )

    if df is None:
        st.error(
            "Unable to normalize market data."
        )
        return

    st.session_state._hq_df = df

    render_live_header(
        ticker,
        df,
    )

    # --------------------------------------------------------------
    # PRIMARY CHART — ALWAYS TOP
    # --------------------------------------------------------------

    signals = build_signal_map(
        df,
        result["technical"],
        result["decision"],
    )

    render_chart(
        ticker,
        df,
        signals,
    )

    # --------------------------------------------------------------
    # INTELLIGENCE GRID
    # --------------------------------------------------------------

    news_col, fair_col = st.columns(
        [1, 1],
        gap="large",
    )

    with news_col:
        render_news(ticker)

    with fair_col:
        render_fair_value(ticker)

    insider_col, decision_col = st.columns(
        [1, 1],
        gap="large",
    )

    with insider_col:
        render_insiders(ticker)

    with decision_col:
        render_production_decision(
            result["decision"]
        )

    # --------------------------------------------------------------
    # SIGNAL ENGINE
    # --------------------------------------------------------------

    render_signal_dashboard(
        signals,
        result["decision"],
    )

    # --------------------------------------------------------------
    # TECHNICAL CONTEXT
    # --------------------------------------------------------------

    render_technical_context(
        result["technical"],
        df,
    )

    # --------------------------------------------------------------
    # BACKTEST
    # --------------------------------------------------------------

    if page == "Backtesting":

        st.subheader(
            "Historical Backtest"
        )

        if BacktestEngine is None:

            st.info(
                "Existing BacktestEngine is not available."
            )

        else:

            try:

                engine = BacktestEngine()

                if hasattr(
                    engine,
                    "run",
                ):

                    result_bt = engine.run(
                        result["data"]
                    )

                    if isinstance(
                        result_bt,
                        dict,
                    ):

                        st.json(
                            result_bt
                        )

                    else:

                        st.write(
                            result_bt
                        )

                else:

                    st.info(
                        "BacktestEngine does not expose run()."
                    )

            except Exception as error:

                st.warning(
                    "Historical backtest could not be displayed."
                )

                st.caption(
                    safe_text(error)
                )

    elif page == "Evidence Research":

        st.subheader(
            "Evidence / Research Model"
        )

        st.info(
            "Research / validation only. "
            "Evidence remains isolated from the production BUY / SELL decision."
        )

    else:

        with st.expander(
            "Historical Backtest",
            expanded=False,
        ):

            st.info(
                "Open Backtesting from the sidebar to run the full historical module."
            )

    # --------------------------------------------------------------
    # Footer
    # --------------------------------------------------------------

    st.divider()

    st.caption(
        "HaViQuant · Turn Market Data Into Decisions · "
        "Independent intelligence architecture"
    )

    # --------------------------------------------------------------
    # Live refresh
    # --------------------------------------------------------------

    if st.session_state.auto_refresh:

        st.caption(
            f"Next refresh in approximately "
            f"{st.session_state.refresh_seconds}s."
        )

        # Streamlit rerun. This refreshes the live quote/UI.
        # It does NOT mean the public provider supplies a new exchange
        # tick every second.
        time.sleep(
            st.session_state.refresh_seconds
        )

        st.rerun()


if __name__ == "__main__":
    main()
