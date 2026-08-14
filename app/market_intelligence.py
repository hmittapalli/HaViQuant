from __future__ import annotations

from typing import Any, Dict, List
import pandas as pd
import numpy as np
try:
    import yfinance as yf
except Exception:
    yf = None
from app.portfolio.portfolio_intelligence import analyze_ticker, SECTOR_MAP, SECTOR_ETFS, _f

MACRO_SYMBOLS={"S&P 500":"SPY","Nasdaq 100":"QQQ","VIX":"^VIX","10Y Yield":"^TNX","2Y Yield":"^IRX","Dollar":"DX-Y.NYB","Gold":"GC=F","Oil":"CL=F"}

UNIVERSE=["NVDA","AMD","AVGO","MSFT","GOOGL","AMZN","META","AAPL","INTU","CRM","ORCL","NOW","CRWD","JPM","BAC","GS","XOM","CVX","COP","SLB","LLY","UNH","CAT","GE","DE","LIN","FCX","XLK","XLF","XLE","XLV","XLI","XLB","XLY","XLP","XLU","XLRE","XLC"]


def macro_snapshot() -> Dict[str,Any]:
    out={}
    if yf is None:
        out["regime"]={"risk_appetite":"UNKNOWN","rates_trend":"UNKNOWN","data_status":"yfinance not installed"}
        return out
    for name,t in MACRO_SYMBOLS.items():
        try:
            hist=yf.Ticker(t).history(period="1mo",interval="1d",auto_adjust=False)
            if hist is None or hist.empty: continue
            c=hist["Close"].dropna(); last=float(c.iloc[-1]); prev=float(c.iloc[-6]) if len(c)>5 else float(c.iloc[0])
            out[name]={"ticker":t,"value":last,"change_5d_pct":(last/prev-1)*100 if prev else None}
        except Exception: continue
    # Simple regime classifier; displayed as macro context, never direct BUY/SELL.
    ten=out.get("10Y Yield",{}).get("change_5d_pct")
    vix=out.get("VIX",{}).get("change_5d_pct")
    qqq=out.get("Nasdaq 100",{}).get("change_5d_pct")
    risk="NEUTRAL"
    if qqq is not None and vix is not None:
        if qqq>1 and vix<0: risk="RISK-ON"
        elif qqq<-1 and vix>0: risk="RISK-OFF"
    out["regime"]={"risk_appetite":risk,"rates_trend":"RISING" if ten is not None and ten>1 else "STABLE/FALLING" if ten is not None else "UNKNOWN"}
    return out


def sector_rotation() -> List[Dict[str,Any]]:
    rows=[]
    if yf is None:
        return rows
    for sector,t in SECTOR_ETFS.items():
        try:
            h=yf.Ticker(t).history(period="3mo",interval="1d",auto_adjust=False)
            if h is None or len(h)<22: continue
            c=h["Close"].dropna(); r5=(float(c.iloc[-1])/float(c.iloc[-6])-1)*100; r20=(float(c.iloc[-1])/float(c.iloc[-21])-1)*100
            score=max(0,min(100,50+r5*8+r20*2))
            rows.append({"sector":sector,"ticker":t,"return_5d":r5,"return_20d":r20,"score":score})
        except Exception: continue
    return sorted(rows,key=lambda x:x["score"],reverse=True)


def scan_opportunities(universe:List[str]|None=None, limit:int=10) -> List[Dict[str,Any]]:
    universe=universe or UNIVERSE; results=[]
    for ticker in universe:
        try:
            a=analyze_ticker(ticker); d=a["decision"]; s=a["snapshot"]; p=a["probability"]; plan=a["trade_plan"]
            sig=str(d.get("signal","WATCH")).upper(); base=float(d.get("score",0) or 0)
            hist=float(p.get("win_rate") or 50); rr=float(plan.get("risk_reward") or 0)
            trend=25 if s.get("price",0)>((s.get("sma50") or s.get("price",0))) else 0
            score=max(0,min(100,0.55*base+0.25*hist+0.20*min(100,rr*30)+trend*.15))
            results.append({"ticker":ticker,"sector":a["sector"],"signal":sig,"score":score,"technical_score":base,"historical_win_rate":hist,"prob_up_3":p.get("prob_up_3"),"risk_reward":rr,"trade_plan":plan,"price":s.get("price")})
        except Exception as exc:
            results.append({"ticker":ticker,"sector":SECTOR_MAP.get(ticker,"Unknown"),"signal":"DATA UNAVAILABLE","score":0,"error":str(exc)})
    return sorted(results,key=lambda x:x.get("score",0),reverse=True)[:limit]


def sector_impact_map(macro: Dict[str,Any], rotation: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    """Heuristic cross-sector transmission map.

    This is intentionally presented as a research scenario, not a deterministic
    claim that one macro move will cause a sector to rise or fall.
    """
    oil=macro.get("Oil",{}).get("change_5d_pct")
    ten=macro.get("10Y Yield",{}).get("change_5d_pct")
    dxy=macro.get("Dollar",{}).get("change_5d_pct")
    vix=macro.get("VIX",{}).get("change_5d_pct")
    scores={s:0.0 for s in SECTOR_ETFS}
    reasons={s:[] for s in SECTOR_ETFS}
    if oil is not None:
        if oil>3:
            for s in ["Energy"]: scores[s]+=25; reasons[s].append("oil momentum positive")
            for s in ["Consumer Discretionary","Industrials"]: scores[s]-=8; reasons[s].append("energy-cost pressure")
        elif oil<-3:
            for s in ["Consumer Discretionary","Industrials"]: scores[s]+=15; reasons[s].append("lower energy-cost pressure")
            scores["Energy"]-=18; reasons["Energy"].append("oil momentum negative")
    if ten is not None:
        if ten>3:
            for s in ["Financials"]: scores[s]+=14; reasons[s].append("higher-rate environment can support net interest margins")
            for s in ["Real Estate","Technology"]: scores[s]-=12; reasons[s].append("discount-rate pressure")
        elif ten<-3:
            for s in ["Technology","Real Estate"]: scores[s]+=14; reasons[s].append("lower discount-rate pressure")
            scores["Financials"]-=8; reasons["Financials"].append("lower-rate pressure")
    if dxy is not None and dxy>3:
        scores["Energy"]+=5; reasons["Energy"].append("commodity pricing context")
        scores["Technology"]-=5; reasons["Technology"].append("translation/global-demand sensitivity")
    if vix is not None and vix>8:
        for s in ["Utilities","Consumer Staples","Healthcare"]: scores[s]+=10; reasons[s].append("defensive regime")
        for s in ["Technology","Consumer Discretionary"]: scores[s]-=8; reasons[s].append("risk-off sensitivity")
    rot={r["sector"]:r["score"] for r in rotation}
    out=[]
    for s,v in scores.items():
        combined=max(-100,min(100,v + (rot.get(s,50)-50)*0.35))
        out.append({"sector":s,"impact_score":combined,"direction":"BENEFIT" if combined>8 else "PRESSURE" if combined<-8 else "MIXED","reasons":reasons[s]})
    return sorted(out,key=lambda x:x["impact_score"],reverse=True)
