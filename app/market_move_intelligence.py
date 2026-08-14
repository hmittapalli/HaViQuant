
"""HaViQuant price-move explanation engine.

This module explains *likely contributors* to a stock's move. It deliberately
does not claim that a headline or indicator caused the move unless there is
strong evidence. It combines:
- price/volume changes
- technical state
- broad market (SPY) move
- sector ETF move
- recent headline sentiment/category
- gap vs previous close

It is an explanatory/research layer and never changes BUY/SELL decisions.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import math
import pandas as pd

try:
    import yfinance as yf
except Exception:
    yf = None

SECTOR_ETFS = {
    "Technology":"XLK","Financials":"XLF","Energy":"XLE","Healthcare":"XLV",
    "Industrials":"XLI","Materials":"XLB","Utilities":"XLU",
    "Consumer Discretionary":"XLY","Consumer Staples":"XLP",
    "Real Estate":"XLRE","Communication Services":"XLC",
    "Broad Market":"SPY","Technology/Growth":"QQQ",
    "Technology/Cybersecurity":"HACK",
    "Alternative/Private Markets":"SPY",
    "Gold/Commodities":"GLD","Long Duration Bonds":"TLT",
    "Small Caps":"IWM",
}

SECTOR_MAP = {
    "NVDA":"Technology","MSFT":"Technology","AAPL":"Technology","GOOGL":"Communication Services",
    "GOOG":"Communication Services","AMZN":"Consumer Discretionary","META":"Communication Services",
    "AVGO":"Technology","AMD":"Technology","INTC":"Technology","CRM":"Technology","ORCL":"Technology",
    "ADBE":"Technology","NFLX":"Communication Services","INTU":"Technology","CRWD":"Technology","NOW":"Technology",
    "QQQM":"Technology/Growth","CIBR":"Technology/Cybersecurity","VOO":"Broad Market","SPY":"Broad Market",
    "SPCX":"Alternative/Private Markets","SKHY":"Alternative/Private Markets","NOK":"Communication Services",
    "JPM":"Financials","BAC":"Financials","GS":"Financials","XLF":"Financials","XLE":"Energy","XOM":"Energy",
    "CVX":"Energy","COP":"Energy","SLB":"Energy","XLV":"Healthcare","LLY":"Healthcare","UNH":"Healthcare",
    "XLI":"Industrials","CAT":"Industrials","GE":"Industrials","XLB":"Materials","GLD":"Gold/Commodities",
    "TLT":"Long Duration Bonds","IWM":"Small Caps",
}

def _f(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else None
    except Exception:
        return None

def _pct(a,b):
    a,b=_f(a),_f(b)
    if a is None or b in (None,0): return None
    return (a/b-1)*100

def _quote_change(symbol: str, period="5d") -> Optional[float]:
    if yf is None: return None
    try:
        h=yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=False)
        if h is None or h.empty: return None
        c=h["Close"].dropna()
        if len(c)<2: return None
        return _pct(c.iloc[-1], c.iloc[0])
    except Exception:
        return None

def _news_signal(articles: List[Dict[str,Any]]) -> Dict[str,Any]:
    pos=sum(1 for a in articles if str(a.get("sentiment","")).lower()=="positive")
    neg=sum(1 for a in articles if str(a.get("sentiment","")).lower()=="negative")
    total=pos+neg
    if total==0:
        return {"label":"NO CLEAR NEWS CATALYST","score":0,"positive":0,"negative":0}
    score=round((pos-neg)/total*100)
    label="POSITIVE NEWS BIAS" if score>20 else "NEGATIVE NEWS BIAS" if score<-20 else "MIXED NEWS"
    return {"label":label,"score":score,"positive":pos,"negative":neg}

def explain_move(ticker: str, df: pd.DataFrame, articles=None, sector=None) -> Dict[str,Any]:
    articles=articles or []
    out={"ticker":ticker.upper(),"direction":"FLAT","move_pct":0.0,"drivers":[],"risks":[],"confidence":"LOW"}
    if df is None or df.empty or "Close" not in df:
        out["drivers"].append({"label":"Price data unavailable","strength":"N/A","evidence":"No usable price history"})
        return out
    c=pd.to_numeric(df["Close"],errors="coerce").dropna()
    if len(c)<2: return out
    last=float(c.iloc[-1]); prev=float(c.iloc[-2]); move=_pct(last,prev) or 0.0
    out["move_pct"]=move
    out["direction"]="UP" if move>0.15 else "DOWN" if move<-0.15 else "FLAT"

    volume_ratio=None
    if "Volume" in df.columns:
        v=pd.to_numeric(df["Volume"],errors="coerce").dropna()
        if len(v)>=21 and float(v.iloc[-1])>0:
            avg=float(v.iloc[-21:-1].mean())
            if avg>0: volume_ratio=float(v.iloc[-1])/avg

    sma20=float(c.rolling(20).mean().iloc[-1]) if len(c)>=20 else None
    sma50=float(c.rolling(50).mean().iloc[-1]) if len(c)>=50 else None
    r5=_pct(c.iloc[-1],c.iloc[-6]) if len(c)>=6 else None
    r20=_pct(c.iloc[-1],c.iloc[-21]) if len(c)>=21 else None

    sector_name=sector or SECTOR_MAP.get(ticker.upper(),"Unknown")
    market5=_quote_change("SPY","10d")
    sector_symbol=SECTOR_ETFS.get(sector_name)
    sector5=_quote_change(sector_symbol,"10d") if sector_symbol else None
    news=_news_signal(articles)

    drivers=[]
    risks=[]

    # Relative performance: strongest explanatory evidence after news.
    if market5 is not None and abs(move)>=0.5:
        rel=move-market5
        if rel>0.75:
            drivers.append({"label":"Stock-specific strength","strength":"HIGH","evidence":f"{move:+.2f}% today vs SPY {market5:+.2f}% over recent window"})
        elif rel<-0.75:
            risks.append({"label":"Stock-specific weakness","strength":"HIGH","evidence":f"{move:+.2f}% today while SPY recent move was {market5:+.2f}%"})

    if sector5 is not None and abs(move)>=0.5:
        rel=move-sector5
        if rel>0.75:
            drivers.append({"label":f"{sector_name} relative strength","strength":"HIGH","evidence":f"Sector ETF {sector5:+.2f}% recent; stock is outperforming"})
        elif rel<-0.75:
            risks.append({"label":f"{sector_name} relative weakness","strength":"HIGH","evidence":f"Sector ETF {sector5:+.2f}% recent; stock is underperforming"})

    if news["score"]>20:
        drivers.append({"label":"Positive news flow","strength":"MEDIUM","evidence":f"{news['positive']} positive vs {news['negative']} negative recent headlines"})
    elif news["score"]<-20:
        risks.append({"label":"Negative news flow","strength":"MEDIUM","evidence":f"{news['negative']} negative vs {news['positive']} positive recent headlines"})

    if volume_ratio is not None and volume_ratio>=1.5 and abs(move)>=0.75:
        drivers.append({"label":"Abnormal volume confirmation","strength":"HIGH","evidence":f"Volume {volume_ratio:.2f}× prior 20D average"})
    elif volume_ratio is not None and volume_ratio<0.75 and abs(move)>=1.0:
        risks.append({"label":"Low-volume move","strength":"MEDIUM","evidence":f"Volume only {volume_ratio:.2f}× prior 20D average; move may lack confirmation"})

    if sma20 is not None and sma50 is not None:
        if last>sma20>sma50 and move>0:
            drivers.append({"label":"Bullish trend alignment","strength":"MEDIUM","evidence":"Price > SMA20 > SMA50"})
        elif last<sma20<sma50 and move<0:
            risks.append({"label":"Bearish trend alignment","strength":"MEDIUM","evidence":"Price < SMA20 < SMA50"})

    if r5 is not None:
        if r5>3: drivers.append({"label":"Short-term momentum","strength":"MEDIUM","evidence":f"5D return {r5:+.2f}%"})
        elif r5<-3: risks.append({"label":"Short-term momentum pressure","strength":"MEDIUM","evidence":f"5D return {r5:+.2f}%"})

    if not drivers and out["direction"]=="UP":
        drivers.append({"label":"Price momentum","strength":"LOW","evidence":f"Price increased {move:+.2f}% today; no stronger driver confirmed"})
    if not risks and out["direction"]=="DOWN":
        risks.append({"label":"Price weakness","strength":"LOW","evidence":f"Price decreased {move:+.2f}% today; no stronger driver confirmed"})

    # Confidence is based on independent evidence buckets, not causality.
    evidence_count=sum(1 for x in [market5,sector5,news["score"],volume_ratio,r5] if x is not None)
    confidence="HIGH" if len(drivers)+len(risks)>=3 and evidence_count>=3 else "MEDIUM" if len(drivers)+len(risks)>=2 else "LOW"
    out.update({"sector":sector_name,"market_5d":market5,"sector_5d":sector5,"volume_ratio":volume_ratio,
                "news":news,"drivers":drivers[:5],"risks":risks[:5],"confidence":confidence,
                "explanation":"Likely contributors based on price, relative performance, volume, trend and recent headlines. This is attribution evidence, not proof of causation."})
    return out
