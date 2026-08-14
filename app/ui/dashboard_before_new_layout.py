"""
HaViQuant - Complete Premium Dashboard

This file is a complete replacement for:
    app/ui/dashboard.py

Design rules:
- Price chart is the primary top section.
- News, insider activity and fair value are separate intelligence panels.
- News/insiders/fair value NEVER modify the technical Decision Engine.
- The price chart is visualization only.
- Existing TechnicalAnalysisEngine and DecisionEngine remain the source of truth.
- No visible HTML is used for application content; HTML is used only for CSS.
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
from typing import Any, Dict, Optional
from urllib.parse import quote
from urllib.request import Request, urlopen

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
# EXISTING ENGINES
# ============================================================

from analysis.technical_analysis import TechnicalAnalysisEngine
from analysis.decision_engine import DecisionEngine
from data.market_data import MarketDataService


# Optional backtesting engine. The dashboard must still work if a
# backtesting dependency is temporarily unavailable.
try:
    from backtesting.backtest_engine import BacktestEngine
except Exception:
    BacktestEngine = None


# ============================================================
# PAGE
# ============================================================

st.set_page_config(
    page_title="HaViQuant",
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
# THEME
# ============================================================

def inject_theme() -> None:
    st.markdown(
        """
        <style>

        .stApp {
            background:
                radial-gradient(
                    circle at 12% 0%,
                    rgba(34,214,138,.055),
                    transparent 28%
                ),
                radial-gradient(
                    circle at 90% 0%,
                    rgba(76,156,255,.055),
                    transparent 30%
                ),
                #06101b;
        }

        .main .block-container {
            max-width: 1780px;
            padding-top: .65rem;
            padding-bottom: 2rem;
        }

        #MainMenu,
        footer {
            visibility: hidden;
        }

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
            padding:
                1rem .8rem;
        }

        .hq-card {
            background:
                linear-gradient(
                    145deg,
                    rgba(13,31,48,.98),
                    rgba(8,20,33,.98)
                );
            border:
                1px solid
                rgba(255,255,255,.07);
            border-radius:
                14px;
            padding:
                14px;
            box-shadow:
                0 12px 35px
                rgba(0,0,0,.18);
        }

        .hq-panel-title {
            font-size: 13px;
            font-weight: 850;
            letter-spacing: .08em;
            text-transform: uppercase;
            color: #eef4fa;
        }

        .hq-panel-subtitle {
            font-size: 11px;
            color: #718398;
            margin-top: 3px;
        }

        .hq-scroll {
            height: 350px;
            overflow-y: auto;
            padding-right: 7px;
        }

        .hq-scroll::-webkit-scrollbar {
            width: 5px;
        }

        .hq-scroll::-webkit-scrollbar-thumb {
            background: #28435b;
            border-radius: 8px;
        }

        .hq-news-item {
            padding:
                10px 4px;
            border-bottom:
                1px solid
                rgba(255,255,255,.055);
        }

        .hq-news-title {
            font-size: 12px;
            line-height: 1.4;
            font-weight: 700;
            color: #e9f0f7;
        }

        .hq-news-meta {
            margin-top: 5px;
            font-size: 9px;
            color: #718398;
        }

        .hq-value {
            font-size: 30px;
            font-weight: 900;
            color: #f7fbff;
            letter-spacing: -.04em;
        }

        .hq-label {
            color: #718398;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: .08em;
            text-transform: uppercase;
        }

        .hq-positive {
            color: #22d68a;
        }

        .hq-negative {
            color: #ff5f73;
        }

        .hq-neutral {
            color: #f2c75c;
        }

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
                12px;
            padding:
                .8rem;
        }

        div[data-testid="stPlotlyChart"] {
            background: #08131f;
            border:
                1px solid
                rgba(255,255,255,.06);
            border-radius:
                14px;
            overflow: hidden;
            box-shadow:
                0 15px 45px
                rgba(0,0,0,.18);
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


def optional_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None

        result = float(value)

        if not np.isfinite(result):
            return None

        return result

    except Exception:
        return None


def safe_text(
    value: Any,
    default: str = "N/A",
) -> str:
    if value is None:
        return default

    text = str(value).strip()

    return text if text else default


def get_value(
    source: Any,
    keys: list[str],
    default: Any = None,
) -> Any:

    if source is None:
        return default

    if isinstance(source, dict):
        for key in keys:
            if key in source and source[key] is not None:
                return source[key]

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


def money(value: Any) -> str:
    number = optional_float(value)

    if number is None:
        return "N/A"

    if abs(number) >= 1_000_000_000:
        return f"${number / 1_000_000_000:.2f}B"

    if abs(number) >= 1_000_000:
        return f"${number / 1_000_000:.2f}M"

    if abs(number) >= 1_000:
        return f"${number / 1_000:.1f}K"

    return f"${number:,.0f}"


def relative_time(dt: Optional[datetime]) -> str:

    if dt is None:
        return "Time unavailable"

    try:
        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        now = datetime.now(
            timezone.utc
        )

        seconds = max(
            0,
            int(
                (
                    now
                    - dt.astimezone(
                        timezone.utc
                    )
                ).total_seconds()
            ),
        )

        if seconds < 60:
            return "Just now"

        if seconds < 3600:
            return f"{seconds // 60} min ago"

        if seconds < 86400:
            return f"{seconds // 3600} hr ago"

        return dt.strftime(
            "%b %d, %Y"
        )

    except Exception:
        return "Time unavailable"


def http_json(
    url: str,
    timeout: int = 12,
) -> Optional[dict]:

    request = Request(
        url,
        headers={
            "User-Agent": (
                "HaViQuant/1.0 "
                "research dashboard "
                "contact: haviquant@example.com"
            ),
            "Accept": (
                "application/json,"
                "text/plain,*/*"
            ),
        },
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            return json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

    except Exception:
        return None


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
# EXISTING TECHNICAL + DECISION ENGINE
# ============================================================

@st.cache_data(
    ttl=300,
    show_spinner=False,
)
def run_analysis(
    ticker: str,
) -> Dict[str, Any]:

    data = load_market_data(
        ticker
    )

    technical_engine = (
        TechnicalAnalysisEngine()
    )

    technical = (
        technical_engine.analyze(
            data
        )
    )

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
# DATAFRAME NORMALIZATION
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

    if isinstance(
        df.columns,
        pd.MultiIndex,
    ):
        df.columns = [
            str(column[0])
            for column in df.columns
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

        normalized = (
            str(column)
            .strip()
            .lower()
        )

        if normalized in mapping:
            rename[column] = (
                mapping[normalized]
            )

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

    try:
        df.index = pd.to_datetime(
            df.index
        )
    except Exception:
        pass

    df = df.sort_index()

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

    # These are chart-only indicators.
    # They NEVER feed the Decision Engine.
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
# CHART
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
            .79,
            .21,
        ],
    )

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
                    color="#22d68a"
                ),
                fillcolor="#22d68a",
            ),
            decreasing=dict(
                line=dict(
                    color="#ff5f73"
                ),
                fillcolor="#ff5f73",
            ),
        ),
        row=1,
        col=1,
    )

    for column, name, color in [
        (
            "SMA20",
            "SMA 20",
            "#4c9cff",
        ),
        (
            "SMA50",
            "SMA 50",
            "#f2c75c",
        ),
        (
            "SMA200",
            "SMA 200",
            "#a978ff",
        ),
    ]:

        if column in data.columns:

            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data[column],
                    mode="lines",
                    name=name,
                    line=dict(
                        color=color,
                        width=1.5,
                    ),
                    connectgaps=False,
                ),
                row=1,
                col=1,
            )

    fig.add_trace(
        go.Bar(
            x=data.index,
            y=data["Volume"],
            name="Volume",
            marker=dict(
                color="rgba(76,156,255,.30)"
            ),
            hovertemplate=(
                "%{x}<br>"
                "Volume: %{y:,.0f}"
                "<extra></extra>"
            ),
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        height=560,
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
            x=0,
            font=dict(size=9),
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


def render_price_chart(
    ticker: str,
    data: pd.DataFrame,
) -> None:

    st.subheader(
        "📈 Price Chart"
    )

    st.caption(
        "Chart-only visualization. "
        "It does not affect news, insider analysis, fair value, "
        "or the BUY / SELL Decision Engine."
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
        default=(
            st.session_state.get(
                "chart_range",
                "6M",
            )
        ),
        key="hq_chart_range",
        label_visibility="collapsed",
    )

    if chart_range is None:
        chart_range = "6M"

    st.session_state.chart_range = (
        chart_range
    )

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
# LIVE NEWS
# ============================================================

def _news_category(
    title: str,
) -> str:

    text = title.lower()

    if any(
        word in text
        for word in [
            "earnings",
            "revenue",
            "profit",
            "eps",
            "guidance",
        ]
    ):
        return "Earnings"

    if any(
        word in text
        for word in [
            "ceo",
            "cfo",
            "executive",
            "leadership",
        ]
    ):
        return "Management"

    if any(
        word in text
        for word in [
            "upgrade",
            "downgrade",
            "analyst",
            "price target",
        ]
    ):
        return "Analyst"

    if any(
        word in text
        for word in [
            "lawsuit",
            "sec",
            "regulatory",
            "investigation",
            "antitrust",
        ]
    ):
        return "Regulatory"

    if any(
        word in text
        for word in [
            "ai",
            "chip",
            "technology",
            "product",
            "launch",
        ]
    ):
        return "Technology"

    return "Market"


def _news_sentiment(
    title: str,
) -> tuple[str, str]:

    text = title.lower()

    positive = [
        "beat",
        "beats",
        "upgrade",
        "upgraded",
        "surge",
        "surges",
        "growth",
        "record",
        "strong",
        "bullish",
        "approval",
        "approved",
        "buy",
        "wins",
    ]

    negative = [
        "miss",
        "misses",
        "downgrade",
        "downgraded",
        "fall",
        "falls",
        "drop",
        "drops",
        "weak",
        "loss",
        "bearish",
        "lawsuit",
        "investigation",
        "warning",
        "sell",
    ]

    p = sum(
        word in text
        for word in positive
    )

    n = sum(
        word in text
        for word in negative
    )

    if p > n:
        return "Positive", "🟢"

    if n > p:
        return "Negative", "🔴"

    return "Neutral", "🟡"


def _fetch_yahoo_news(
    ticker: str,
    limit: int = 10,
) -> list[dict[str, Any]]:

    url = (
        "https://query1.finance.yahoo.com/"
        "v1/finance/search?"
        f"q={quote(ticker)}"
        f"&quotesCount=1"
        f"&newsCount={limit}"
        "&enableFuzzyQuery=false"
    )

    payload = http_json(url)

    if not payload:
        return []

    items = payload.get(
        "news",
        [],
    )

    results = []
    seen = set()

    for item in items:

        if not isinstance(
            item,
            dict,
        ):
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

        if title.lower() in seen:
            continue

        seen.add(
            title.lower()
        )

        sentiment, icon = (
            _news_sentiment(title)
        )

        published = "Recent"

        timestamp = (
            item.get(
                "providerPublishTime"
            )
        )

        if timestamp:
            try:
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
                "publisher": safe_text(
                    item.get(
                        "publisher",
                        "Yahoo Finance",
                    ),
                    "Yahoo Finance",
                ),
                "link": link,
                "published": published,
                "category": _news_category(
                    title
                ),
                "sentiment": sentiment,
                "icon": icon,
            }
        )

        if len(results) >= limit:
            break

    return results


def _fetch_google_news(
    ticker: str,
    limit: int = 10,
) -> list[dict[str, Any]]:

    query = (
        f'"{ticker}" stock when:2d'
    )

    url = (
        "https://news.google.com/rss/search?"
        f"q={quote(query)}"
        "&hl=en-US&gl=US&ceid=US:en"
    )

    request = Request(
        url,
        headers={
            "User-Agent":
                "Mozilla/5.0 HaViQuant",
        },
    )

    try:
        with urlopen(
            request,
            timeout=12,
        ) as response:

            xml_data = response.read()

    except Exception:
        return []

    try:
        root = ET.fromstring(
            xml_data
        )
    except Exception:
        return []

    results = []
    seen = set()

    for item in root.findall(
        ".//item"
    ):

        title_node = item.find(
            "title"
        )

        link_node = item.find(
            "link"
        )

        pub_node = item.find(
            "pubDate"
        )

        source_node = item.find(
            "source"
        )

        title = safe_text(
            (
                title_node.text
                if title_node is not None
                else None
            ),
            "",
        )

        link = safe_text(
            (
                link_node.text
                if link_node is not None
                else None
            ),
            "",
        )

        if not title or not link:
            continue

        key = title.lower()

        if key in seen:
            continue

        seen.add(key)

        published = "Recent"

        if (
            pub_node is not None
            and pub_node.text
        ):
            try:
                published = relative_time(
                    parsedate_to_datetime(
                        pub_node.text
                    )
                )
            except Exception:
                pass

        sentiment, icon = (
            _news_sentiment(title)
        )

        results.append(
            {
                "title": title,
                "publisher": safe_text(
                    (
                        source_node.text
                        if source_node is not None
                        else None
                    ),
                    "Google News",
                ),
                "link": link,
                "published": published,
                "category": _news_category(
                    title
                ),
                "sentiment": sentiment,
                "icon": icon,
            }
        )

        if len(results) >= limit:
            break

    return results


@st.cache_data(
    ttl=300,
    show_spinner=False,
)
def fetch_news(
    ticker: str,
) -> list[dict[str, Any]]:

    results = _fetch_yahoo_news(
        ticker,
        10,
    )

    if results:
        return results

    return _fetch_google_news(
        ticker,
        10,
    )


def render_news_panel(
    ticker: str,
) -> None:

    st.markdown(
        '<div class="hq-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        "### 📰 Live Market News"
    )

    st.caption(
        f"Recent {ticker} headlines. "
        "News is display-only and does not affect BUY / SELL."
    )

    articles = fetch_news(
        ticker
    )

    if not articles:

        st.info(
            f"No recent news is available for {ticker}."
        )

        st.caption(
            "News providers may temporarily limit public requests."
        )

    else:

        # Native Streamlit container gives us real scrolling.
        with st.container(
            height=350,
            border=False,
        ):

            for article in articles:

                title = article["title"]

                st.markdown(
                    f"**{article['icon']} "
                    f"[{title}]({article['link']})**"
                )

                st.caption(
                    f"{article['publisher']} · "
                    f"{article['published']} · "
                    f"{article['category']} · "
                    f"{article['sentiment']}"
                )

                st.divider()

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# SEC INSIDER ACTIVITY
# ============================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def _sec_cik_for_ticker(
    ticker: str,
) -> Optional[str]:

    url = (
        "https://www.sec.gov/files/"
        "company_tickers.json"
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

            payload = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

    except Exception:
        return None

    target = ticker.upper()

    for item in payload.values():

        if (
            str(
                item.get("ticker", "")
            ).upper()
            == target
        ):

            cik = item.get(
                "cik_str"
            )

            if cik is not None:
                return str(
                    int(cik)
                ).zfill(10)

    return None


def _sec_submissions(
    cik: str,
) -> Optional[dict]:

    url = (
        "https://data.sec.gov/submissions/"
        f"CIK{cik}.json"
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

            return json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

    except Exception:
        return None


@st.cache_data(
    ttl=1800,
    show_spinner=False,
)
def fetch_insider_activity(
    ticker: str,
) -> list[dict[str, Any]]:

    cik = _sec_cik_for_ticker(
        ticker
    )

    if not cik:
        return []

    submissions = _sec_submissions(
        cik
    )

    if not submissions:
        return []

    recent = submissions.get(
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

    accession_numbers = recent.get(
        "accessionNumber",
        [],
    )

    filing_dates = recent.get(
        "filingDate",
        [],
    )

    primary_documents = recent.get(
        "primaryDocument",
        [],
    )

    results = []

    for i, form in enumerate(forms):

        if form not in {
            "4",
            "4/A",
        }:
            continue

        if i >= len(
            accession_numbers
        ):
            continue

        accession = (
            accession_numbers[i]
        )

        filing_date = (
            filing_dates[i]
            if i < len(filing_dates)
            else "N/A"
        )

        document = (
            primary_documents[i]
            if i < len(primary_documents)
            else ""
        )

        accession_clean = (
            accession.replace(
                "-",
                "",
            )
        )

        filing_url = (
            "https://www.sec.gov/Archives/"
            f"edgar/data/{int(cik)}/"
            f"{accession_clean}/"
            f"{document}"
        )

        results.append(
            {
                "form": form,
                "filing_date": filing_date,
                "url": filing_url,
                "action": "Form 4 filed",
                "value": None,
                "insider": "SEC insider filing",
                "role": "Officer / Director / Holder",
            }
        )

        if len(results) >= 8:
            break

    return results


def render_insider_panel(
    ticker: str,
) -> None:

    st.markdown(
        '<div class="hq-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        "### 👔 Insider Activity"
    )

    st.caption(
        "SEC Form 4 activity. "
        "This is separate from the Decision Engine."
    )

    filings = fetch_insider_activity(
        ticker
    )

    if not filings:

        st.info(
            "No recent SEC Form 4 filings were returned."
        )

        st.caption(
            "This does not mean insiders did not trade. "
            "It means the public lookup did not return usable filings."
        )

    else:

        st.metric(
            "Recent Form 4 Filings",
            len(filings),
        )

        for filing in filings:

            st.markdown(
                f"**{filing['action']}** · "
                f"{filing['filing_date']}"
            )

            st.caption(
                "Officers, directors and 10% holders "
                "reported through SEC Form 4."
            )

            st.link_button(
                "Open SEC Filing",
                filing["url"],
            )

            st.divider()

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# FUNDAMENTAL FAIR VALUE
# ============================================================

def _yahoo_fundamentals(
    ticker: str,
) -> dict[str, Any]:

    modules = (
        "price,"
        "summaryDetail,"
        "defaultKeyStatistics,"
        "financialData,"
        "summaryProfile"
    )

    url = (
        "https://query1.finance.yahoo.com/"
        "v10/finance/quoteSummary/"
        f"{quote(ticker)}"
        f"?modules={modules}"
    )

    payload = http_json(
        url
    )

    if not payload:
        return {}

    result = (
        payload
        .get(
            "quoteSummary",
            {}
        )
        .get(
            "result",
            []
        )
    )

    if not result:
        return {}

    return result[0]


def _yahoo_number(
    source: dict,
    key: str,
) -> Optional[float]:

    value = source.get(
        key
    )

    if isinstance(
        value,
        dict,
    ):

        value = value.get(
            "raw"
        )

    return optional_float(
        value
    )


@st.cache_data(
    ttl=1800,
    show_spinner=False,
)
def calculate_fair_value(
    ticker: str,
) -> dict[str, Any]:

    fundamentals = (
        _yahoo_fundamentals(
            ticker
        )
    )

    if not fundamentals:
        return {
            "available": False,
            "reason": (
                "Fundamental valuation data "
                "is not currently available."
            ),
        }

    financial = fundamentals.get(
        "financialData",
        {}
    )

    statistics = fundamentals.get(
        "defaultKeyStatistics",
        {}
    )

    detail = fundamentals.get(
        "summaryDetail",
        {}
    )

    price_block = fundamentals.get(
        "price",
        {}
    )

    current = (
        _yahoo_number(
            price_block,
            "regularMarketPrice",
        )
        or _yahoo_number(
            detail,
            "regularMarketPrice",
        )
    )

    eps = (
        _yahoo_number(
            statistics,
            "trailingEps",
        )
    )

    forward_eps = (
        _yahoo_number(
            statistics,
            "forwardEps",
        )
    )

    revenue_growth = (
        _yahoo_number(
            financial,
            "revenueGrowth",
        )
    )

    free_cash_flow = (
        _yahoo_number(
            financial,
            "freeCashflow",
        )
    )

    operating_cash_flow = (
        _yahoo_number(
            financial,
            "operatingCashflow",
        )
    )

    target_price = (
        _yahoo_number(
            financial,
            "targetMeanPrice",
        )
    )

    # --------------------------------------------------------
    # Method 1: analyst target reference
    # --------------------------------------------------------

    analyst_value = target_price

    # --------------------------------------------------------
    # Method 2: earnings multiple
    #
    # This is deliberately a transparent reference model,
    # not a claim of intrinsic truth.
    # --------------------------------------------------------

    earnings_value = None

    usable_eps = (
        forward_eps
        if forward_eps is not None
        else eps
    )

    if (
        usable_eps is not None
        and usable_eps > 0
    ):

        growth = (
            revenue_growth
            if revenue_growth is not None
            else 0.05
        )

        # Conservative growth-adjusted multiple.
        multiple = min(
            35.0,
            max(
                12.0,
                18.0
                + growth * 100.0 * .50,
            ),
        )

        earnings_value = (
            usable_eps
            * multiple
        )

    # --------------------------------------------------------
    # Method 3: cash-flow reference
    # --------------------------------------------------------

    cashflow_value = None

    if (
        free_cash_flow is not None
        and free_cash_flow > 0
    ):

        # We need shares outstanding to convert FCF
        # to per-share value.
        shares = (
            _yahoo_number(
                financial,
                "sharesOutstanding",
            )
            or _yahoo_number(
                statistics,
                "sharesOutstanding",
            )
        )

        if (
            shares is not None
            and shares > 0
        ):

            fcf_per_share = (
                free_cash_flow
                / shares
            )

            cashflow_value = (
                fcf_per_share
                * 22.0
            )

    candidates = [
        value
        for value in [
            analyst_value,
            earnings_value,
            cashflow_value,
        ]
        if value is not None
        and value > 0
        and math.isfinite(value)
    ]

    if not candidates:

        return {
            "available": False,
            "reason": (
                "Not enough fundamental inputs "
                "for a reliable fair-value estimate."
            ),
            "current": current,
        }

    base = (
        float(
            np.median(
                candidates
            )
        )
    )

    # Scenario spread is deliberately explicit.
    bear = base * .80
    bull = base * 1.20

    upside = None

    if (
        current is not None
        and current > 0
    ):

        upside = (
            (base / current) - 1
        ) * 100

    confidence = (
        "High"
        if len(candidates) >= 3
        else "Moderate"
        if len(candidates) == 2
        else "Low"
    )

    return {
        "available": True,
        "current": current,
        "bear": bear,
        "base": base,
        "bull": bull,
        "upside": upside,
        "confidence": confidence,
        "methods": {
            "Analyst reference":
                analyst_value,
            "Earnings multiple":
                earnings_value,
            "FCF reference":
                cashflow_value,
        },
        "revenue_growth":
            revenue_growth,
        "eps":
            usable_eps,
        "free_cash_flow":
            free_cash_flow,
        "operating_cash_flow":
            operating_cash_flow,
    }


def render_fair_value_panel(
    ticker: str,
) -> None:

    st.markdown(
        '<div class="hq-card">',
        unsafe_allow_html=True,
    )

    st.markdown(
        "### 💰 HaViQuant Fair Value"
    )

    st.caption(
        "Fundamental valuation only. "
        "The price chart is not used to calculate fair value."
    )

    valuation = calculate_fair_value(
        ticker
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

        current = valuation.get(
            "current"
        )

        if current is not None:
            st.metric(
                "Current Price",
                f"${current:,.2f}",
            )

        st.markdown(
            "</div>",
            unsafe_allow_html=True,
        )

        return

    top1, top2 = st.columns(
        2
    )

    with top1:
        st.metric(
            "Base Fair Value",
            f"${valuation['base']:,.2f}",
        )

    with top2:

        upside = valuation.get(
            "upside"
        )

        if upside is None:
            st.metric(
                "Upside / Downside",
                "N/A",
            )
        else:
            st.metric(
                "Upside / Downside",
                f"{upside:+.1f}%",
            )

    bear_col, base_col, bull_col = (
        st.columns(3)
    )

    with bear_col:
        st.metric(
            "Bear",
            f"${valuation['bear']:,.2f}",
        )

    with base_col:
        st.metric(
            "Base",
            f"${valuation['base']:,.2f}",
        )

    with bull_col:
        st.metric(
            "Bull",
            f"${valuation['bull']:,.2f}",
        )

    st.caption(
        f"Confidence: {valuation['confidence']}"
    )

    st.markdown(
        "#### Valuation References"
    )

    for method, value in (
        valuation["methods"].items()
    ):

        if value is None:
            display = "N/A"
        else:
            display = f"${value:,.2f}"

        st.write(
            f"**{method}:** {display}"
        )

    st.caption(
        "Fair value is a model estimate, not a guaranteed target. "
        "Different valuation methods can disagree substantially."
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# STOCK SUMMARY
# ============================================================

def render_stock_summary(
    ticker: str,
    data: pd.DataFrame,
) -> None:

    latest = safe_float(
        data["Close"].iloc[-1]
    )

    previous = (
        safe_float(
            data["Close"].iloc[-2]
        )
        if len(data) >= 2
        else latest
    )

    change = (
        latest - previous
    )

    change_pct = (
        change / previous * 100
        if previous
        else 0
    )

    left, middle, right = st.columns(
        [4, 2, 2],
        vertical_alignment="center",
    )

    with left:

        st.title(
            ticker
        )

        st.caption(
            "HaViQuant Market Intelligence"
        )

    with middle:

        st.metric(
            "Current Price",
            f"${latest:,.2f}",
            f"{change_pct:+.2f}%"
        )

    with right:

        st.caption(
            "Intelligence Modules"
        )

        st.write(
            "📰 News  ·  👔 Insiders  ·  💰 Fair Value"
        )


# ============================================================
# TECHNICAL METRICS
# ============================================================

def render_technical_metrics(
    technical: Any,
    decision: Any = None,
) -> None:

    rsi = optional_float(
        get_value(
            technical,
            ["rsi"],
        )
    )

    macd = optional_float(
        get_value(
            technical,
            ["macd"],
        )
    )

    macd_signal = optional_float(
        get_value(
            technical,
            [
                "macd_signal",
                "macdSignal",
            ],
        )
    )

    volume = optional_float(
        get_value(
            technical,
            ["volume"],
        )
    )

    avg_volume = optional_float(
        get_value(
            technical,
            [
                "avg_volume_20",
                "average_volume_20",
                "avg_volume",
            ],
        )
    )

    volume_ratio = (
        volume / avg_volume
        if (
            volume is not None
            and avg_volume is not None
            and avg_volume > 0
        )
        else None
    )

    trend = safe_text(
        get_value(
            decision,
            [
                "trend",
                "trend_classification",
                "trend_label",
            ],
            get_value(
                technical,
                [
                    "trend",
                    "trend_classification",
                    "trend_label",
                ],
                "N/A",
            ),
        )
    )

    momentum = safe_text(
        get_value(
            decision,
            [
                "momentum",
                "momentum_classification",
                "momentum_label",
            ],
            "N/A",
        )
    )

    st.subheader(
        "Technical Context"
    )

    st.caption(
        "Live indicators supplied by the existing Technical Analysis Engine."
    )

    columns = st.columns(5)

    with columns[0]:
        st.metric(
            "RSI",
            (
                f"{rsi:.2f}"
                if rsi is not None
                else "N/A"
            ),
        )

    with columns[1]:
        st.metric(
            "MACD",
            (
                f"{macd:.2f}"
                if macd is not None
                else "N/A"
            ),
        )

    with columns[2]:
        st.metric(
            "Volume",
            (
                f"{volume_ratio:.2f}x"
                if volume_ratio is not None
                else "N/A"
            ),
        )

    with columns[3]:
        st.metric(
            "Trend",
            trend,
        )

    with columns[4]:
        st.metric(
            "Momentum",
            momentum,
        )


# ============================================================
# DECISION
# ============================================================

def render_decision(
    decision: Any,
) -> None:

    signal = safe_text(
        get_value(
            decision,
            ["signal"],
            "UNKNOWN",
        )
    )

    score = optional_float(
        get_value(
            decision,
            [
                "technical_score",
                "score",
            ],
        )
    )

    st.subheader(
        "Decision Intelligence"
    )

    left, right = st.columns(
        2
    )

    with left:

        if "BUY" in signal.upper():

            st.success(
                f"🟢 {signal.upper()}"
            )

        elif "SELL" in signal.upper() or (
            "REDUCE" in signal.upper()
        ):

            st.error(
                f"🔴 {signal.upper()}"
            )

        else:

            st.warning(
                signal.upper()
            )

        st.metric(
            "Technical Score",
            (
                f"{score:.0f} / 100"
                if score is not None
                else "N/A"
            ),
        )

    with right:

        st.info(
            "Decision Engine"
        )

        st.caption(
            "This score comes directly from the existing "
            "Technical Decision Engine."
        )

        st.caption(
            "News, insider activity and fair value do not "
            "modify this decision."
        )


def render_decision_components(
    decision: Any,
) -> None:

    mappings = {
        "Trend": "trend_score",
        "Momentum": "momentum_score",
        "MACD": "macd_score",
        "Volume": "volume_score",
        "Price Action": "price_action_score",
    }

    values = []

    for label, key in mappings.items():

        value = optional_float(
            get_value(
                decision,
                [key],
            )
        )

        if value is not None:
            values.append(
                (label, value)
            )

    if not values:
        return

    st.subheader(
        "Decision Components"
    )

    columns = st.columns(
        len(values)
    )

    for column, (
        label,
        value,
    ) in zip(
        columns,
        values,
    ):

        with column:

            st.metric(
                label,
                f"{value:.0f}",
            )


def render_reasons(
    decision: Any,
) -> None:

    reasons = get_value(
        decision,
        ["reasons"],
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
    ticker: str,
    data: pd.DataFrame,
) -> None:

    st.subheader(
        "Historical Backtest"
    )

    st.caption(
        "Existing backtesting engine. "
        "Historical results are not guarantees of future returns."
    )

    if BacktestEngine is None:

        st.info(
            "Backtesting engine is not available in this environment."
        )

        return

    try:

        engine = BacktestEngine()

        if hasattr(
            engine,
            "run",
        ):

            result = engine.run(
                data
            )

        else:

            st.info(
                "Backtesting engine does not expose run()."
            )

            return

        if not isinstance(
            result,
            dict,
        ):

            st.info(
                "No structured backtest result was returned."
            )

            return

        benchmark = result.get(
            "benchmark",
            {}
        )

        if not benchmark:
            benchmark = result

        cards = []

        for horizon in [
            "5D",
            "10D",
            "20D",
            "60D",
        ]:

            values = benchmark.get(
                horizon,
                {}
            )

            if not isinstance(
                values,
                dict,
            ):
                values = {}

            win_rate = values.get(
                "win_rate"
            )

            if win_rate is None:
                win_rate = result.get(
                    f"win_rate_{horizon.lower()}"
                )

            cards.append(
                (
                    horizon,
                    optional_float(
                        win_rate
                    ),
                )
            )

        columns = st.columns(4)

        for column, (
            horizon,
            win_rate,
        ) in zip(
            columns,
            cards,
        ):

            with column:

                st.metric(
                    f"{horizon} Win Rate",
                    (
                        f"{win_rate:.2f}%"
                        if win_rate is not None
                        else "N/A"
                    ),
                )

    except Exception as error:

        st.warning(
            "Backtest could not be displayed."
        )

        st.caption(
            safe_text(
                error
            )
        )


# ============================================================
# WATCHLIST
# ============================================================

def render_watchlist() -> None:

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
# EVIDENCE
# ============================================================

def render_evidence() -> None:

    st.subheader(
        "Evidence Research"
    )

    st.caption(
        "Research / validation only."
    )

    st.info(
        "The Evidence Model remains isolated from "
        "the production BUY / SELL Decision Engine."
    )

    st.warning(
        "Evidence is not automatically promoted into "
        "the production decision."
    )


# ============================================================
# SIDEBAR
# ============================================================

def render_sidebar() -> tuple[str, str]:

    with st.sidebar:

        logo_path = (
            Path(__file__).resolve().parent
            / "assets"
            / "haviquant_logo.png"
        )

        if logo_path.exists():
            st.image(
                str(logo_path),
                width=190,
            )

        else:
            st.title(
                "📈 HaViQuant"
            )

        st.caption(
            "TURN MARKET DATA INTO DECISIONS."
        )

        st.success(
            "● MARKET DATA ONLINE"
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
            index=[
                "Dashboard",
                "Stock Analysis",
                "Backtesting",
                "Evidence Research",
                "Watchlist",
            ].index(
                st.session_state.get(
                    "page",
                    "Dashboard",
                )
            ),
            key="hq_navigation",
        )

        ticker = st.text_input(
            "Ticker",
            value=st.session_state.ticker,
            max_chars=12,
            placeholder="NVDA",
        )

        ticker = (
            ticker.strip().upper()
        )

        if not ticker:
            ticker = DEFAULT_TICKER

        st.session_state.ticker = ticker
        st.session_state.page = page

        if st.button(
            "↻ Refresh Analysis",
            width="stretch",
        ):

            load_market_data.clear()
            run_analysis.clear()
            fetch_news.clear()
            fetch_insider_activity.clear()
            calculate_fair_value.clear()

            st.rerun()

        st.divider()

        st.caption(
            "Technical Decision Engine active"
        )

        st.caption(
            "News / Insider / Fair Value are independent intelligence."
        )

    return page, ticker


# ============================================================
# HEADER
# ============================================================

def render_header() -> None:

    left, right = st.columns(
        [7, 2],
        vertical_alignment="center",
    )

    with left:

        st.title(
            "HaViQuant"
        )

        st.caption(
            "Turn Market Data Into Decisions."
        )

    with right:

        st.success(
            "● MARKET DATA LIVE"
        )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    inject_theme()

    page, ticker = render_sidebar()

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
    # Analysis
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

        st.exception(
            error
        )

        return

    data = analysis["data"]

    normalized = normalize_market_dataframe(
        data
    )

    if normalized is None:

        st.error(
            "Market data could not be normalized."
        )

        return

    # --------------------------------------------------------
    # Stock summary
    # --------------------------------------------------------

    render_stock_summary(
        ticker,
        normalized,
    )

    # --------------------------------------------------------
    # PRICE CHART — TOP
    # --------------------------------------------------------

    render_price_chart(
        ticker,
        normalized,
    )

    # --------------------------------------------------------
    # INTELLIGENCE GRID
    #
    # Chart is already complete above.
    # These modules are independent.
    # --------------------------------------------------------

    news_col, fair_col = st.columns(
        [1, 1],
        gap="large",
    )

    with news_col:

        render_news_panel(
            ticker
        )

    with fair_col:

        render_fair_value_panel(
            ticker
        )

    insider_col, decision_col = st.columns(
        [1, 1],
        gap="large",
    )

    with insider_col:

        render_insider_panel(
            ticker
        )

    with decision_col:

        render_decision(
            analysis["decision"]
        )

        render_decision_components(
            analysis["decision"]
        )

    # --------------------------------------------------------
    # Technical
    # --------------------------------------------------------

    render_technical_metrics(
        analysis["technical"],
        analysis["decision"],
    )

    render_reasons(
        analysis["decision"]
    )

    # --------------------------------------------------------
    # Backtest
    # --------------------------------------------------------

    if page == "Backtesting":

        render_backtest(
            ticker,
            normalized,
        )

    else:

        with st.expander(
            "Historical Backtest",
            expanded=False,
        ):

            render_backtest(
                ticker,
                normalized,
            )

    st.divider()

    st.caption(
        "HaViQuant · Turn Market Data Into Decisions · "
        "Chart, News, Insider and Fair Value modules are independent."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
