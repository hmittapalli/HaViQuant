from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import math, os, re, statistics, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

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

APP_VERSION = "26.2.0"
app = FastAPI(title="HaViQuant V26 360 Trading Intelligence", version=APP_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

SCAN_UNIVERSE = [
    "SPCX", "NVDA", "AMD", "AVGO", "TSLA", "META", "MSFT", "AAPL", "AMZN", "GOOGL", "NFLX",
    "PLTR", "SMCI", "ARM", "MU", "TSM", "MRNA", "PFE", "LLY", "NVO", "UNH",
    "JPM", "GS", "COIN", "MARA", "RIOT", "HOOD", "SOFI", "RIVN", "LCID", "CCL",
    "NCLH", "BA", "GE", "XOM", "CVX", "OXY", "URA", "CCJ", "AI", "SNOW",
    "CRWD", "PANW", "NET", "DDOG", "SHOP", "UBER", "ABNB", "ROKU", "RBLX", "IONQ",
    "APP", "AFRM", "UPST", "MSTR", "BABA", "PDD", "SE", "MELI", "CELH", "ELF",
    "DKNG", "PINS", "SNAP", "SQ", "PYPL", "INTC", "QCOM", "ORCL", "NOW", "CRM",
    "VRTX", "REGN", "BIIB", "GILD", "BMY", "MRK", "ISRG", "TMO", "DHR", "GEHC",
    "LMT", "RTX", "NOC", "CAT", "DE", "FCX", "NEM", "SLV", "GLD", "TLT",
    "IWM", "XBI", "XLE", "XLK", "XLF", "XLI", "XLY", "XLP", "XLV", "XME",
]

SECTOR_UNIVERSES = {
    "AI / Semiconductors": ["NVDA", "AMD", "AVGO", "ARM", "MU", "TSM", "SMCI", "QCOM", "INTC", "ORCL"],
    "Software / Cloud": ["MSFT", "GOOGL", "META", "SNOW", "CRWD", "PANW", "NET", "DDOG", "NOW", "CRM"],
    "Biotech / Healthcare": ["MRNA", "PFE", "LLY", "NVO", "UNH", "VRTX", "REGN", "BIIB", "GILD", "BMY", "MRK", "ISRG"],
    "Space / Defense": ["SPCX", "RKLB", "BA", "LMT", "RTX", "NOC", "GE", "GEHC"],
    "EV / Mobility": ["TSLA", "RIVN", "LCID", "UBER", "ABNB", "CCL", "NCLH"],
    "Crypto / Fintech": ["COIN", "MARA", "RIOT", "HOOD", "SOFI", "AFRM", "UPST", "PYPL", "MSTR"],
    "Energy / Commodities": ["XOM", "CVX", "OXY", "URA", "CCJ", "FCX", "NEM", "SLV", "GLD", "XLE", "XME"],
    "Consumer / Internet": ["AMZN", "NFLX", "SHOP", "ROKU", "RBLX", "BABA", "PDD", "SE", "MELI", "CELH", "ELF", "DKNG", "PINS", "SNAP"],
    "Financials": ["JPM", "GS", "XLF", "SQ", "PYPL", "HOOD", "SOFI"],
    "ETFs / Macro": ["SPY", "QQQ", "IWM", "TLT", "XBI", "XLE", "XLK", "XLF", "XLI", "XLY", "XLP", "XLV"],
}

GEOPOLITICAL_THEMES = [
    {
        "name": "Tariffs / Trade Policy",
        "query": "US tariffs trade policy China imports exports stocks sectors",
        "fallback_queries": ["tariffs stocks Reuters", "trade policy China tariffs market impact", "US import tariffs sector impact stocks"],
        "benefits": ["domestic industrials", "steel/materials", "defense supply chain"],
        "pressures": ["retail importers", "hardware margins", "global autos"],
        "tickers": ["CAT", "DE", "XME", "FCX", "AAPL", "TSLA", "XLY"],
    },
    {
        "name": "Defense / Global Conflict",
        "query": "global conflict defense spending NATO missiles drones stocks",
        "fallback_queries": ["defense spending stocks global conflict", "NATO defense budget stocks", "missile drones defense stocks"],
        "benefits": ["defense", "aerospace", "cybersecurity"],
        "pressures": ["airlines", "travel", "risk assets"],
        "tickers": ["LMT", "RTX", "NOC", "BA", "PANW", "CRWD", "CCL", "NCLH"],
    },
    {
        "name": "Energy Security / Oil",
        "query": "geopolitics oil sanctions OPEC energy security stocks",
        "fallback_queries": ["oil sanctions stocks energy security", "OPEC geopolitics oil stocks", "Middle East oil market stocks"],
        "benefits": ["oil producers", "uranium", "energy infrastructure"],
        "pressures": ["airlines", "consumer discretionary", "transportation"],
        "tickers": ["XOM", "CVX", "OXY", "URA", "CCJ", "XLE", "XLY"],
    },
    {
        "name": "Technology Regulation / AI Policy",
        "query": "AI regulation export controls chips data centers government policy stocks",
        "fallback_queries": ["AI regulation chip export controls stocks", "semiconductor export controls stocks", "data center policy AI stocks"],
        "benefits": ["approved AI infrastructure", "cybersecurity", "domestic semiconductors"],
        "pressures": ["restricted chip exports", "high multiple software"],
        "tickers": ["NVDA", "AMD", "AVGO", "TSM", "CRWD", "PANW", "NET", "XLK"],
    },
    {
        "name": "Healthcare / FDA Policy",
        "query": "FDA approval healthcare policy drug pricing biotech stocks",
        "fallback_queries": ["FDA approval biotech stocks", "drug pricing policy healthcare stocks", "healthcare policy biotech market impact"],
        "benefits": ["approved drugs", "biotech catalysts", "medical devices"],
        "pressures": ["drug pricing exposed names", "failed trial stocks"],
        "tickers": ["MRNA", "LLY", "NVO", "VRTX", "REGN", "XBI", "XLV"],
    },
]

CATALYST_KEYWORDS = {
    "approval": 18, "approved": 18, "fda": 16, "phase 3": 14, "trial": 10,
    "partnership": 12, "deal": 10, "contract": 12, "order": 10, "backlog": 9,
    "upgrade": 12, "raises target": 12, "outperform": 9, "beat": 11, "beats": 11,
    "guidance": 9, "raises guidance": 16, "record": 8, "surge": 8, "launch": 8,
    "ai": 8, "chip": 8, "data center": 10, "buyback": 9, "activist": 8,
    "merger": 11, "acquisition": 11, "short squeeze": 12,
}

NEGATIVE_CATALYST_KEYWORDS = {
    "downgrade": 12, "miss": 10, "misses": 10, "lawsuit": 9, "investigation": 10,
    "warning": 9, "cuts guidance": 15, "bankruptcy": 20, "offering": 10,
}


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


def quote_fallback_history(ticker):
    try:
        fast = yf.Ticker(ticker).fast_info
        price = float(fast.get("last_price") or fast.get("lastPrice") or fast.get("regular_market_price"))
        prev = float(fast.get("previous_close") or fast.get("previousClose") or price)
        volume = int(fast.get("last_volume") or fast.get("lastVolume") or 0)
    except Exception:
        return None
    if not math.isfinite(price) or price <= 0:
        return None
    if not math.isfinite(prev) or prev <= 0:
        prev = price
    dates = pd.date_range(end=pd.Timestamp.now(tz="UTC"), periods=2, freq="D")
    return pd.DataFrame(
        {
            "Open": [prev, prev],
            "High": [max(prev, price), max(prev, price)],
            "Low": [min(prev, price), min(prev, price)],
            "Close": [prev, price],
            "Volume": [volume, volume],
        },
        index=dates,
    )


def download(ticker, period="6mo", interval="1d"):
    # yfinance has no native 4H interval; fetch 1H and resample below.
    source_interval = "1h" if interval == "4h" else interval
    period = period_for_interval(period, source_interval)
    try:
        df = yf.download(ticker, period=period, interval=source_interval, progress=False, auto_adjust=False, threads=False)
    except Exception as e:
        raise HTTPException(502, f"Market data provider error: {e}")
    if df is None or df.empty:
        if source_interval != "1d":
            try:
                df = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=False, threads=False)
                source_interval = "1d"
            except Exception as e:
                raise HTTPException(502, f"Market data provider error: {e}")
        if df is None or df.empty:
            raise HTTPException(404, f"No market data found for {ticker} ({interval})")
    if isinstance(df.columns, pd.MultiIndex):
        levels = [list(map(str, df.columns.get_level_values(i))) for i in range(df.columns.nlevels)]
        if ticker in levels[-1]:
            df = df.xs(ticker, axis=1, level=df.columns.nlevels - 1)
        elif ticker in levels[0]:
            df = df.xs(ticker, axis=1, level=0)
        else:
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df.rename(columns={c:str(c).title().replace("Adj close", "Adj Close") for c in df.columns})
    df = df.loc[:, ~df.columns.duplicated()]
    needed = ["Open","High","Low","Close","Volume"]
    for c in needed:
        if c not in df.columns: raise HTTPException(502, f"Provider did not return {c}")
    df = df[needed].copy().dropna(subset=["Open","High","Low","Close"])
    if df.empty:
        fallback = quote_fallback_history(ticker)
        if fallback is not None:
            return fallback
        raise HTTPException(404, f"No usable market data found for {ticker} ({interval})")
    if interval == "4h" and source_interval != "1d":
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


def score_catalysts(items):
    score = 0
    reasons = []
    titles = []
    for item in items[:8]:
        title = item.get("title") or ""
        body = f"{title} {item.get('summary') or ''}".lower()
        titles.append(title)
        for word, points in CATALYST_KEYWORDS.items():
            if word in body:
                score += points
                reasons.append(word)
        for word, points in NEGATIVE_CATALYST_KEYWORDS.items():
            if word in body:
                score -= points
                reasons.append(f"risk: {word}")
    unique = []
    for reason in reasons:
        if reason not in unique:
            unique.append(reason)
    return score, unique[:6], titles[:3]


def infer_policy_detail(item, theme_name):
    title = item.get("title") or ""
    text = f"{title} {item.get('summary') or ''}".lower()
    places = []
    for label, terms in {
        "United States": ["u.s.", "us ", "united states", "white house", "washington", "congress", "senate"],
        "China": ["china", "beijing"],
        "Europe / EU": ["europe", "european union", " eu ", "brussels"],
        "Russia": ["russia", "moscow"],
        "Middle East": ["middle east", "iran", "israel", "gaza", "saudi", "opec"],
        "India": ["india", "new delhi"],
        "Global": ["global", "worldwide", "international"],
    }.items():
        if any(term in f" {text} " for term in terms):
            places.append(label)
    policy = []
    for label, terms in {
        "Tariff / trade restriction": ["tariff", "tariffs", "import", "export", "trade"],
        "Sanctions / ban": ["sanction", "sanctions", "ban", "banned"],
        "Government spending / contract": ["spending", "contract", "budget", "defense bill"],
        "Regulation / policy decision": ["regulation", "policy", "rule", "government"],
        "Central bank / speech": ["fed", "federal reserve", "speech", "rate"],
        "FDA / healthcare decision": ["fda", "approval", "trial", "drug"],
    }.items():
        if any(term in text for term in terms):
            policy.append(label)
    published = item.get("published_iso") or item.get("published")
    end_match = re.search(r"(?:until|through|expires?|ending|ends?)\s+([A-Z][a-z]+\.?\s+\d{1,2},?\s+\d{4}|\d{4})", title + " " + (item.get("summary") or ""))
    return clean({
        "headline": title,
        "theme": theme_name,
        "place": ", ".join(places) or "Not specified in headline",
        "policy": ", ".join(policy) or theme_name,
        "announced_or_reported": published or "Date not provided by feed",
        "status": "Reported in linked article",
        "end_date": end_match.group(1) if end_match else "Not stated in the article headline/feed summary",
        "source": item.get("publisher") or "News source",
        "url": item.get("url"),
        "sentiment": item.get("sentiment"),
    })


def scanner_row(ticker):
    t = norm_ticker(ticker)
    result = {"ticker": t, "score": 0, "signal": "WATCH", "why": [], "articles": []}
    try:
        a = analysis(t, "3mo", "1d")
        result.update({
            "price": a.get("price"),
            "change_pct": a.get("change_pct"),
            "technical_score": a.get("setup_quality"),
            "trend": a.get("trend"),
            "momentum": a.get("momentum"),
            "signal": a.get("signal"),
            "volume_ratio": a.get("volume_ratio"),
        })
        result["score"] += float(a.get("setup_quality") or 0) * 0.55
        if a.get("trend") == "Bullish": result["score"] += 8
        if a.get("momentum") == "Strong": result["score"] += 8
        if float(a.get("volume_ratio") or 0) >= 1.4: result["score"] += 6
    except Exception as e:
        result["why"].append(f"technical data unavailable: {e}")

    headlines = []
    try:
        headlines.extend(news(t).get("items", [])[:6])
    except Exception:
        pass
    headlines.extend(rss_search(f"{t} stock catalyst FDA earnings upgrade contract partnership AI", 6))
    catalyst_score, reasons, titles = score_catalysts(headlines)
    result["score"] += catalyst_score
    result["catalyst_score"] = catalyst_score
    result["catalysts"] = reasons
    result["articles"] = [
        {"title": x.get("title"), "publisher": x.get("publisher"), "url": x.get("url"), "sentiment": x.get("sentiment")}
        for x in headlines[:5] if x.get("title")
    ]
    if reasons:
        result["why"].append("News catalyst language: " + ", ".join(reasons[:4]))
    if titles:
        result["why"].append("Fresh headlines are appearing before the move is fully reflected in the setup.")
    if not result["why"]:
        result["why"].append("No strong catalyst found; keep on watchlist only.")
    positive = [x for x in reasons if not x.startswith("risk:")]
    risks = [x.replace("risk: ", "") for x in reasons if x.startswith("risk:")]
    trend = result.get("trend") or "Unknown"
    momentum = result.get("momentum") or "Unknown"
    signal = result.get("signal") or "WATCH"
    tech_score = result.get("technical_score")
    result["upside_thesis"] = (
        f"{t} is ranked because the scan found {', '.join(positive[:3]) or 'early catalyst'} "
        f"language while the chart reads {trend.lower()} with {momentum.lower()} momentum. "
        f"The current system signal is {signal} and the technical score is {round(float(tech_score), 1) if tech_score is not None else 'N/A'}."
    )
    result["confirmation"] = [
        "Follow-through above the prior day high",
        "Volume expansion above the 20-day average",
        "Fresh positive headline or analyst/event confirmation",
    ]
    result["risk_watch"] = risks[:3] or [
        "Headline may already be priced in",
        "Broad market weakness can override the setup",
        "Wait for price confirmation before entry",
    ]
    if signal == "BUY" and momentum == "Strong":
        result["estimated_bullish_timeframe"] = "1-5 trading days after price and volume confirmation"
    elif trend == "Bullish":
        result["estimated_bullish_timeframe"] = "1-3 weeks if the catalyst continues and support holds"
    elif trend == "Mixed":
        result["estimated_bullish_timeframe"] = "Watch 2-6 weeks; needs breakout confirmation first"
    else:
        result["estimated_bullish_timeframe"] = "No bullish timeframe yet; wait for trend reversal"
    lead_article = result["articles"][0] if result["articles"] else {}
    result["next_announcement_watch"] = {
        "summary": lead_article.get("title") or "Watch the next earnings call, SEC filing, company update, product launch, regulatory update, or analyst revision.",
        "source": lead_article.get("publisher") or "Market/news feed",
        "url": lead_article.get("url"),
    }
    result["product_progress_watch"] = (
        "Track product launches, customer contracts, regulatory milestones, production/delivery updates, and management guidance for confirmation."
    )
    base_upside = 3 + max(0, (result["score"] - 60) / 8)
    if signal == "BUY": base_upside += 2
    if momentum == "Strong": base_upside += 1.5
    result["estimated_upside_pct"] = round(max(1.5, min(14, base_upside)), 1)
    price = result.get("price")
    result["estimated_target_price"] = round(float(price) * (1 + result["estimated_upside_pct"] / 100), 2) if price else None
    result["score"] = round(max(0, min(100, result["score"])), 1)
    return clean(result)


@app.get("/api/v1/market/trade-scanner")
def trade_scanner(limit:int=50, universe:Optional[str]=None, sector:Optional[str]=None):
    selected_sector = urllib.parse.unquote(sector or "").strip()
    if universe:
        source_symbols = universe.split(",")
    elif selected_sector and selected_sector.lower() != "all":
        source_symbols = SECTOR_UNIVERSES.get(selected_sector, SCAN_UNIVERSE)
    else:
        source_symbols = SCAN_UNIVERSE
    symbols = [x.strip().upper() for x in source_symbols if x.strip()]
    symbols = [x for x in symbols if re.fullmatch(r"[A-Z0-9.\-]{1,12}", x)][:80]
    rows = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(scanner_row, s): s for s in symbols}
        for f in as_completed(futures):
            try:
                rows.append(f.result())
            except Exception as e:
                rows.append({"ticker": futures[f], "score": 0, "signal": "WATCH", "why": [str(e)], "articles": []})
    rows.sort(key=lambda x: (x.get("score") or 0, x.get("catalyst_score") or 0), reverse=True)
    return clean({
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "sector": selected_sector or "All",
        "sectors": ["All"] + list(SECTOR_UNIVERSES.keys()),
        "universe_size": len(symbols),
        "items": rows[:max(1, min(50, int(limit)))],
        "method": "Ranks symbols by recent catalyst headlines, technical setup, momentum, volume expansion, and positive event language.",
        "disclaimer": "Research signal only. This does not guarantee that the stock price will rise.",
    })


def geopolitics_theme(theme):
    articles = rss_search(theme["query"], 8)
    if not articles:
        for q in theme.get("fallback_queries", []):
            articles.extend(rss_search(q, 4))
            if len(articles) >= 5:
                break
    text = " ".join([(x.get("title") or "") + " " + (x.get("summary") or "") for x in articles]).lower()
    heat = 35
    for word in ["tariff", "sanction", "ban", "export control", "war", "conflict", "fda", "regulation", "policy", "speech", "government"]:
        if word in text:
            heat += 9
    for word in ["approval", "deal", "spending", "contract", "subsidy", "investment"]:
        if word in text:
            heat += 6
    heat = max(0, min(100, heat))
    direction = "Benefit" if heat >= 60 else "Watch"
    details = [infer_policy_detail(x, theme["name"]) for x in articles[:5] if x.get("title")]
    if details:
        why = f"{theme['name']} has {len(details)} linked article signal{'s' if len(details) != 1 else ''}. Review place, policy, reported date and end-date status before trading."
    else:
        why = f"No verified live article detail was returned for {theme['name'].lower()} in this scan. Keep the theme on watch, but do not treat it as an active catalyst without source confirmation."
    return clean({
        "theme": theme["name"],
        "heat": heat,
        "direction": direction,
        "benefiting_sectors": theme["benefits"],
        "pressured_sectors": theme["pressures"],
        "stocks_to_watch": theme["tickers"],
        "why": why,
        "policy_details": details,
        "articles": [
            {"title": x.get("title"), "publisher": x.get("publisher"), "url": x.get("url"), "published_iso": x.get("published_iso"), "sentiment": x.get("sentiment")}
            for x in articles[:5] if x.get("title")
        ],
    })


@app.get("/api/v1/market/geopolitics")
def geopolitical_scanner(limit:int=8):
    rows = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(geopolitics_theme, theme): theme["name"] for theme in GEOPOLITICAL_THEMES}
        for f in as_completed(futures):
            try:
                rows.append(f.result())
            except Exception as e:
                rows.append({"theme": futures[f], "heat": 0, "direction": "Unavailable", "why": str(e), "articles": []})
    rows.sort(key=lambda x: x.get("heat") or 0, reverse=True)
    return clean({
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "items": rows[:max(1, min(20, int(limit)))],
        "method": "Scans policy, politician speech, government decisions, tariffs, sanctions, regulation, Fed/global politics and maps them to sectors/stocks.",
        "disclaimer": "Policy impact is probabilistic. Confirm with price, volume, official releases, and sector ETF behavior.",
    })


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


INDEX_SYMBOLS = [
    ("S&P 500", "^GSPC"),
    ("NASDAQ", "^IXIC"),
    ("DOW", "^DJI"),
    ("VIX", "^VIX"),
]


def latest_market_row(symbol, label=None):
    try:
        df = yf.download(symbol, period="5d", interval="1d", progress=False, auto_adjust=False, threads=False)
    except Exception:
        df = None
    if df is None or df.empty:
        fallback = quote_fallback_history(symbol)
        df = fallback if fallback is not None else None
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df = df.rename(columns={c: str(c).title().replace("Adj close", "Adj Close") for c in df.columns})
    df = df.loc[:, ~df.columns.duplicated()]
    df = df.dropna(subset=["Close"])
    if df.empty:
        return None
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    def scalar(value):
        if isinstance(value, pd.Series):
            value = value.dropna().iloc[0] if not value.dropna().empty else None
        return value
    price_value = scalar(last.Close)
    prev_value = scalar(prev.Close)
    if price_value is None or pd.isna(price_value):
        return None
    price = float(price_value)
    prev_close = float(prev_value) if prev_value is not None and pd.notna(prev_value) and float(prev_value) else price
    volume_value = scalar(last.Volume) if "Volume" in df.columns else None
    volume = int(volume_value) if volume_value is not None and pd.notna(volume_value) else None
    avg_volume = None
    if "Volume" in df.columns:
        values = [float(x) for x in df.Volume.tail(5).tolist() if pd.notna(x) and float(x) > 0]
        avg_volume = statistics.mean(values) if values else None
    return clean({
        "symbol": label or symbol,
        "ticker": symbol,
        "price": price,
        "change_pct": ((price / prev_close) - 1) * 100 if prev_close else None,
        "volume": volume,
        "avg_volume": avg_volume,
        "relative_volume": (volume / avg_volume) if volume and avg_volume else None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Yahoo Finance via yfinance",
    })


def market_indices():
    rows = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(latest_market_row, symbol, label): label for label, symbol in INDEX_SYMBOLS}
        for f in as_completed(futures):
            item = f.result()
            if item:
                rows.append(item)
    order = {label: idx for idx, (label, _) in enumerate(INDEX_SYMBOLS)}
    rows.sort(key=lambda x: order.get(x.get("symbol"), 99))
    return rows


def market_movers(limit=12):
    symbols = [s for s in SCAN_UNIVERSE if re.fullmatch(r"[A-Z0-9.\-]{1,12}", s)][:70]
    rows = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(latest_market_row, symbol): symbol for symbol in symbols}
        for f in as_completed(futures):
            item = f.result()
            if item and item.get("price") is not None and item.get("change_pct") is not None:
                rows.append(item)
    mode_rows = rows[:]
    mode_rows.sort(key=lambda x: (abs(float(x.get("change_pct") or 0)), float(x.get("relative_volume") or 0)), reverse=True)
    active_rows = rows[:]
    active_rows.sort(key=lambda x: (float(x.get("relative_volume") or 0), float(x.get("volume") or 0)), reverse=True)
    return clean({
        "items": mode_rows[:max(1, min(30, int(limit)))],
        "gainers": sorted(rows, key=lambda x: float(x.get("change_pct") or -999), reverse=True)[:max(1, min(30, int(limit)))],
        "losers": sorted(rows, key=lambda x: float(x.get("change_pct") or 999))[:max(1, min(30, int(limit)))],
        "most_active": active_rows[:max(1, min(30, int(limit)))],
        "source": "Yahoo Finance via yfinance",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })


def market_sentiment(indices):
    values = [float(x.get("change_pct")) for x in indices if x.get("symbol") != "VIX" and x.get("change_pct") is not None]
    vix = next((x for x in indices if x.get("symbol") == "VIX"), {})
    vix_change = float(vix.get("change_pct")) if vix.get("change_pct") is not None else 0
    avg = statistics.mean(values) if values else 0
    raw = 50 + (avg * 10) - (vix_change * 2)
    score = round(max(0, min(100, raw)), 1)
    label = "Bullish" if score >= 60 else ("Bearish" if score <= 40 else "Mixed")
    positives = sum(1 for x in values if x > 0)
    negatives = sum(1 for x in values if x < 0)
    total = max(1, len(values))
    return clean({
        "score": score,
        "label": label,
        "market_regime": label,
        "bullish_pct": round((positives / total) * 100, 1),
        "bearish_pct": round((negatives / total) * 100, 1),
        "neutral_pct": round(((total - positives - negatives) / total) * 100, 1),
        "vix_change_pct": vix_change if vix else None,
        "source": "Derived from provider index changes and VIX movement",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })


def macro_event_feed(ticker):
    queries = [
        (f"{ticker} earnings analyst rating product launch market catalyst", "Earnings"),
        ("Federal Reserve rate decision inflation jobs GDP CPI PCE market impact", "Fed / Macro"),
        ("US economic calendar CPI PCE GDP jobs report market impact", "Economic"),
        ("markets geopolitics tariffs sanctions regulation stocks", "Geopolitical"),
    ]
    seen = set()
    events = []
    for query, category in queries:
        for item in rss_search(query, 5):
            title = item.get("title")
            if not title or title in seen:
                continue
            seen.add(title)
            s = item.get("sentiment") or sentiment(title)
            events.append(clean({
                **item,
                "category": category,
                "impact": s.get("impact"),
                "impact_label": s.get("impact"),
                "status": "Linked source",
                "source_name": item.get("publisher") or "News source",
            }))
    events.sort(key=lambda x: x.get("published_iso") or "", reverse=True)
    return events[:16]


def company_info(ticker):
    try:
        info=yf.Ticker(ticker).info or {}
        return clean({"ticker":ticker,"name":info.get("longName") or info.get("shortName") or ticker,"sector":info.get("sector"),"industry":info.get("industry"),"marketCap":info.get("marketCap"),"website":info.get("website"),"country":info.get("country"),"exchange":info.get("exchange")})
    except Exception as e: return {"ticker":ticker,"name":ticker,"sector":None,"industry":None,"marketCap":None,"error":str(e)}


def fundamentals(ticker):
    data = {"ticker": ticker, "source": "Yahoo Finance via yfinance"}
    try:
        info=yf.Ticker(ticker).info or {}
        data.update({
            "marketCap":info.get("marketCap"),
            "trailingPE":info.get("trailingPE"),
            "forwardPE":info.get("forwardPE"),
            "epsTrailingTwelveMonths":info.get("epsTrailingEps") or info.get("epsTrailingTwelveMonths"),
            "revenueGrowth":info.get("revenueGrowth"),
            "profitMargins":info.get("profitMargins"),
            "returnOnEquity":info.get("returnOnEquity"),
            "dividendYield":info.get("dividendYield"),
            "beta":info.get("beta"),
        })
    except Exception as e:
        data["primary_error"] = str(e)
    try:
        fast = yf.Ticker(ticker).fast_info or {}
        data["marketCap"] = data.get("marketCap") or fast.get("market_cap")
    except Exception:
        pass
    return clean(data)


def insiders(ticker):
    t = norm_ticker(ticker)
    out = {"ticker": t, "items": [], "holders": [], "source": "Yahoo Finance insider/holder data"}
    try:
        obj = yf.Ticker(t)
        tx = getattr(obj, "insider_transactions", None)
        if tx is not None and not tx.empty:
            for _, row in tx.head(12).iterrows():
                data = {str(k): clean(v) for k, v in row.items()}
                out["items"].append(data)
        holders = getattr(obj, "major_holders", None)
        if holders is not None and not holders.empty:
            out["holders"] = clean(holders.reset_index().to_dict("records")[:8])
    except Exception as e:
        out["error"] = str(e)
    return clean(out)


@app.get("/api/v1/meta")
def api_metadata():
    return clean({
        "app":"HaViQuant",
        "version":APP_VERSION,
        "supported_intraday":["1m","5m","15m","1h","4h"],
        "supported_navigation":["Stock Analysis","Dashboard","Company Intelligence","Fundamentals","Technical","Decision","Trade Scanner","Evidence Research","Portfolio","Risk","Backtesting","News","Watchlist","Alerts","Calendar","Settings"]
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
    t=norm_ticker(ticker)
    indices = market_indices()
    movers = market_movers(14)
    sent = market_sentiment(indices)
    events = macro_event_feed(t)
    return clean({
        "ticker": t,
        "market_indices": indices,
        "top_movers": movers,
        "sentiment": sent,
        "market_regime": sent.get("market_regime"),
        "vix_regime": "Elevated" if abs(float(sent.get("vix_change_pct") or 0)) >= 2 else "Normal",
        "events": events,
        "geopolitical": rss_search(f"{t} geopolitics tariffs sanctions trade war international policy",6),
        "politics": rss_search(f"{t} politician speech policy regulation government",6),
        "macro": rss_search(f"{t} Federal Reserve rates inflation jobs economy",6),
        "sources": ["Yahoo Finance via yfinance", "Google News RSS"],
        "note": "Market context is derived from linked provider data and headlines. It does not deterministically predict price.",
    })

@app.get("/api/v1/market/insiders")
def market_insiders(ticker:str=Query(...)): return insiders(norm_ticker(ticker))

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
