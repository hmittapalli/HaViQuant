import sys, types, importlib.util
import numpy as np, pandas as pd
from datetime import datetime, timezone, timedelta

fake = types.ModuleType('yfinance')
rng=np.random.default_rng(42)

def make_df(period='6mo', interval='1d'):
    n={'1m':500,'5m':500,'15m':500,'1h':500,'1d':300,'1wk':100,'1mo':60}.get(interval,300)
    freq={'1m':'min','5m':'5min','15m':'15min','1h':'h','1d':'D','1wk':'W','1mo':'MS'}.get(interval,'D')
    end=pd.Timestamp.now(tz='UTC').floor('min')
    idx=pd.date_range(end=end, periods=n, freq=freq)
    base=100+np.cumsum(rng.normal(.05,1,n))
    op=base+rng.normal(0,.3,n); cl=op+rng.normal(.1,.8,n); hi=np.maximum(op,cl)+rng.uniform(.1,1,n); lo=np.minimum(op,cl)-rng.uniform(.1,1,n); vol=rng.integers(1000,100000,n)
    return pd.DataFrame({'Open':op,'High':hi,'Low':lo,'Close':cl,'Volume':vol},index=idx)

def download(*args, **kwargs): return make_df(interval=kwargs.get('interval','1d'))
class Ticker:
    def __init__(self,t): self.t=t
    @property
    def news(self):
        now=datetime.now(timezone.utc)
        return [{'content':{'title':'AAPL beats earnings estimates with strong growth','canonicalUrl':{'url':'https://example.com/1'},'provider':{'displayName':'Test News'},'pubDate':(now-timedelta(days=1)).isoformat()}},{'content':{'title':'AAPL faces investigation and tariff warning','canonicalUrl':{'url':'https://example.com/2'},'provider':{'displayName':'Test News'},'pubDate':(now-timedelta(days=2)).isoformat()}}]
    @property
    def info(self): return {'longName':'Apple Inc.','sector':'Technology','industry':'Consumer Electronics','marketCap':3000000000000,'trailingPE':30.0,'forwardPE':28.0,'epsTrailingTwelveMonths':10.0,'revenueGrowth':.08,'profitMargins':.25,'returnOnEquity':1.5,'beta':1.2,'exchange':'NMS','country':'United States'}
fake.download=download; fake.Ticker=Ticker
sys.modules['yfinance']=fake
sys.path.insert(0,'/tmp/havi_v26')
import backend.main as m

assert m.health()['version']=='26.1.0'
a=m.analysis('AAPL','6mo','1d'); assert a['candles'] and a['levels']['target3']>a['price']
for interval,period in [('1m','7d'),('5m','60d'),('15m','60d'),('1h','60d'),('4h','60d')]:
    x=m.analysis('AAPL',period,interval); assert x['candles'], interval
mtf=m.mtf('AAPL'); assert [x['tf'] for x in mtf]==['4H','1H','15m','5m','1m']
assert m.sentiment('strong growth beats estimates')['label']=='Positive'
assert m.sentiment('investigation tariff warning')['label']=='Negative'
assert m.sentiment('company announces update')['label']=='Neutral'
n=m.news('AAPL'); assert len(n['items'])==2 and all('sentiment' in x for x in n['items'])
c=m.company_info('AAPL'); assert c['sector']=='Technology' and c['marketCap']
f=m.fundamentals('AAPL'); assert f['trailingPE']==30.0
p=m.trade_plan('AAPL',10000,1,3); assert p['risk_budget']==100 and p['stop_pct']==3 and p['shares']>=0
p0=m.trade_plan('AAPL',0,1,3); assert p0['shares']==0
pbig=m.trade_plan('AAPL',1000000,20,50); assert pbig['shares']>=0
# Validate every registered path is unique for each method.
seen=set(); dup=[]
for r in m.app.routes:
    for method in getattr(r,'methods',[]) or []:
        key=(method,r.path)
        if key in seen: dup.append(key)
        seen.add(key)
assert not dup, dup
print('PASS: backend functional smoke tests')
print('PASS: intraday 1m/5m/15m/1h/4h analysis')
print('PASS: MTF 4H/1H/15m/5m/1m')
print('PASS: sentiment positive/negative/neutral')
print('PASS: company/fundamentals')
print('PASS: trade-plan boundary scenarios')
print('PASS: no duplicate FastAPI method/path registrations')
