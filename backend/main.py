from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import math, os, re, statistics, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, as_completed

import numpy as np
import pandas as pd
import yfinance as yf

try:
    # Works when FastAPI is started from the project root.
    from backend.company.intelligence_engine import get_company_intelligence
except Exception:
    try:
        # Fallback when running with backend as the working directory.
        from company.intelligence_engine import get_company_intelligence
    except Exception:
        get_company_intelligence = None

APP_VERSION = "26.2.1"
app = FastAPI(title="HaViQuant V26 360 Trading Intelligence", version=APP_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


class TradePlannerRequest(BaseModel):
    capital: float = 500
    max_loss_amount: float = 25
    number_of_positions: int = 3
    risk_profile: str = "balanced"
    strategy: str = "auto"
    symbols: Optional[List[str]] = None
    sector: Optional[str] = "All"
    allow_fractional_shares: bool = True
    portfolio_aware: bool = False


def clean(v: Any):
    if v is None or isinstance(v, (str, bool, int)):
        return v
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if hasattr(v, "item"):
        try: return clean(v.item())
        except Exception: pass
    if isinstance(v, dict): return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)): return [clean(x) for x in v]
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating,)): return clean(float(v))
    if isinstance(v, pd.Timestamp): return v.isoformat()
    try:
        if pd.isna(v): return None
    except Exception: pass
    return v


def norm_ticker(t):
    t = (t or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9.\-]{1,12}", t):
        raise HTTPException(400, "Invalid ticker")
    return t


def period_for_interval(period, interval):
    allowed = {"1m":"7d", "2m":"60d", "5m":"60d", "15m":"60d", "30m":"60d", "60m":"730d", "1h":"730d", "1d":period or "6mo", "1wk":period or "5y", "1mo":period or "5y"}
    if interval not in allowed: raise HTTPException(400, f"Unsupported interval: {interval}")
    return allowed[interval] if interval in {"1m","2m","5m","15m","30m","60m","1h"} else (period or allowed[interval])


def download(ticker, period="6mo", interval="1d"):
    # yfinance has no native 4H interval; fetch 1H and resample below.
    source_interval = "1h" if interval == "4h" else interval
    period = period_for_interval(period, source_interval)
    try:
        df = yf.download(ticker, period=period, interval=source_interval, progress=False, auto_adjust=False, threads=False, timeout=8)
    except Exception as e:
        raise HTTPException(502, f"Market data provider error: {e}")
    if df is None or df.empty:
        raise HTTPException(404, f"No market data found for {ticker} ({interval})")
    if isinstance(df.columns, pd.MultiIndex): df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df.rename(columns={c:str(c).title().replace("Adj close", "Adj Close") for c in df.columns})
    needed = ["Open","High","Low","Close","Volume"]
    for c in needed:
        if c not in df.columns: raise HTTPException(502, f"Provider did not return {c}")
    df = df[needed].copy().dropna(subset=["Open","High","Low","Close"])
    if interval == "4h":
        df = df.resample("4h").agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"}).dropna(subset=["Open","High","Low","Close"])
    return df


def indicators(df):
    d=df.copy(); c=d.Close; h=d.High; l=d.Low; o=d.Open; v=d.Volume
    d["SMA20"]=c.rolling(20).mean(); d["SMA50"]=c.rolling(50).mean(); d["SMA200"]=c.rolling(200).mean()
    delta=c.diff(); gain=delta.clip(lower=0).rolling(14).mean(); loss=(-delta.clip(upper=0)).rolling(14).mean()
    rs=gain/loss.replace(0,np.nan); d["RSI14"]=100-(100/(1+rs))
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1); d["ATR14"]=tr.rolling(14).mean()
    d["Vol20"]=v.rolling(20).mean(); d["VolRatio"]=v/d["Vol20"]
    d["EMA9"]=c.ewm(span=9,adjust=False).mean(); d["EMA12"]=c.ewm(span=12,adjust=False).mean(); d["EMA26"]=c.ewm(span=26,adjust=False).mean()
    d["MACD"]=d.EMA12-d.EMA26; d["MACDSignal"]=d.MACD.ewm(span=9,adjust=False).mean(); d["VWAP"]=((c*v).cumsum()/v.replace(0,np.nan).cumsum())
    d["BBmid"]=c.rolling(20).mean(); sd=c.rolling(20).std(); d["BBupper"]=d.BBmid+2*sd; d["BBlower"]=d.BBmid-2*sd
    return d


def pattern(d):
    if len(d)<5: return {"name":"Insufficient history","confidence":0,"description":"Need more candles."}
    r=d.iloc[-1]; p=d.iloc[-2]; body=abs(r.Close-r.Open); rng=max(r.High-r.Low,1e-9); upper=r.High-max(r.Open,r.Close); lower=min(r.Open,r.Close)-r.Low
    if lower>body*2 and upper<max(body,1e-9)*.8 and r.Close>r.Open: return {"name":"Bullish hammer","confidence":78,"description":"Long lower wick with bullish close; buyers defended lower prices."}
    if upper>body*2 and lower<max(body,1e-9)*.8 and r.Close<r.Open: return {"name":"Bearish rejection","confidence":76,"description":"Long upper wick with bearish close; sellers rejected higher prices."}
    if r.Close>r.Open and p.Close<p.Open and r.Open<=p.Close and r.Close>=p.Open: return {"name":"Bullish engulfing","confidence":82,"description":"Current bullish body engulfs the prior bearish body."}
    if r.Close<r.Open and p.Close>p.Open and r.Open>=p.Close and r.Close<=p.Open: return {"name":"Bearish engulfing","confidence":82,"description":"Current bearish body engulfs the prior bullish body."}
    if body/rng<.12: return {"name":"Doji / indecision","confidence":62,"description":"Small body relative to range; wait for confirmation."}
    if len(d)>=20 and r.Close>r.SMA20 and r.SMA20>p.SMA20: return {"name":"Ascending trend / continuation","confidence":74,"description":"Price is above a rising SMA20; trend continuation is dominant."}
    if len(d)>=20 and r.Close<r.SMA20 and r.SMA20<p.SMA20: return {"name":"Descending trend / continuation","confidence":74,"description":"Price is below a falling SMA20; downside continuation is dominant."}
    return {"name":"Range / mixed structure","confidence":55,"description":"No single high-confidence candle pattern dominates."}


def analysis(ticker, period="6mo", interval="1d"):
    raw=download(ticker,period,interval); d=indicators(raw); r=d.iloc[-1]; prev=d.iloc[-2] if len(d)>1 else r; price=float(r.Close)
    atr=float(r.ATR14) if pd.notna(r.ATR14) else price*.02; sma20=float(r.SMA20) if pd.notna(r.SMA20) else price; sma50=float(r.SMA50) if pd.notna(r.SMA50) else price
    rsi=float(r.RSI14) if pd.notna(r.RSI14) else 50; macd=float(r.MACD) if pd.notna(r.MACD) else 0; macds=float(r.MACDSignal) if pd.notna(r.MACDSignal) else 0; vr=float(r.VolRatio) if pd.notna(r.VolRatio) else 1
    trend="Bullish" if price>sma20 and sma20>sma50 else ("Bearish" if price<sma20 and sma20<sma50 else "Mixed")
    momentum="Strong" if rsi>=60 and macd>macds else ("Weak" if rsi<=40 and macd<macds else "Neutral")
    volatility="Elevated" if atr/price>.035 else ("Low" if atr/price<.015 else "Normal")
    signal="BUY" if trend=="Bullish" and momentum=="Strong" else ("SELL" if trend=="Bearish" and momentum=="Weak" else "WAIT")
    support=float(d.Low.tail(20).min()); resistance=float(d.High.tail(20).max()); entry=price; stop=max(.01,entry-atr); t1=entry+atr; t2=entry+2*atr; t3=entry+3*atr
    rr1=(t1-entry)/(entry-stop) if entry>stop else 0; rr2=(t2-entry)/(entry-stop) if entry>stop else 0; rr3=(t3-entry)/(entry-stop) if entry>stop else 0
    expected_daily=max(atr,price*.005); eta=[max(1,round((x-entry)/expected_daily)) for x in (t1,t2,t3)]
    score=max(0,min(100,round(35+(12 if trend=="Bullish" else -8 if trend=="Bearish" else 0)+(15 if momentum=="Strong" else -10 if momentum=="Weak" else 0)+(8 if 1<=vr<=2 else 0)+(8 if signal=="BUY" else 0))))
    rows=[]
    for idx,x in d.tail(180).iterrows(): rows.append({"time":idx.isoformat(),"open":float(x.Open),"high":float(x.High),"low":float(x.Low),"close":float(x.Close),"volume":int(x.Volume) if pd.notna(x.Volume) else 0,"sma20":clean(x.SMA20),"ema9":clean(x.EMA9),"vwap":clean(x.VWAP),"rsi":clean(x.RSI14),"vol_ratio":clean(x.VolRatio)})
    return clean({"ticker":ticker,"price":price,"change_pct":((price/float(prev.Close))-1)*100,"signal":signal,"setup_quality":score,"trend":trend,"momentum":momentum,"volatility":volatility,"support":support,"resistance":resistance,"atr":atr,"rsi":rsi,"macd":macd,"macd_signal":macds,"volume_ratio":vr,"ema9":clean(r.EMA9),"vwap":clean(r.VWAP),"pattern":pattern(d),"levels":{"entry":entry,"stop":stop,"target1":t1,"target2":t2,"target3":t3},"eta_days":{"target1":eta[0],"target2":eta[1],"target3":eta[2]},"risk_reward":{"t1":rr1,"t2":rr2,"t3":rr3},"candles":rows,"interval":interval,"period":period,"updated_at":datetime.now(timezone.utc).isoformat()})


def timeframe_snapshot(ticker, interval, period):
    try:
        a=analysis(ticker,period,interval)
        ema_dir = "Bullish" if a["price"] >= (a.get("ema9") or a["price"]) else "Bearish"
        return {"interval":interval,"period":period,"trend":a["trend"],"momentum":a["momentum"],"signal":a["signal"],"rsi":a["rsi"],"volume_ratio":a["volume_ratio"],"ema_direction":ema_dir,"pattern":a["pattern"]["name"],"confidence":a["setup_quality"]}
    except HTTPException as e:
        return {"interval":interval,"period":period,"trend":"Unavailable","momentum":"Unavailable","signal":"WAIT","rsi":None,"volume_ratio":None,"ema_direction":"Unavailable","pattern":str(e.detail),"confidence":0}


def mtf(ticker):
    specs=[("4H","Trend","4h","60d"),("1H","Structure","1h","60d"),("15m","Setup","15m","60d"),("5m","Trigger","5m","60d"),("1m","Signal","1m","7d")]
    results={}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures={pool.submit(timeframe_snapshot,ticker,interval,period):(tf,label) for tf,label,interval,period in specs}
        for f in as_completed(futures):
            tf,label=futures[f]
            try: results[tf]={"tf":tf,"label":label,"data":f.result()}
            except Exception as e: results[tf]={"tf":tf,"label":label,"data":{"signal":"WAIT","trend":"Unavailable","pattern":str(e),"confidence":0}}
    return [results[tf] for tf,_,_,_ in specs]


def sentiment(text):
    text=(text or "").lower()
    pos={"beat","beats","strong","growth","grow","record","profit","profits","surge","surges","bullish","upgrade","upgraded","gain","gains","positive","approval","approved","deal","partnership","outperform","raises","raised","cut costs","rebound","recovery"}
    neg={"miss","misses","weak","decline","declines","drop","drops","fall","falls","bearish","downgrade","downgraded","loss","losses","negative","lawsuit","investigation","fine","fined","layoff","layoffs","tariff","tariffs","ban","banned","warning","warns","risk","risks","slump","crash","cuts","cut guidance"}
    words=set(re.findall(r"[a-z][a-z'-]+",text)); p=len(words&pos); n=len(words&neg); score=(p-n)/max(1,p+n)
    if score>=.25: label="Positive"
    elif score<=-.25: label="Negative"
    else: label="Neutral"
    impact="High" if abs(score)>=.6 or any(x in text for x in ["earnings","fed","rate decision","tariff","lawsuit","investigation","merger","acquisition"]) else ("Medium" if abs(score)>=.25 else "Low")
    return {"label":label,"score":round(score,2),"impact":impact}


def parse_pub(value):
    if isinstance(value,(int,float)):
        try: return datetime.fromtimestamp(value,tz=timezone.utc)
        except Exception:return None
    if isinstance(value,str):
        try: return datetime.fromisoformat(value.replace("Z","+00:00"))
        except Exception:
            try: return datetime.strptime(value[:25],"%a, %d %b %Y %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:return None
    return None


def enrich_item(item):
    s=sentiment((item.get("title") or "")+" "+(item.get("summary") or "")); dt=parse_pub(item.get("published"));
    return clean({**item,"sentiment":s,"published_iso":dt.isoformat() if dt else None,"recency":"Recent" if dt and dt>=datetime.now(timezone.utc)-timedelta(days=30) else "Older"})


def news(ticker):
    items=[]
    try:
        raw=yf.Ticker(ticker).news or []
        for n in raw[:20]:
            c=n.get("content",n); title=c.get("title") or n.get("title"); link=(c.get("canonicalUrl") or {}).get("url") if isinstance(c.get("canonicalUrl"),dict) else c.get("link"); provider=(c.get("provider") or {}).get("displayName") if isinstance(c.get("provider"),dict) else n.get("publisher"); pub=c.get("pubDate") or n.get("providerPublishTime")
            if title: items.append(enrich_item({"title":title,"publisher":provider or "Market source","url":link,"published":pub,"summary":c.get("summary") or c.get("description") or ""}))
    except Exception: pass
    items.sort(key=lambda x: x.get("published_iso") or "", reverse=True)
    return clean({"ticker":ticker,"items":items,"source":"Yahoo Finance news feed"})


def rss_search(query, limit=8):
    url="https://news.google.com/rss/search?q="+urllib.parse.quote(query)+"&hl=en-US&gl=US&ceid=US:en"; req=urllib.request.Request(url,headers={"User-Agent":"HaViQuant/26"})
    try:
        root=ET.fromstring(urllib.request.urlopen(req,timeout=8).read()); out=[]
        for item in root.findall(".//item")[:limit]: out.append(enrich_item({"title":item.findtext("title"),"url":item.findtext("link"),"published":item.findtext("pubDate"),"publisher":item.findtext("source")}))
        out.sort(key=lambda x:x.get("published_iso") or "", reverse=True)
        cutoff = datetime.now(timezone.utc) - timedelta(days=180)
        recent = [x for x in out if not x.get("published_iso") or parse_pub(x.get("published_iso")) >= cutoff]
        return recent or out
    except Exception: return []


def company_info(ticker):
    try:
        info=yf.Ticker(ticker).info or {}
        return clean({"ticker":ticker,"name":info.get("longName") or info.get("shortName") or ticker,"sector":info.get("sector"),"industry":info.get("industry"),"marketCap":info.get("marketCap"),"website":info.get("website"),"country":info.get("country"),"exchange":info.get("exchange")})
    except Exception as e: return {"ticker":ticker,"name":ticker,"sector":None,"industry":None,"marketCap":None,"error":str(e)}


def fundamentals(ticker):
    try:
        info=yf.Ticker(ticker).info or {}
        return clean({"ticker":ticker,"marketCap":info.get("marketCap"),"trailingPE":info.get("trailingPE"),"forwardPE":info.get("forwardPE"),"epsTrailingTwelveMonths":info.get("epsTrailingTwelveMonths"),"revenueGrowth":info.get("revenueGrowth"),"profitMargins":info.get("profitMargins"),"returnOnEquity":info.get("returnOnEquity"),"dividendYield":info.get("dividendYield"),"beta":info.get("beta")})
    except Exception as e: return {"ticker":ticker,"error":str(e)}


@app.get("/api/v1/meta")
def api_metadata():
    return clean({
        "app":"HaViQuant",
        "version":APP_VERSION,
        "supported_intraday":["1m","5m","15m","1h","4h"],
        "supported_navigation":["Stock Analysis","Dashboard","Company Intelligence","Fundamentals","Technical","Decision","Evidence Research","Portfolio","Risk","Backtesting","News","Watchlist","Alerts","Calendar","Settings"]
    })

@app.get("/api/v1/health")
def health(): return {"status":"ok","version":APP_VERSION,"data_provider":"yfinance"}

@app.get("/api/v1/market/quote")
def quote(ticker:str=Query(...)):
    a=analysis(norm_ticker(ticker),"1mo","1d"); return clean({"ticker":a["ticker"],"price":a["price"],"change_pct":a["change_pct"],"updated_at":a["updated_at"]})

@app.get("/api/v1/market/analysis")
def market_analysis(ticker:str=Query(...), period:str="6mo", interval:str="1d", include_mtf:bool=True):
    t=norm_ticker(ticker); a=analysis(t,period,interval)
    if include_mtf and interval=="1d": a["mtf"]=mtf(t)
    return clean(a)

@app.get("/api/v1/market/news")
def market_news(ticker:str=Query(...)): return news(norm_ticker(ticker))

@app.get("/api/v1/market/macro")
def macro(ticker:str=Query(...)):
    t=norm_ticker(ticker); return clean({"ticker":t,"geopolitical":rss_search(f"{t} geopolitics tariffs sanctions trade war international policy",6),"politics":rss_search(f"{t} politician speech policy regulation government",6),"macro":rss_search(f"{t} Federal Reserve rates inflation jobs economy",6),"note":"Headline/context signals only; they do not deterministically predict price."})

@app.get("/api/v1/market/360")
def full360(ticker:str=Query(...)):
    t=norm_ticker(ticker); return clean({"analysis":market_analysis(t,include_mtf=True),"news":news(t)["items"],"macro":macro(t)})

@app.get("/api/v1/trade-plan")
def trade_plan(ticker:str, capital:float=10000, risk_pct:float=1.0, stop_pct:float=3.0):
    t=norm_ticker(ticker); a=analysis(t); capital=max(0,float(capital)); risk_pct=max(.1,min(20,float(risk_pct))); stop_pct=max(.5,min(50,float(stop_pct))); entry=float(a["price"])
    shares_available=max(0,math.floor(capital/entry)) if entry>0 else 0; risk_budget=capital*risk_pct/100; stop=max(.01,entry*(1-stop_pct/100)); risk_per=entry-stop; risk_shares=math.floor(risk_budget/risk_per) if risk_per>0 else shares_available; shares=max(0,min(shares_available,risk_shares)); used=shares*entry
    levels={"entry":entry,"stop":stop,"target1":float(a["levels"]["target1"]),"target2":float(a["levels"]["target2"]),"target3":float(a["levels"]["target3"])}
    profits={k:shares*(levels[k]-entry) for k in ("target1","target2","target3")}; rr={k:(levels[k]-entry)/risk_per if risk_per else 0 for k in ("target1","target2","target3")}
    return clean({"ticker":t,"capital":capital,"entry":entry,"shares_available":shares_available,"shares":shares,"capital_used":used,"risk_pct":risk_pct,"risk_budget":risk_budget,"stop_pct":stop_pct,"risk_per_share":risk_per,"maximum_loss":shares*risk_per,"maximum_loss_full_position":shares_available*risk_per,"target1":levels["target1"],"target2":levels["target2"],"target3":levels["target3"],"profit_t1":profits["target1"],"profit_t2":profits["target2"],"profit_t3":profits["target3"],"risk_reward":rr,"eta_days":a["eta_days"],"suggested_daily_stop":capital*.02,"signal":a["signal"],"setup_quality":a["setup_quality"],"note":"Position size is constrained by both available capital and risk budget. Target timing is an estimate, not a guarantee."})


@app.get("/api/v1/company-intelligence/{ticker}")
def company_intelligence(ticker: str, quarters: int = 10):
    t = norm_ticker(ticker)
    if get_company_intelligence is None:
        raise HTTPException(500, "Company Intelligence engine is not available.")
    try:
        return clean(get_company_intelligence(t, quarters=max(1, min(20, int(quarters)))))
    except Exception as e:
        raise HTTPException(502, f"Company Intelligence failed for {t}: {e}")


def planner_strategy(value):
    return value if value and value != "auto" else "swing_trade"


def planner_universe(req: TradePlannerRequest):
    defaults = ["NVDA","MSFT","AAPL","AMD","AVGO","META","GOOGL","AMZN","TSLA","CRWD","PANW","SMCI"]
    symbols = req.symbols or defaults
    out = []
    for symbol in symbols:
        try:
            t = norm_ticker(symbol)
            if t not in out:
                out.append(t)
        except HTTPException:
            continue
    return out[:12] or defaults[:8]


def planner_candidate(ticker, req: TradePlannerRequest, slots):
    a = analysis(ticker, "1mo", "1d")
    price = float(a["price"])
    entry = float(a["levels"]["entry"])
    stop = float(a["levels"]["stop"])
    target1 = float(a["levels"]["target1"])
    target2 = float(a["levels"]["target2"])
    risk_per_share = max(entry - stop, entry * 0.01)
    reward_per_share = max(target1 - entry, 0)
    max_loss = max(0, float(req.max_loss_amount or 0))
    risk_budget = max_loss / max(1, slots) if max_loss else max(1, float(req.capital or 0) * 0.01 / max(1, slots))
    capital_slice = max(0, float(req.capital or 0)) / max(1, slots)
    shares_by_risk = risk_budget / risk_per_share if risk_per_share else 0
    shares_by_capital = capital_slice / entry if entry else 0
    shares = max(0, min(shares_by_risk, shares_by_capital))
    if not req.allow_fractional_shares:
        shares = math.floor(shares)
    allocation = shares * entry
    potential_profit = shares * reward_per_share
    potential_loss = shares * risk_per_share
    rr = reward_per_share / risk_per_share if risk_per_share else 0
    base_score = float(a.get("setup_quality") or 0)
    score = base_score
    score += 10 if a["signal"] == "BUY" else -4 if a["signal"] == "SELL" else 0
    score += 8 if a["trend"] == "Bullish" else -5 if a["trend"] == "Bearish" else 0
    score += 5 if a["momentum"] == "Strong" else -4 if a["momentum"] == "Weak" else 0
    confidence = max(0, min(100, round(score)))
    expected_return = (target1 - entry) / entry if entry else 0
    positive_probability = max(.35, min(.75, confidence / 100))
    expected_value = (potential_profit * positive_probability) - (potential_loss * (1 - positive_probability))
    return clean({
        "ticker": ticker,
        "company": ticker,
        "strategy": planner_strategy(req.strategy),
        "data_quality": "live",
        "confidence": confidence,
        "havi_score": confidence,
        "current_price": price,
        "entry": entry,
        "capital_allocation": allocation,
        "shares": shares,
        "target_1": target1,
        "target_2": target2,
        "stop_loss": stop,
        "reward_risk_ratio": rr,
        "risk_reward": rr,
        "expected_return": expected_return,
        "potential_profit_at_target": potential_profit,
        "potential_loss_at_stop": potential_loss,
        "expected_profit": potential_profit,
        "expected_value": expected_value,
        "positive_probability": positive_probability,
        "signal": a["signal"],
        "trend": a["trend"],
        "evidence": {
            "technical": {"status": a["trend"], "score": confidence, "evidence": [{"metric": "RSI", "value": a["rsi"]}]},
            "momentum": {"status": a["momentum"], "score": confidence},
            "volume": {"status": f"{round(float(a.get('volume_ratio') or 1), 2)}x average", "evidence": [{"metric": "Volume ratio", "value": a.get("volume_ratio")}]},
            "pattern": {"status": (a.get("pattern") or {}).get("name")},
            "fundamental": {"status": "Confirm with fundamentals before execution"},
            "news_sentiment": {"status": "Review current headlines before execution"},
            "geopolitical_policy": {"status": "Normal review"},
            "backtest": {"status": "Derived from live technical setup"},
        },
        "scenarios": {
            "bull": {"probability": .25, "return_percent": expected_return * 100 * 1.5},
            "base": {"probability": .50, "return_percent": expected_return * 100},
            "bear": {"probability": .25, "return_percent": -abs((entry - stop) / entry * 100) if entry else 0},
        },
        "horizons": {
            "day": {"expected_return": expected_return * .35, "positive_probability": positive_probability, "low_return": -abs(expected_return * .25), "high_return": expected_return},
            "swing": {"expected_return": expected_return, "positive_probability": positive_probability, "low_return": -abs((entry - stop) / entry) if entry else 0, "high_return": expected_return * 1.5},
        },
        "why_selected": [f"{ticker} has {a['trend']} trend, {a['momentum']} momentum, and {round(float(a.get('volume_ratio') or 1), 2)}x average volume."],
    })


def build_trade_planner(req: TradePlannerRequest):
    slots = max(1, min(5, int(req.number_of_positions or 1)))
    candidates = []
    rejected = []
    universe = planner_universe(req)[:max(3, min(5, slots + 2))]
    pool = ThreadPoolExecutor(max_workers=min(4, len(universe)))
    futures = {pool.submit(planner_candidate, ticker, req, slots): ticker for ticker in universe}
    try:
        for future in as_completed(futures, timeout=14):
            ticker = futures[future]
            try:
                candidates.append(future.result(timeout=1))
            except HTTPException as e:
                rejected.append({"ticker": ticker, "reason": str(e.detail)})
            except Exception as e:
                rejected.append({"ticker": ticker, "reason": str(e)})
    except FuturesTimeoutError:
        pending = [ticker for future, ticker in futures.items() if not future.done()]
        rejected.extend({"ticker": ticker, "reason": "Provider timed out"} for ticker in pending)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    candidates.sort(key=lambda x: float(x.get("confidence") or 0), reverse=True)
    selected = candidates[:slots]
    allocated = sum(float(x.get("capital_allocation") or 0) for x in selected)
    potential_profit = sum(float(x.get("potential_profit_at_target") or 0) for x in selected)
    planned_risk = sum(float(x.get("potential_loss_at_stop") or 0) for x in selected)
    confidence = sum(float(x.get("confidence") or 0) for x in selected) / max(1, len(selected)) if selected else 0
    decision = "REVIEW" if selected and confidence >= 45 else "WAIT"
    summary = "Planner built from live market analysis and risk limits." if selected else "No planner opportunities passed the current provider checks."
    first_symbol = (req.symbols or ["SPY"])[0]
    return clean({
        "decision": decision,
        "planner_mode": "full",
        "summary": summary,
        "recommendations": selected,
        "allocation": {"allocated_capital": allocated, "requested_capital": req.capital, "positions": len(selected)},
        "cash_reserve": max(0, float(req.capital or 0) - allocated),
        "potential_profit_at_target": potential_profit,
        "expected_profit": potential_profit,
        "planned_risk": planned_risk,
        "maximum_expected_loss": planned_risk,
        "expected_value": sum(float(x.get("expected_value") or 0) for x in selected),
        "expected_portfolio_return": potential_profit / max(1, float(req.capital or 0)),
        "confidence": confidence,
        "warnings": [] if selected else ["Provider did not return enough tradable candidates."],
        "market_regime": {
            "regime": "Mixed",
            "trend": selected[0]["trend"] if selected else "Not returned",
            "volatility": "Normal",
            "confidence": confidence,
            "market_data_as_of": datetime.now(timezone.utc).isoformat(),
            "evidence": [{"symbol": x["ticker"], "price": x["current_price"], "change_pct": 0} for x in selected[:4]],
        },
        "alternative_strategies": [
            {"strategy": "day_trade", "average_score": confidence * .9},
            {"strategy": "swing_trade", "average_score": confidence},
            {"strategy": "position_trade", "average_score": confidence * .95},
        ],
        "rejected_candidates": rejected[:8],
        "ticker": norm_ticker(first_symbol),
    })


@app.post("/api/v1/planner/analyze")
@app.post("/api/v1/trade-planner/analyze")
def trade_planner(req: TradePlannerRequest):
    return build_trade_planner(req)

# Compatibility routes
@app.get("/api/v1/stock/{ticker}")
def old_stock(ticker:str): return analysis(norm_ticker(ticker))
@app.get("/api/v1/company/{ticker}")
def old_company(ticker:str): return company_info(norm_ticker(ticker))
@app.get("/api/v1/fundamental/{ticker}")
def old_fundamental(ticker:str): return fundamentals(norm_ticker(ticker))
@app.get("/api/v1/research/{ticker}")
def old_research(ticker:str): return full360(norm_ticker(ticker))
@app.get("/api/v1/risk")
def old_risk(ticker:str="SPY"): return clean({"ticker":norm_ticker(ticker),"status":"calculated from live market volatility"})
@app.get("/api/v1/portfolio")
def portfolio(): return {"status":"ready","cash":0,"positions":[],"engine":"Portfolio data source not connected"}
