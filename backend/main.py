from __future__ import annotations

import json
import math
import traceback
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Literal, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from backend.auth import (
    LoginRequest,
    TokenResponse,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from fastapi.middleware.cors import CORSMiddleware

from app.data.live_quotes import get_live_quote
from app.data.market_data import MarketDataService
from app.data.news_data import fetch_ticker_news
from app.analysis.technical_analysis import TechnicalAnalysisEngine
from app.analysis.decision_engine import DecisionEngine
from app.company.intelligence_engine import build_company_intelligence
from app.market_intelligence import scan_opportunities, macro_snapshot
from app.portfolio.portfolio_intelligence import (
    portfolio_rows, portfolio_doctor, analyze_ticker
)

app = FastAPI(
    title="HaViQuant Complete API",
    version="19.0.0",
    description="Complete API adapter over the existing HaViQuant intelligence engines."
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO_FILE = ROOT / "data" / "portfolio.json"
market = MarketDataService()
technical_engine = TechnicalAnalysisEngine()
decision_engine = DecisionEngine()


class TradePlannerRequest(BaseModel):
    capital: float = Field(gt=0)
    risk_profile: Literal["conservative", "balanced", "aggressive"] = "balanced"
    strategy: Literal["auto", "day_trade", "swing_trade", "position_trade", "long_term"] = "auto"
    trade_horizon: Optional[Literal["auto", "day", "swing", "position", "long_term", "day_trade", "swing_trade", "position_trade"]] = None
    holding_period: Optional[str] = None
    max_loss: Optional[float] = Field(default=None, ge=0)
    max_loss_amount: Optional[float] = Field(default=None, ge=0)
    max_loss_percent: Optional[float] = Field(default=None, ge=0, le=100)
    positions: Optional[int] = Field(default=None, ge=1, le=5)
    number_of_positions: int = Field(default=3, ge=1, le=5)
    allow_fractional_shares: bool = True
    cash_reserve_percent: Optional[float] = Field(default=None, ge=0, le=100)
    portfolio_aware: bool = False
    symbols: Optional[list[str]] = None
    sector: Optional[str] = None
    market: str = "US"

PERIOD_RE = "^(1d|5d|7d|1mo|3mo|6mo|60d|1y|2y|5y|10y|max)$"
INTERVAL_RE = "^(1m|2m|5m|15m|30m|60m|90m|1h|1d|5d|1wk|1mo|3mo)$"
MARKET_TAPE = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DOW": "^DJI",
    "VIX": "^VIX",
}
SCANNER_SECTORS = {
    "All": None,
    "AI / Semiconductors": ["NVDA", "AMD", "AVGO", "ARM", "MU", "TSM", "SMCI", "QCOM", "INTC"],
    "Software / Cloud": ["MSFT", "GOOGL", "META", "SNOW", "CRWD", "PANW", "NET", "DDOG", "NOW", "CRM"],
    "Biotech / Healthcare": ["MRNA", "PFE", "LLY", "NVO", "UNH", "VRTX", "REGN", "BIIB", "GILD", "BMY", "MRK"],
    "Space / Defense": ["RKLB", "BA", "LMT", "RTX", "NOC", "GE"],
    "EV / Mobility": ["TSLA", "RIVN", "LCID", "UBER", "ABNB", "CCL", "NCLH"],
    "Crypto / Fintech": ["COIN", "MARA", "RIOT", "HOOD", "SOFI", "AFRM", "UPST", "PYPL", "MSTR"],
    "Energy / Commodities": ["XOM", "CVX", "OXY", "URA", "CCJ", "FCX", "NEM", "SLV", "GLD", "XLE"],
    "Consumer / Internet": ["AMZN", "NFLX", "SHOP", "ROKU", "RBLX", "BABA", "PDD", "SE", "MELI"],
    "Financials": ["JPM", "GS", "XLF", "SQ", "PYPL", "HOOD", "SOFI"],
    "ETFs / Macro": ["SPY", "QQQ", "IWM", "TLT", "XBI", "XLE", "XLK", "XLF", "XLI", "XLY", "XLP", "XLV"],
}

def safe(v: Any):
    if v is None:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v) if np.isfinite(v) else None
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if isinstance(v, (np.ndarray,)):
        return [safe(x) for x in v.tolist()]
    if isinstance(v, pd.DataFrame):
        return [safe(x) for x in v.to_dict(orient="records")]
    if isinstance(v, pd.Series):
        return {str(k): safe(x) for k, x in v.to_dict().items()}
    if isinstance(v, dict):
        return {str(k): safe(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [safe(x) for x in v]
    return v

def history(ticker: str, period: str):
    ticker = ticker.strip().upper()
    if not ticker:
        raise ValueError("Ticker is required")
    return market.get_history(ticker, period=period)

def rows_from_df(df):
    return safe([
        {
            "date": i.isoformat(),
            "open": r["Open"], "high": r["High"], "low": r["Low"],
            "close": r["Close"], "volume": r["Volume"]
        }
        for i, r in df.iterrows()
    ])

def _num(value: Any):
    try:
        if value is None:
            return None
        n = float(value)
        return n if math.isfinite(n) else None
    except Exception:
        return None

def _first(*values):
    for value in values:
        if value not in (None, "", "N/A", "-"):
            return value
    return None

def _json_get(url: str):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 HaViQuant/1.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))

def _yahoo_summary(ticker: str) -> Dict[str, Any]:
    modules = ",".join([
        "price",
        "summaryDetail",
        "defaultKeyStatistics",
        "financialData",
        "assetProfile",
    ])
    url = (
        "https://query2.finance.yahoo.com/v10/finance/quoteSummary/"
        f"{urllib.parse.quote(ticker.upper())}?modules={modules}"
    )
    try:
        data = _json_get(url)
        result = ((data.get("quoteSummary") or {}).get("result") or [{}])[0]
        price = result.get("price") or {}
        detail = result.get("summaryDetail") or {}
        stats = result.get("defaultKeyStatistics") or {}
        financial = result.get("financialData") or {}
        profile = result.get("assetProfile") or {}
        value = lambda obj, key: ((obj.get(key) or {}).get("raw") if isinstance(obj.get(key), dict) else obj.get(key))
        return {
            "name": _first(price.get("longName"), price.get("shortName")),
            "sector": profile.get("sector"),
            "industry": profile.get("industry"),
            "employees": _num(profile.get("fullTimeEmployees")),
            "description": profile.get("longBusinessSummary"),
            "market_cap": _num(value(price, "marketCap") or value(stats, "marketCap")),
            "shares_outstanding": _num(value(stats, "sharesOutstanding")),
            "trailing_pe": _num(value(detail, "trailingPE")),
            "forward_pe": _num(value(stats, "forwardPE")),
            "profit_margin": _num(value(financial, "profitMargins")),
            "roe": _num(value(financial, "returnOnEquity")),
            "revenue_growth": _num(value(financial, "revenueGrowth")),
            "beta": _num(value(stats, "beta")),
            "dividend_yield": _num(value(detail, "dividendYield")),
            "trailing_eps": _num(value(stats, "trailingEps")),
            "source": "Yahoo Finance quoteSummary",
        }
    except Exception as exc:
        return {"error": str(exc)}

def _history_with_interval(ticker: str, period: str, interval: str):
    try:
        import yfinance as yf
        df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=False)
        if df is not None and not df.empty:
            return df
    except Exception:
        pass
    return history(ticker, "1y" if period not in {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"} else period)

def _sma(series, window: int):
    return _num(series.tail(window).mean()) if len(series) >= window else None

def _rsi(close, window: int = 14):
    if len(close) <= window:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = -delta.clip(upper=0).rolling(window).mean()
    rs = gain / loss.replace(0, np.nan)
    return _num((100 - (100 / (1 + rs))).iloc[-1])

def _analysis_payload(ticker: str, period: str, interval: str, include_mtf: bool = False):
    df = _history_with_interval(ticker, period, interval)
    if df is None or df.empty:
        raise ValueError(f"No market data found for {ticker}.")
    df = df.dropna(subset=["Open", "High", "Low", "Close"]).sort_index()
    close = pd.to_numeric(df["Close"], errors="coerce").dropna()
    volume = pd.to_numeric(df["Volume"], errors="coerce").fillna(0)
    quote_data = {}
    try:
        quote_data = get_live_quote(ticker)
    except Exception:
        quote_data = {}
    price = _first(_num(quote_data.get("price")), _num(close.iloc[-1]))
    previous = _first(_num(quote_data.get("previous")), _num(close.iloc[-2]) if len(close) > 1 else None)
    change_pct = _first(_num(quote_data.get("change_pct")), ((price / previous - 1) * 100 if price and previous else None))
    typical = (pd.to_numeric(df["High"], errors="coerce") + pd.to_numeric(df["Low"], errors="coerce") + pd.to_numeric(df["Close"], errors="coerce")) / 3
    recent_volume = volume.tail(78)
    recent_typical = typical.tail(78)
    vwap = _num((recent_typical * recent_volume).sum() / recent_volume.sum()) if recent_volume.sum() else None
    sma20 = _sma(close, 20)
    sma50 = _sma(close, 50)
    sma200 = _sma(close, 200)
    vol_avg = _num(volume.tail(60).mean())
    vol_last = _num(volume.iloc[-1])
    volume_ratio = vol_last / vol_avg if vol_last and vol_avg else None
    support = _num(pd.to_numeric(df["Low"], errors="coerce").tail(40).min())
    resistance = _num(pd.to_numeric(df["High"], errors="coerce").tail(40).max())
    tech = {}
    dec = {}
    try:
        tech = technical_engine.analyze(df)
        dec = decision_engine.evaluate(tech)
    except Exception:
        pass
    signal = _first(dec.get("signal"), "WAIT" if price and sma20 else None)
    setup_quality = _first(_num(dec.get("score")), _num(dec.get("technical_score")))
    levels = {
        "entry": price,
        "stop": support,
        "target1": resistance,
        "target2": (price + (resistance - support)) if price and support and resistance and resistance > support else None,
    }
    return safe({
        "ticker": ticker.upper(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "quote": quote_data,
        "price": price,
        "previous": previous,
        "change_pct": change_pct,
        "candles": rows_from_df(df.tail(220)),
        "sma_20": _first(tech.get("sma_20"), tech.get("sma20"), sma20),
        "sma_50": _first(tech.get("sma_50"), tech.get("sma50"), sma50),
        "sma_200": _first(tech.get("sma_200"), tech.get("sma200"), sma200),
        "vwap": _first(tech.get("vwap"), vwap),
        "volume": vol_last,
        "volume_ratio": _first(tech.get("volume_ratio"), tech.get("volumeRatio"), volume_ratio),
        "rsi": _first(tech.get("rsi"), tech.get("RSI"), _rsi(close)),
        "macd": tech.get("macd"),
        "macd_signal": tech.get("macd_signal"),
        "atr": tech.get("atr"),
        "trend": _first(tech.get("trend"), dec.get("trend")),
        "momentum": _first(tech.get("momentum"), dec.get("momentum")),
        "signal": signal,
        "setup_quality": setup_quality,
        "support": support,
        "resistance": resistance,
        "levels": levels,
        "mtf": [] if include_mtf else None,
    })

def _fundamental_payload(ticker: str, error: Optional[str] = None):
    summary = _yahoo_summary(ticker)
    quote_data = {}
    try:
        quote_data = get_live_quote(ticker)
    except Exception:
        pass
    price = _num(quote_data.get("price"))
    shares = _num(summary.get("shares_outstanding"))
    market_cap = _first(_num(summary.get("market_cap")), price * shares if price and shares else None)
    return safe({
        "ticker": ticker.upper(),
        "provider_status": "PARTIAL" if error else "OK",
        "provider_error": error,
        "live_quote": quote_data,
        "profile": {
            "name": summary.get("name"),
            "sector": summary.get("sector"),
            "industry": summary.get("industry"),
            "employees": summary.get("employees"),
            "description": summary.get("description"),
            "market_cap": market_cap,
            "trailing_pe": summary.get("trailing_pe"),
            "forward_pe": summary.get("forward_pe"),
            "profit_margin": summary.get("profit_margin"),
            "roe": summary.get("roe"),
            "revenue_growth": summary.get("revenue_growth"),
        },
        "valuation": {
            "trailing_pe": summary.get("trailing_pe"),
            "forward_pe": summary.get("forward_pe"),
        },
        "growth": {
            "revenue_growth": summary.get("revenue_growth"),
        },
        "profitability": {
            "profit_margin": summary.get("profit_margin"),
            "roe": summary.get("roe"),
        },
        "earnings": {
            "trailing_eps": summary.get("trailing_eps"),
        },
        "beta": summary.get("beta"),
        "dividend_yield": summary.get("dividend_yield"),
        "source": summary.get("source") if summary.get("market_cap") else None,
    })

def _history_quote_row(symbol: str, label: str | None = None):
    try:
        import yfinance as yf
        df = yf.Ticker(symbol).history(period="5d", interval="1d", auto_adjust=False)
        if df is None or df.empty:
            return None
        df = df.dropna(subset=["Close"]).sort_index()
        if df.empty:
            return None
        close = pd.to_numeric(df["Close"], errors="coerce").dropna()
        if close.empty:
            return None
        price = _num(close.iloc[-1])
        previous = _num(close.iloc[-2]) if len(close) > 1 else None
        change_pct = ((price / previous - 1) * 100) if price and previous else None
        volume = _num(pd.to_numeric(df.get("Volume", pd.Series(dtype=float)), errors="coerce").fillna(0).iloc[-1])
        return {
            "symbol": label or symbol,
            "ticker": symbol,
            "price": price,
            "change_pct": _num(change_pct),
            "volume": volume,
            "source": "Yahoo Finance history",
        }
    except Exception:
        return None

def _quote_row(symbol: str, label: str | None = None):
    try:
        quote_data = get_live_quote(symbol)
        price = _num(quote_data.get("price"))
        if price is not None:
            return {
                "symbol": label or symbol,
                "ticker": symbol,
                "price": price,
                "change_pct": _num(quote_data.get("change_pct")),
                "volume": _num(quote_data.get("volume")),
                "source": quote_data.get("source"),
            }
    except Exception:
        pass
    return _history_quote_row(symbol, label)

def _market_macro_payload(ticker: str):
    tape = [row for label, symbol in MARKET_TAPE.items() if (row := _quote_row(symbol, label))]
    quoted = _quote_row(ticker.upper())
    universe = sorted({
        symbol
        for symbols in SCANNER_SECTORS.values()
        if symbols
        for symbol in symbols
    })
    movers = [row for symbol in universe if (row := _quote_row(symbol))]
    gainers = sorted(
        [row for row in movers if row.get("change_pct") is not None],
        key=lambda row: row["change_pct"],
        reverse=True,
    )[:12]
    most_active = sorted(
        [row for row in movers if row.get("volume") is not None],
        key=lambda row: row["volume"],
        reverse=True,
    )[:12] or gainers
    scores = [
        row["change_pct"]
        for row in tape
        if row.get("ticker") != "^VIX" and row.get("change_pct") is not None
    ]
    avg = sum(scores) / len(scores) if scores else None
    sentiment = None
    if avg is not None:
        sentiment = {
            "score": max(0, min(100, 50 + avg * 8)),
            "label": "Bullish" if avg > 0.35 else "Bearish" if avg < -0.35 else "Mixed",
            "bullish_pct": 100 if avg > 0 else 0,
            "neutral_pct": 100 if abs(avg) <= 0.35 else 0,
            "bearish_pct": 100 if avg < 0 else 0,
        }
    events = []
    try:
        events = fetch_ticker_news(ticker, 12)
    except Exception:
        pass
    macro_data = {}
    try:
        macro_data = macro_snapshot()
    except Exception:
        pass
    return safe({
        "ticker": ticker.upper(),
        "quote": quoted,
        "market_indices": tape,
        "top_movers": {"items": gainers, "gainers": gainers, "most_active": most_active},
        "sentiment": sentiment,
        "events": events,
        "macro": macro_data,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })

def _fallback_scanner_items(symbols: list[str] | None, limit: int):
    universe = symbols or [
        "NVDA", "AMD", "AVGO", "MSFT", "AAPL", "GOOGL", "META", "AMZN", "TSLA",
        "CRWD", "PANW", "NET", "DDOG", "NOW", "SHOP", "MSTR", "COIN", "LLY",
        "JPM", "XOM",
    ]
    items = []
    for symbol in universe[: max(limit * 2, limit)]:
        try:
            analysis = _analysis_payload(symbol, "3mo", "1d")
        except Exception:
            continue
        price = _num(analysis.get("price"))
        change_pct = _num(analysis.get("change_pct"))
        volume_ratio = _num(analysis.get("volume_ratio"))
        rsi = _num(analysis.get("rsi"))
        sma20 = _num(analysis.get("sma_20"))
        sma50 = _num(analysis.get("sma_50"))
        score_parts = [
            20 if change_pct and change_pct > 0 else 0,
            20 if volume_ratio and volume_ratio >= 1.4 else 0,
            20 if price and sma20 and price > sma20 else 0,
            20 if sma20 and sma50 and sma20 > sma50 else 0,
            20 if rsi and 45 <= rsi <= 75 else 0,
        ]
        score = sum(score_parts)
        confirmation = []
        if price and sma20 and price > sma20:
            confirmation.append(f"Price above 20-day average ({sma20:.2f}).")
        if volume_ratio and volume_ratio >= 1.4:
            confirmation.append(f"Volume running {volume_ratio:.2f}x recent average.")
        if rsi and 45 <= rsi <= 75:
            confirmation.append(f"RSI is in tradable range ({rsi:.1f}).")
        risk_watch = []
        if rsi and rsi > 75:
            risk_watch.append(f"RSI elevated ({rsi:.1f}).")
        if price and sma20 and price < sma20:
            risk_watch.append(f"Price below 20-day average ({sma20:.2f}).")
        items.append({
            "ticker": symbol,
            "sector": None,
            "signal": "LONG" if score >= 60 else "WAIT",
            "score": score,
            "price": price,
            "change_pct": change_pct,
            "estimated_target_price": analysis.get("resistance"),
            "estimated_bullish_timeframe": "Provider technical scan",
            "risk_reward": None,
            "why": confirmation,
            "confirmation": confirmation,
            "risk_watch": risk_watch,
            "articles": [],
        })
    return sorted(items, key=lambda row: row.get("score") or 0, reverse=True)[:limit]

def core_analysis(ticker: str, period: str = "1y"):
    df = history(ticker, period)
    technical = technical_engine.analyze(df)
    decision = decision_engine.evaluate(technical)
    quote = get_live_quote(ticker)
    return df, quote, technical, decision

@app.get("/api/v1/health")
def health():
    return {
        "status": "ok",
        "service": "haviquant-api",
        "version": "13.0.0",
        "engines": "CONNECTED",
        "modules": [
            "market", "technical", "fundamental", "decision",
            "company", "portfolio", "risk", "news",
            "evidence", "research-3.8", "research-3.9", "research-3.9.1"
        ]
    }

@app.get("/api/v1/quote/{ticker}")
def quote(ticker: str):
    try:
        return safe(get_live_quote(ticker))
    except Exception as e:
        raise HTTPException(502, str(e))

@app.get("/api/v1/history/{ticker}")
def history_api(ticker: str, period: str = Query("1y", pattern=PERIOD_RE)):
    try:
        return {"ticker": ticker.upper(), "period": period, "rows": rows_from_df(history(ticker, period))}
    except Exception as e:
        raise HTTPException(502, str(e))

@app.get("/api/v1/technical/{ticker}")
def technical(ticker: str, period: str = Query("1y", pattern=PERIOD_RE)):
    try:
        df, quote, tech, dec = core_analysis(ticker, period)
        tech_out = dict(tech or {})
        # Canonical aliases for web/mobile clients. Preserve the original
        # engine keys; aliases do not change calculations.
        for src_key, alias in [
            ("sma_5","sma5"),("sma_10","sma10"),("sma_20","sma20"),
            ("sma_50","sma50"),("sma_200","sma200"),
            ("macd_signal","macdSignal"),("macd_histogram","macdHistogram"),
            ("volume_ratio","volumeRatio")
        ]:
            if alias not in tech_out:
                tech_out[alias] = tech_out.get(src_key)
        decision_out = dict(dec or {})
        if "technical_score" not in decision_out:
            decision_out["technical_score"] = decision_out.get("score")
        return safe({
            "ticker": ticker.upper(), "quote": quote,
            "technical": tech_out, "decision": decision_out
        })
    except Exception as e:
        raise HTTPException(502, str(e))

@app.get("/api/v1/fundamental/{ticker}")
def fundamental(ticker: str, quarters: int = 10):
    try:
        result = build_company_intelligence(ticker, quarters=max(1, min(int(quarters), 20)))
        profile = result.get("profile") or {}
        scores = result.get("scores") or {}
        earnings = result.get("earnings") or {}
        # Compatibility adapter: expose the canonical engine fields plus
        # stable aliases expected by web/mobile clients. No values are
        # invented; aliases point to existing engine outputs.
        valuation = result.get("valuation") or {}
        return safe({
            "ticker": ticker.upper(),
            "profile": {
                **profile,
                "description": profile.get("description") or profile.get("summary"),
            },
            "live_quote": result.get("live_quote"),
            "scores": {
                **scores,
                "fundamental_score": scores.get("fundamental_score")
                    if scores.get("fundamental_score") is not None
                    else scores.get("overall_company_score"),
                "fundamental": scores.get("fundamental")
                    if scores.get("fundamental") is not None
                    else scores.get("overall_company_score"),
                "overall": scores.get("overall")
                    if scores.get("overall") is not None
                    else scores.get("overall_company_score"),
            },
            "valuation": valuation,
            "earnings": earnings,
            "profitability": {
                "profit_margin": (
                    profile.get("profit_margin")
                    if profile.get("profit_margin") is not None
                    else None
                ),
                "roe": profile.get("roe"),
            },
            "growth": {
                "revenue_growth": profile.get("revenue_growth"),
                "earnings_growth": earnings.get("earnings_growth_pct"),
            },
            "quarters": result.get("quarters"),
            "products_demand": result.get("products_demand"),
            "backlog": result.get("backlog"),
            "competition": result.get("competition"),
            "risks": result.get("risks"),
            "governance_ethics": result.get("governance_ethics"),
            "research_status": result.get("research_status"),
            "sources": result.get("sources"),
        })
    except Exception as e:
        return _fundamental_payload(ticker, str(e))

@app.get("/api/v1/decision/{ticker}")
def decision(ticker: str):
    try:
        _, quote, tech, dec = core_analysis(ticker, "1y")
        return safe({"ticker": ticker.upper(), "quote": quote, "technical": tech, "decision": dec})
    except Exception as e:
        raise HTTPException(502, str(e))

@app.get("/api/v1/dashboard/{ticker}")
def dashboard(ticker: str, period: str = Query("1y", pattern=PERIOD_RE)):
    try:
        df, quote, tech, dec = core_analysis(ticker, period)
        return safe({
            "ticker": ticker.upper(),
            "quote": quote,
            "technical": tech,
            "decision": dec,
            "chart": rows_from_df(df.tail(1200)),
        })
    except Exception as e:
        raise HTTPException(502, str(e))

@app.get("/api/v1/company/{ticker}")
def company(ticker: str, quarters: int = 10):
    try:
        return safe(build_company_intelligence(ticker, quarters=quarters))
    except Exception as e:
        return _fundamental_payload(ticker, str(e))

@app.get("/api/v1/company-intelligence/{ticker}")
def company_intelligence_alias(ticker: str, quarters: int = 10):
    return company(ticker, quarters)

@app.get("/api/v1/news/{ticker}")
def news(ticker: str, limit: int = 12):
    try:
        return {
            "ticker": ticker.upper(),
            "items": safe(fetch_ticker_news(ticker, max(1, min(limit, 30))))
        }
    except Exception as e:
        return {"ticker": ticker.upper(), "items": [], "error": str(e)}

@app.get("/api/v1/market/news")
def market_news(ticker: str = "NVDA", limit: int = 12):
    return news(ticker, limit)

@app.get("/api/v1/market/analysis")
def market_analysis(
    ticker: str = "NVDA",
    period: str = Query("60d", pattern=PERIOD_RE),
    interval: str = Query("5m", pattern=INTERVAL_RE),
    include_mtf: bool = False,
):
    try:
        return _analysis_payload(ticker.strip().upper(), period, interval, include_mtf)
    except Exception as e:
        raise HTTPException(502, str(e))

@app.get("/api/v1/market/macro")
def market_macro(ticker: str = "NVDA"):
    return _market_macro_payload(ticker)

@app.get("/api/v1/market/insiders")
def market_insiders(ticker: str = "NVDA"):
    try:
        result = build_company_intelligence(ticker, quarters=4)
        stock_level = result.get("stock_level") or {}
        holders = []
        for key in [
            "insidersPercentHeld",
            "institutionsPercentHeld",
            "institutionsFloatPercentHeld",
            "institutionsCount",
        ]:
            if stock_level.get(key) is not None:
                holders.append({"label": key, "value": stock_level.get(key)})
        return safe({"ticker": ticker.upper(), "items": [], "holders": holders})
    except Exception as e:
        return {"ticker": ticker.upper(), "items": [], "holders": [], "error": str(e)}

@app.get("/api/v1/market/trade-scanner")
def market_trade_scanner(limit: int = 50, sector: str = "All"):
    selected = SCANNER_SECTORS.get(sector) or SCANNER_SECTORS["All"]
    try:
        results = scan_opportunities(universe=selected, limit=max(1, min(int(limit), 50)))
        items = []
        for row in results:
            if row.get("error"):
                continue
            plan = row.get("trade_plan") or {}
            items.append({
                "ticker": row.get("ticker"),
                "sector": row.get("sector"),
                "signal": row.get("signal"),
                "score": row.get("score"),
                "price": row.get("price"),
                "change_pct": row.get("change_pct"),
                "estimated_target_price": plan.get("target"),
                "estimated_bullish_timeframe": plan.get("timeframe"),
                "risk_reward": row.get("risk_reward"),
                "why": [
                    value for value in [
                        f"Technical score {row.get('technical_score'):.0f}" if row.get("technical_score") is not None else None,
                        f"Historical win rate {row.get('historical_win_rate'):.1f}%" if row.get("historical_win_rate") is not None else None,
                        f"Risk/reward {row.get('risk_reward'):.2f}" if row.get("risk_reward") is not None else None,
                    ] if value
                ],
                "confirmation": [],
                "risk_watch": [],
                "articles": [],
            })
        return safe({
            "sector": sector,
            "sectors": list(SCANNER_SECTORS.keys()),
            "universe_size": len(selected) if selected else len(results),
            "items": items,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "method": "Ranks provider-returned symbols with the existing technical and decision engines.",
            "disclaimer": "Research signal only. This does not guarantee price movement.",
        })
    except Exception as e:
        items = _fallback_scanner_items(selected, max(1, min(int(limit), 50)))
        return safe({
            "sector": sector,
            "sectors": list(SCANNER_SECTORS.keys()),
            "universe_size": len(selected) if selected else len(items),
            "items": items,
            "engine_error": str(e),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "method": "Ranks provider-returned chart data when the scanner engine is unavailable.",
            "disclaimer": "Research signal only. This does not guarantee price movement.",
        })


RISK_PROFILES = {
    "conservative": {"reserve": 45, "min_score": 70, "risk": .006},
    "balanced": {"reserve": 25, "min_score": 60, "risk": .012},
    "aggressive": {"reserve": 10, "min_score": 52, "risk": .02},
}
COMPOSITE_SCORE_WEIGHTS = {
    "technical": .22,
    "momentum": .14,
    "trend": .12,
    "volume": .10,
    "fundamental": .12,
    "market_regime": .12,
    "risk_reward": .18,
}


def _bounded(value: Any, lo: float = 0, hi: float = 100) -> float:
    n = _num(value)
    return max(lo, min(hi, n if n is not None else lo))


def _weighted_score(components: Dict[str, Any], weights: Dict[str, float]) -> float:
    available = {
        key: float(value)
        for key, value in components.items()
        if value is not None and math.isfinite(float(value))
    }
    total = sum(weights.get(key, 0) for key in available)
    if total <= 0:
        return 0
    return round(sum(available[key] * weights.get(key, 0) for key in available) / total, 1)


def _trend_component(label: Any, price: Any = None, sma20: Any = None, sma50: Any = None) -> float:
    text = str(label or "").lower()
    if "bull" in text:
        return 78
    if "bear" in text:
        return 24
    p, s20, s50 = _num(price), _num(sma20), _num(sma50)
    if p and s20 and s50:
        if p > s20 > s50:
            return 76
        if p < s20 < s50:
            return 28
    return 50


def _strategy(value: Any) -> str:
    return {
        "auto": "auto",
        "day": "day_trade",
        "day_trade": "day_trade",
        "swing": "swing_trade",
        "swing_trade": "swing_trade",
        "position": "position_trade",
        "position_trade": "position_trade",
        "long_term": "long_term",
    }.get(str(value or "auto"), "auto")


def _planner_positions(req: TradePlannerRequest) -> int:
    return max(1, min(5, int(req.positions or req.number_of_positions or 3)))


def _planner_max_loss(req: TradePlannerRequest, profile: Dict[str, float]) -> float:
    loss = req.max_loss if req.max_loss is not None else req.max_loss_amount
    if loss is None:
        loss = req.capital * ((req.max_loss_percent or (profile["risk"] * 100)) / 100)
    if loss > req.capital:
        raise HTTPException(422, "max_loss cannot exceed capital")
    return max(0, float(loss))


def planner_market_regime(seed_ticker: str = "SPY"):
    macro = _market_macro_payload(seed_ticker or "SPY")
    sentiment = macro.get("sentiment") or {}
    label = sentiment.get("label") or "Mixed"
    score = _bounded(sentiment.get("score"), 0, 100) if sentiment else 50
    return safe({
        "label": "neutral_bullish" if label == "Bullish" else "risk_off" if label == "Bearish" else "neutral",
        "score": score,
        "regime": "risk_on" if label == "Bullish" else "risk_off" if label == "Bearish" else "neutral",
        "trend": str(label).lower(),
        "volatility": "normal",
        "confidence": max(45, min(85, 50 + abs(score - 50))),
        "summary": f"Market regime is {label} based on production macro/index data.",
        "evidence": macro.get("market_indices") or [],
        "market_data_as_of": macro.get("updated_at") or datetime.now(timezone.utc).isoformat(),
    })


def _fundamental_component(data: Dict[str, Any]) -> tuple[Optional[float], list[Dict[str, Any]]]:
    profile = data.get("profile") or {}
    valuation = data.get("valuation") or {}
    profitability = data.get("profitability") or {}
    growth = data.get("growth") or {}
    evidence = []
    scores = []
    pe = _num(_first(valuation.get("forward_pe"), profile.get("forward_pe"), valuation.get("trailing_pe"), profile.get("trailing_pe")))
    revenue_growth = _num(_first(growth.get("revenue_growth"), profile.get("revenue_growth")))
    margin = _num(_first(profitability.get("profit_margin"), profile.get("profit_margin")))
    roe = _num(_first(profitability.get("roe"), profile.get("roe")))
    if pe:
        scores.append(76 if pe <= 25 else 62 if pe <= 45 else 42)
        evidence.append({"metric": "P/E", "value": pe})
    if revenue_growth is not None:
        scores.append(78 if revenue_growth >= .12 else 58 if revenue_growth >= 0 else 35)
        evidence.append({"metric": "Revenue growth", "value": revenue_growth})
    if margin is not None:
        scores.append(76 if margin >= .18 else 56 if margin >= .05 else 36)
        evidence.append({"metric": "Profit margin", "value": margin})
    if roe is not None:
        scores.append(74 if roe >= .15 else 55 if roe >= .05 else 35)
        evidence.append({"metric": "ROE", "value": roe})
    return (round(sum(scores) / len(scores), 1), evidence) if scores else (None, evidence)


def planner_candidate(symbol: str, market_regime: Dict[str, Any], strategy: str):
    analysis = _analysis_payload(symbol, "6mo", "1d", False)
    fundamental_data = fundamental(symbol, quarters=8)
    price = _num(_first(analysis.get("price"), (analysis.get("quote") or {}).get("price")))
    if not price:
        raise ValueError("No usable price returned")
    levels = analysis.get("levels") or {}
    support = _num(_first(levels.get("stop"), analysis.get("support")))
    resistance = _num(_first(levels.get("target1"), analysis.get("resistance")))
    target2 = _num(levels.get("target2"))
    atr = _num(analysis.get("atr"))
    stop = support if support and support < price else price - (atr if atr else max(price * .015, 0.01))
    target1 = resistance if resistance and resistance > price else price + ((atr * 1.6) if atr else max(price * .02, 0.01))
    if not target2 or target2 <= target1:
        target2 = target1 + max(target1 - price, price - stop)
    risk_per_share = max(0, price - stop)
    reward_per_share = max(0, target1 - price)
    reward_risk = reward_per_share / risk_per_share if risk_per_share else None
    rsi = _num(analysis.get("rsi"))
    volume_ratio = _num(analysis.get("volume_ratio"))
    tech_score = _bounded(_first(analysis.get("setup_quality"), (analysis.get("decision") or {}).get("technical_score"), 50))
    momentum_score = _bounded(50 + ((rsi or 50) - 50) * .9)
    trend_score = _trend_component(analysis.get("trend"), price, analysis.get("sma_20"), analysis.get("sma_50"))
    volume_score = _bounded(50 + ((volume_ratio or 1) - 1) * 18)
    fund_score, fund_evidence = _fundamental_component(fundamental_data)
    market_score = _bounded(market_regime.get("score"), 0, 100)
    risk_reward_score = _bounded((reward_risk or 0) * 32)
    score_breakdown = {
        "technical": tech_score,
        "momentum": momentum_score,
        "trend": trend_score,
        "volume": volume_score,
        "fundamental": fund_score,
        "market_regime": market_score,
        "risk_reward": risk_reward_score if reward_risk else None,
    }
    havi_score = _weighted_score(score_breakdown, COMPOSITE_SCORE_WEIGHTS)
    chosen_strategy = strategy if strategy != "auto" else (
        "day_trade" if volume_score >= 72 and momentum_score >= 58 else
        "position_trade" if (fund_score or 0) >= 70 and trend_score >= 60 else
        "swing_trade"
    )
    confidence = _weighted_score(
        {"havi": havi_score, "technical": tech_score, "risk_reward": risk_reward_score, "market": market_score},
        {"havi": .45, "technical": .2, "risk_reward": .2, "market": .15},
    )
    unavailable = [key for key, value in score_breakdown.items() if value is None]
    why_selected = [
        f"Technical setup score is {round(tech_score, 1)}.",
        f"Trend score is {round(trend_score, 1)} and momentum score is {round(momentum_score, 1)}.",
        f"Reward/risk is {round(reward_risk, 2)} from production support/resistance levels." if reward_risk else "Reward/risk could not be confirmed.",
    ]
    return safe({
        "ticker": symbol.upper(),
        "company": (fundamental_data.get("profile") or {}).get("name") or symbol.upper(),
        "sector": (fundamental_data.get("profile") or {}).get("sector"),
        "current_price": price,
        "entry": price,
        "entry_low": price - (atr * .2 if atr else 0),
        "entry_high": price + (atr * .2 if atr else 0),
        "stop_loss": stop,
        "stop": stop,
        "target_1": target1,
        "target_2": target2,
        "risk_per_share": risk_per_share,
        "reward_per_share": reward_per_share,
        "risk_reward": reward_risk,
        "reward_risk_ratio": reward_risk,
        "havi_score": havi_score,
        "selected_score": havi_score,
        "confidence": confidence,
        "score_breakdown": score_breakdown,
        "strategy": chosen_strategy,
        "selected_horizon": chosen_strategy.replace("_trade", ""),
        "horizon_reason": "Selected from production technical, volume, fundamental, and market-regime scores.",
        "why_selected": why_selected,
        "bull_case": why_selected,
        "risk_factors": ["Optional data missing: " + ", ".join(unavailable)] if unavailable else [],
        "invalidation_reason": f"Break below {round(stop, 2)} invalidates this long setup.",
        "data_quality": "partial" if unavailable else "good",
        "unavailable_components": unavailable,
        "evidence": {
            "technical": {"score": tech_score, "status": analysis.get("trend")},
            "volume": {"score": volume_score, "status": f"{round(volume_ratio, 2)}x average" if volume_ratio else "Not returned"},
            "fundamental": {"score": fund_score, "status": "provider_backed" if fund_evidence else "limited_data", "evidence": fund_evidence},
            "market_regime": {"score": market_score, "status": market_regime.get("regime")},
        },
        "win_probability": None,
        "expected_return": reward_per_share / price if price else None,
    })


def build_trade_planner_response(req: TradePlannerRequest):
    profile = RISK_PROFILES[req.risk_profile]
    strategy = _strategy(req.trade_horizon or req.strategy)
    max_loss = _planner_max_loss(req, profile)
    requested_positions = _planner_positions(req)
    sector = urllib.parse.unquote(req.sector or "All")
    symbols = req.symbols
    if not symbols:
        scan = market_trade_scanner(limit=20, sector=sector)
        symbols = [row.get("ticker") for row in scan.get("items", []) if row.get("ticker")]
    symbols = [str(symbol).strip().upper() for symbol in (symbols or []) if str(symbol).strip()][:20]
    market_regime = planner_market_regime(symbols[0] if symbols else "SPY")
    candidates = []
    rejected = []
    for symbol in symbols:
        try:
            candidate = planner_candidate(symbol, market_regime, strategy)
            if (candidate.get("havi_score") or 0) >= profile["min_score"] and (candidate.get("risk_reward") or 0) >= 1:
                candidates.append(candidate)
            else:
                rejected.append({"ticker": symbol, "reason": "Below planner score or reward/risk threshold", "score": candidate.get("havi_score"), "risk_reward": candidate.get("risk_reward")})
        except Exception as exc:
            rejected.append({"ticker": symbol, "reason": str(exc)})
    candidates.sort(key=lambda row: (row.get("havi_score") or 0, row.get("risk_reward") or 0, row.get("confidence") or 0), reverse=True)
    selected = candidates[:requested_positions]
    reserve_pct = req.cash_reserve_percent if req.cash_reserve_percent is not None else profile["reserve"]
    deployable = req.capital * (1 - reserve_pct / 100)
    if not selected:
        return safe({
            "request": req.model_dump(),
            "planner_mode": "full",
            "decision": "WAIT",
            "decision_reason": "No candidate passed planner quality and reward/risk filters.",
            "summary": "No planner opportunities passed the current quality filters.",
            "market_regime": market_regime,
            "recommendations": [],
            "allocation": {"allocated_capital": 0, "cash_reserve": req.capital, "positions": []},
            "cash_reserve": req.capital,
            "planned_risk": 0,
            "potential_profit_at_target": 0,
            "expected_value": None,
            "maximum_expected_loss": 0,
            "confidence": market_regime.get("confidence"),
            "rejected_candidates": rejected[:12],
            "warnings": ["WAIT is valid when live evidence is incomplete or unattractive."],
        })
    per_position = deployable / len(selected)
    positions_out = []
    total_risk = 0
    total_profit = 0
    for candidate in selected:
        price = float(candidate.get("entry") or 0)
        risk_per_share = float(candidate.get("risk_per_share") or 0)
        raw_shares = per_position / price if price else 0
        risk_shares = (max_loss / len(selected)) / risk_per_share if risk_per_share else raw_shares
        shares = min(raw_shares, risk_shares)
        if not req.allow_fractional_shares:
            shares = math.floor(shares)
        capital_allocated = shares * price
        possible_loss = shares * risk_per_share
        potential_profit = shares * max(0, float(candidate.get("target_1") or price) - price)
        total_risk += possible_loss
        total_profit += potential_profit
        positions_out.append(safe({
            **candidate,
            "rank": len(positions_out) + 1,
            "shares": shares,
            "capital": capital_allocated,
            "capital_allocation": capital_allocated,
            "potential_loss_at_stop": possible_loss,
            "potential_profit_at_target": potential_profit,
            "expected_value": None,
            "rank_reason": f"Ranks #{len(positions_out) + 1} by HaVi score, reward/risk, and confidence.",
        }))
    allocated = sum(item.get("capital_allocation") or 0 for item in positions_out)
    average_score = sum(float(item.get("havi_score") or 0) for item in positions_out) / len(positions_out)
    decision = "BUY" if market_regime.get("regime") == "risk_on" and average_score >= 72 else "REVIEW"
    return safe({
        "request": req.model_dump(),
        "planner_mode": "full",
        "decision": decision,
        "decision_reason": f"{len(positions_out)} setup{'s' if len(positions_out) != 1 else ''} passed planner filters.",
        "summary": "Planner used production scanner, market analysis, fundamentals, support/resistance, and risk constraints.",
        "market_regime": market_regime,
        "recommendations": positions_out,
        "allocation": {"allocated_capital": allocated, "cash_reserve": max(0, req.capital - allocated), "positions": positions_out},
        "cash_reserve": max(0, req.capital - allocated),
        "planned_risk": total_risk,
        "potential_profit_at_target": total_profit,
        "expected_profit": total_profit,
        "expected_value": None,
        "maximum_expected_loss": total_risk,
        "confidence": round(sum(float(item.get("confidence") or 0) for item in positions_out) / len(positions_out), 1),
        "rejected_candidates": rejected[:12],
        "warnings": [],
        "data_timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.post("/api/v1/planner/analyze")
def planner_analyze(req: TradePlannerRequest):
    return build_trade_planner_response(req)


@app.post("/api/v1/trade-planner/analyze")
def trade_planner_analyze(req: TradePlannerRequest):
    return build_trade_planner_response(req)


@app.get("/api/v1/market/geopolitics")
def market_geopolitics(limit: int = 8):
    try:
        items = fetch_ticker_news("SPY", max(1, min(int(limit), 20)))
        return safe({
            "items": [
                {
                    "theme": item.get("title"),
                    "heat": (item.get("sentiment") or {}).get("score"),
                    "why": item.get("summary"),
                    "policy_details": [item],
                    "benefiting_sectors": [],
                    "pressured_sectors": [],
                    "stocks_to_watch": [],
                }
                for item in items
            ],
            "method": "Provider news scan for policy, rates, macro and geopolitical headlines.",
            "disclaimer": "Confirm policy impact with price, volume and official releases.",
        })
    except Exception as e:
        return {"items": [], "error": str(e)}

@app.get("/api/v1/evidence/{ticker}")
def evidence(ticker: str, run: bool = False):
    # Evidence endpoint now reports actual research results when requested.
    if run:
        return research(ticker, run=True)
    return {
        "ticker": ticker.upper(),
        "status": "RESEARCH_ONLY",
        "production_signal_impact": False,
        "phases": {"3.8": "AVAILABLE", "3.9": "AVAILABLE", "3.9.1": "AVAILABLE"},
        "message": "Select Run Research to execute the existing validation pipeline."
    }

@app.get("/api/v1/research/{ticker}")
def research(ticker: str, run: bool = False):
    if not run:
        return {
            "ticker": ticker.upper(),
            "status": "NOT_RUN",
            "production_signal_impact": False,
            "phases": ["3.8", "3.9", "3.9.1"],
            "message": "Research is available but has not been executed."
        }
    try:
        from app.backtesting.feature_engineering import FeatureEngineeringEngine
        from app.backtesting.evidence_engine import EvidenceEngine
        from app.backtesting.phase_38_robustness import Phase38Robustness
        from app.backtesting.phase_39_statistical_validation import Phase39StatisticalValidation
        from app.backtesting.phase_39_1_evidence_diagnostic import Phase391EvidenceDiagnostic

        df = history(ticker, "5y")
        fe = FeatureEngineeringEngine(df)
        features = fe.build_features()
        current = fe.build_current_features(df)
        train_size = max(1, int(len(features) * 0.7))
        train, test = features.iloc[:train_size].copy(), features.iloc[train_size:].copy()

        evidence_engine = EvidenceEngine(feature_data=features)
        evidence_engine.fit(train)
        current_evidence = evidence_engine.evaluate_current_features(current)
        status = evidence_engine.status()
        stable = status.get("stable_features", {}) if isinstance(status, dict) else {}

        phase38 = (
            Phase38Robustness(feature_data=features, stable_features=stable).run()
            if stable else {"status": "NO_STABLE_FEATURES"}
        )

        current_scores = {}
        summary = current_evidence.get("summary") if isinstance(current_evidence, dict) else None
        if hasattr(summary, "iterrows"):
            for _, row in summary.iterrows():
                if row.get("horizon") is not None and row.get("score") is not None:
                    current_scores[str(row["horizon"])] = float(row["score"])

        phase39 = Phase39StatisticalValidation(
            evidence_engine=evidence_engine, test_data=test,
            current_features=current, current_scores=current_scores
        ).run()

        phase391 = Phase391EvidenceDiagnostic(
            evidence_engine=evidence_engine, test_data=test,
            train_data=train, feature_data=features,
            current_scores=current_scores
        ).run()

        return safe({
            "ticker": ticker.upper(),
            "status": "COMPLETE",
            "production_signal_impact": False,
            "phase_3_8": phase38,
            "phase_3_9": phase39,
            "phase_3_9_1": phase391,
            "current_evidence": current_evidence,
        })
    except Exception as e:
        return {
            "ticker": ticker.upper(),
            "status": "ERROR",
            "production_signal_impact": False,
            "error": str(e),
            "traceback": traceback.format_exc(limit=8)
        }

@app.get("/api/v1/fundamentals/{ticker}")
def fundamentals_alias(ticker: str, quarters: int = 10):
    return fundamental(ticker, quarters)

@app.get("/api/v1/risk")
def risk():
    try:
        payload = json.loads(PORTFOLIO_FILE.read_text())
        rows = portfolio_rows(payload)
        doctor = portfolio_doctor(payload, rows)
        return safe({"doctor": doctor, "positions": rows})
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/v1/overview/{ticker}")
def overview(ticker: str, period: str = Query("1y", pattern=PERIOD_RE)):
    return dashboard(ticker, period)

@app.post("/api/v1/auth/login", response_model=TokenResponse)
def login(request: LoginRequest):
    if not authenticate_user(request.username, request.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    token = create_access_token(request.username)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=60 * 60 * 8,
    )


@app.get("/api/v1/auth/me")
def auth_me(current_user: str = Depends(get_current_user)):
    return {
        "authenticated": True,
        "username": current_user,
    }


@app.get("/api/v1/portfolio")
def portfolio(current_user: str = Depends(get_current_user)):
    try:
        payload = json.loads(PORTFOLIO_FILE.read_text())
        rows = portfolio_rows(payload)
        doctor = portfolio_doctor(payload, rows)
        return safe({"portfolio": payload, "positions": rows, "doctor": doctor})
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/v1/portfolio/{ticker}")
def portfolio_ticker(
    ticker: str,
    current_user: str = Depends(get_current_user),
):
    try:
        return safe(analyze_ticker(ticker.upper()))
    except Exception as e:
        raise HTTPException(502, str(e))

@app.get("/api/v1/stock/{ticker}")
def stock_workspace(ticker: str):
    """One-call workspace payload for the web/mobile clients."""
    t = ticker.upper()
    try:
        df, quote, tech, dec = core_analysis(t, "1y")
        company_data = build_company_intelligence(t, quarters=10)
        try:
            fundamental_data = fundamental(t, quarters=10)
        except Exception:
            fundamental_data = {}
        try:
            news_data = fetch_ticker_news(t, 12)
        except Exception:
            news_data = []
        tech_out = dict(tech or {})
        for src_key, alias in [
            ("sma_5","sma5"),("sma_10","sma10"),("sma_20","sma20"),
            ("sma_50","sma50"),("sma_200","sma200"),
            ("macd_signal","macdSignal"),("macd_histogram","macdHistogram"),
            ("volume_ratio","volumeRatio")
        ]:
            if alias not in tech_out:
                tech_out[alias] = tech_out.get(src_key)
        decision_out = dict(dec or {})
        if "technical_score" not in decision_out:
            decision_out["technical_score"] = decision_out.get("score")
        return safe({
            "ticker": t,
            "quote": quote,
            "technical": tech_out,
            "decision": decision_out,
            "company": company_data,
            "fundamental": fundamental_data,
            "news": news_data,
            "chart": rows_from_df(df.tail(1200)),
        })
    except Exception as e:
        raise HTTPException(502, str(e))
