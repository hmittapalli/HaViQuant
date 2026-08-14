from __future__ import annotations

from typing import Any, Dict, Optional
import time
try:
    import yfinance as yf
except Exception:
    yf = None


def _num(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        x = float(value)
        if x != x:
            return None
        return x
    except Exception:
        return None


def get_live_quote(ticker: str) -> Dict[str, Any]:
    """Best-effort live/last-available quote with explicit data health.

    The portfolio must never interpret a missing quote as a zero-dollar position.
    """
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return {"ticker": ticker, "price": None, "status": "INVALID"}

    errors = []
    now = time.time()
    if yf is None:
        return {"ticker": ticker, "price": None, "previous": None, "change": None, "change_pct": None, "source": None, "status": "UNAVAILABLE", "errors": ["yfinance is not installed"]}

    # 1) fast_info
    try:
        info = yf.Ticker(ticker).fast_info
        price = _num(info.get("last_price"))
        previous = _num(info.get("previous_close"))
        if price is not None and price > 0:
            change = price - previous if previous is not None else None
            pct = change / previous * 100 if change is not None and previous else None
            return {
                "ticker": ticker, "price": price, "previous": previous,
                "change": change, "change_pct": pct,
                "source": "Yahoo Finance fast_info", "status": "LIVE",
                "timestamp": now,
            }
    except Exception as exc:
        errors.append(f"fast_info: {exc}")

    # 2) 1d history
    try:
        hist = yf.Ticker(ticker).history(period="5d", interval="1d", auto_adjust=False)
        if hist is not None and not hist.empty:
            close = _num(hist["Close"].dropna().iloc[-1])
            previous = _num(hist["Close"].dropna().iloc[-2]) if len(hist["Close"].dropna()) > 1 else None
            if close is not None and close > 0:
                change = close - previous if previous is not None else None
                pct = change / previous * 100 if change is not None and previous else None
                return {
                    "ticker": ticker, "price": close, "previous": previous,
                    "change": change, "change_pct": pct,
                    "source": "Yahoo Finance history", "status": "LAST_AVAILABLE",
                    "timestamp": now,
                }
    except Exception as exc:
        errors.append(f"history: {exc}")

    return {
        "ticker": ticker, "price": None, "previous": None,
        "change": None, "change_pct": None,
        "source": None, "status": "UNAVAILABLE",
        "timestamp": now, "errors": errors,
    }
