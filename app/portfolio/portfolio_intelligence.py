from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import math
import numpy as np
import pandas as pd

from app.data.live_quotes import get_live_quote
from app.data.market_data import MarketDataService
from app.analysis.technical_analysis import TechnicalAnalysisEngine
from app.analysis.decision_engine import DecisionEngine

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
    "TLT":"Long Duration Bonds","IWM":"Small Caps","DIA":"Broad Market","VTI":"Broad Market",
}

SECTOR_ETFS = {
    "Technology":"XLK","Financials":"XLF","Energy":"XLE","Healthcare":"XLV","Industrials":"XLI",
    "Materials":"XLB","Utilities":"XLU","Consumer Discretionary":"XLY","Consumer Staples":"XLP",
    "Real Estate":"XLRE","Communication Services":"XLC",
}


def _f(v: Any) -> Optional[float]:
    try:
        if v is None: return None
        x = float(v)
        return None if not math.isfinite(x) else x
    except Exception:
        return None


def _decision_signal(decision: Any) -> str:
    if isinstance(decision, dict):
        return str(decision.get("signal") or decision.get("decision") or "WATCH").upper()
    return str(getattr(decision, "signal", "WATCH")).upper()


def _atr(df: pd.DataFrame) -> float:
    h,l,c = df["High"], df["Low"], df["Close"]
    pc = c.shift(1)
    tr = pd.concat([(h-l),(h-pc).abs(),(l-pc).abs()], axis=1).max(axis=1)
    return float(tr.rolling(14).mean().iloc[-1]) if len(df) >= 15 else float(c.iloc[-1] * .03)


def _technical_snapshot(df: pd.DataFrame) -> Dict[str, float]:
    c = df["Close"]
    v = df["Volume"]
    sma20 = c.rolling(20).mean()
    sma50 = c.rolling(50).mean()
    sma200 = c.rolling(200).mean()
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    sig = macd.ewm(span=9, adjust=False).mean()
    delta = c.diff(); gain = delta.clip(lower=0); loss = -delta.clip(upper=0)
    rs = gain.ewm(alpha=1/14, adjust=False).mean() / loss.ewm(alpha=1/14, adjust=False).mean().replace(0,np.nan)
    rsi = 100 - 100/(1+rs)
    rv = v / v.rolling(20).mean()
    atr = _atr(df)
    price = float(c.iloc[-1])
    return {
        "price": price, "sma20": _f(sma20.iloc[-1]), "sma50": _f(sma50.iloc[-1]), "sma200": _f(sma200.iloc[-1]),
        "rsi": _f(rsi.iloc[-1]), "macd": _f(macd.iloc[-1]), "macd_signal": _f(sig.iloc[-1]),
        "macd_hist": _f((macd-sig).iloc[-1]), "relative_volume": _f(rv.iloc[-1]), "atr": atr,
        "return_5d": _f(c.pct_change(5).iloc[-1]*100), "return_20d": _f(c.pct_change(20).iloc[-1]*100),
        "high_20": _f(c.tail(20).max()), "low_20": _f(c.tail(20).min()),
    }


def historical_probability(df: pd.DataFrame, snap: Dict[str,float], horizon: int = 5) -> Dict[str, Any]:
    """Empirical analog probability; current row is excluded.

    This is a research statistic, not a guarantee or a trained ML forecast.
    """
    if len(df) < 260:
        return {"samples":0,"prob_up_3":None,"prob_down_3":None,"median_return":None,"win_rate":None}
    c = df["Close"].astype(float)
    sma20 = c.rolling(20).mean(); sma50 = c.rolling(50).mean(); sma200 = c.rolling(200).mean()
    ema12 = c.ewm(span=12,adjust=False).mean(); ema26=c.ewm(span=26,adjust=False).mean(); macd=ema12-ema26; sig=macd.ewm(span=9,adjust=False).mean()
    delta=c.diff(); gain=delta.clip(lower=0); loss=-delta.clip(upper=0); rs=gain.ewm(alpha=1/14,adjust=False).mean()/loss.ewm(alpha=1/14,adjust=False).mean().replace(0,np.nan); rsi=100-100/(1+rs)
    rv=df["Volume"]/df["Volume"].rolling(20).mean()
    mask=(sma20<sma50 if (snap.get("sma20") or 0)<(snap.get("sma50") or 0) else sma20>=sma50)
    if (snap.get("rsi") or 50) >= 60: mask &= rsi.between(55,75)
    elif (snap.get("rsi") or 50) <= 40: mask &= rsi.between(25,45)
    else: mask &= rsi.between(40,60)
    if (snap.get("macd") or 0) >= (snap.get("macd_signal") or 0): mask &= macd >= sig
    else: mask &= macd <= sig
    if (snap.get("relative_volume") or 1) >= 1.2: mask &= rv >= 1.0
    else: mask &= rv < 1.5
    future = c.shift(-horizon)/c - 1
    vals = future[mask].dropna() * 100
    if len(vals) < 20:
        vals = future.dropna().tail(500) * 100
    if vals.empty:
        return {"samples":0,"prob_up_3":None,"prob_down_3":None,"median_return":None,"win_rate":None}
    return {"samples":int(len(vals)),"prob_up_3":float((vals>=3).mean()*100),"prob_down_3":float((vals<=-3).mean()*100),"median_return":float(vals.median()),"win_rate":float((vals>0).mean()*100)}


def build_trade_plan(df: pd.DataFrame, signal: str, probability: Dict[str,Any]) -> Dict[str,Any]:
    s = _technical_snapshot(df); p=s["price"]; atr=s["atr"] or p*.03
    support=float(df["Low"].tail(20).min()); resistance=float(df["High"].tail(20).max())
    bullish="BUY" in signal or "STRONG BUY" in signal
    bearish="SELL" in signal or "STRONG SELL" in signal
    if bullish:
        entry_low=min(p, p-0.35*atr); entry_high=p+0.15*atr; stop=max(support-0.25*atr, p-1.5*atr)
        risk=max(entry_high-stop, 0.01); t1=max(resistance, entry_high+2*risk); t2=entry_high+3*risk
    elif bearish:
        entry_low=p-0.15*atr; entry_high=max(p,p+0.35*atr); stop=min(resistance+0.25*atr,p+1.5*atr)
        risk=max(stop-entry_low,0.01); t1=min(support,entry_low-2*risk); t2=entry_low-3*risk
    else:
        entry_low=max(0,p-0.5*atr); entry_high=p+0.5*atr; stop=None; t1=None; t2=None
    rr = abs((t1-entry_high)/(entry_high-stop)) if stop and t1 else None
    return {"entry_low":entry_low,"entry_high":entry_high,"stop":stop,"target1":t1,"target2":t2,"support":support,"resistance":resistance,"risk_reward":rr,"horizon":"3-10 trading days"}


def analyze_ticker(ticker: str) -> Dict[str,Any]:
    ticker=ticker.upper().strip(); service=MarketDataService(); df=service.get_history(ticker,"5y")
    technical=TechnicalAnalysisEngine().analyze(df); decision=DecisionEngine().evaluate(technical)
    snap=_technical_snapshot(df); prob=historical_probability(df,snap,5); plan=build_trade_plan(df,_decision_signal(decision),prob)
    return {"ticker":ticker,"sector":SECTOR_MAP.get(ticker,"Unknown"),"quote":get_live_quote(ticker),"technical":technical,"decision":decision,"snapshot":snap,"probability":prob,"trade_plan":plan}


def portfolio_rows(portfolio: Dict[str,Any]) -> List[Dict[str,Any]]:
    rows=[]
    for p in portfolio.get("positions",[]):
        t=str(p.get("ticker","")).upper(); shares=_f(p.get("shares")) or 0; avg=_f(p.get("average_cost")) or 0
        if not t or shares<=0: continue
        q=get_live_quote(t); price=_f(q.get("price")); value=price*shares if price is not None else None; cost=avg*shares if avg>0 else None
        pnl=value-cost if value is not None and cost is not None else None
        rows.append({**p,"ticker":t,"shares":shares,"average_cost":avg,"price":price,"market_value":value,"cost_basis":cost,"pnl":pnl,"pnl_pct":pnl/cost*100 if pnl is not None and cost else None,"quote_status":q.get("status"),"quote_source":q.get("source"),"change_pct":q.get("change_pct")})
    return rows


def portfolio_doctor(portfolio: Dict[str,Any], rows: List[Dict[str,Any]]) -> Dict[str,Any]:
    total=sum(r["market_value"] or 0 for r in rows); total_cost=sum(r["cost_basis"] or 0 for r in rows)
    valued_cost=sum(r["cost_basis"] or 0 for r in rows if r.get("market_value") is not None)
    coverage=(valued_cost/total_cost*100) if total_cost else 100.0
    pnl=(total-valued_cost) if valued_cost > 0 else None
    sector={}
    for r in rows:
        value=r["market_value"] or 0; sec=SECTOR_MAP.get(r["ticker"],"Other"); sector[sec]=sector.get(sec,0)+value
    sector_weights={k:(v/total*100 if total else 0) for k,v in sector.items()}
    issues=[]; strengths=[]
    tech_weight=sum(v for k,v in sector_weights.items() if "Technology" in k or k in {"Technology/Growth","Technology/Cybersecurity"})
    broad=sum(v for k,v in sector_weights.items() if k=="Broad Market")
    speculative=sum(v for k,v in sector_weights.items() if "Alternative" in k)
    if tech_weight>35: issues.append({"severity":"HIGH","title":"Technology concentration","detail":f"Estimated direct technology exposure is {tech_weight:.1f}% before ETF look-through."})
    if broad>45: issues.append({"severity":"MEDIUM","title":"Broad-market overlap","detail":f"Broad-market ETFs represent {broad:.1f}% of tracked holdings."})
    if speculative>10: issues.append({"severity":"MEDIUM","title":"Speculative exposure","detail":f"Alternative/private-market exposure is {speculative:.1f}%."})
    missing=[s for s in ["Financials","Healthcare","Energy","Industrials","Materials","Utilities"] if sector_weights.get(s,0)<5]
    if missing: issues.append({"severity":"MEDIUM","title":"Underrepresented sectors","detail":"Consider new-money diversification toward: "+", ".join(missing)+"."})
    if coverage < 100:
        issues.append({"severity":"HIGH","title":"Incomplete live valuation","detail":f"Only {coverage:.1f}% of invested cost has a valid live/last-available quote. Unknown positions are excluded from P/L instead of being treated as losses."})
    if total>0: strengths.append("Live quote coverage and market-value calculations are available for positions with valid quotes.")
    health=max(0,min(100,100-len([i for i in issues if i['severity']=='HIGH'])*18-len([i for i in issues if i['severity']=='MEDIUM'])*8))
    return {"health":health,"total_value":total,"total_cost":total_cost,"valued_cost":valued_cost,"valuation_coverage":coverage,"pnl":pnl,"pnl_pct":(pnl/valued_cost*100) if pnl is not None and valued_cost else None,"sector_weights":sector_weights,"issues":issues,"strengths":strengths,"missing_sectors":missing}
